"""Local file-based storage for raw provider responses."""

from __future__ import annotations

from enum import Enum
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.schemas.storage import SavedRawRecord
from backend.settings import get_settings
from backend.utils.time import utc_now_iso
from backend.utils.values import clean_text


class FileRawStorageRepository:
    """Save one raw response per JSON file on disk."""

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path)

    def save_raw_response(
        self,
        source_config: SourceConfig,
        raw_response: RawProviderResponse,
    ) -> SavedRawRecord:
        """Save one raw provider response to a JSON file."""
        self.root_path.mkdir(parents=True, exist_ok=True)

        saved_record = SavedRawRecord(
            record_id=uuid4().hex,
            source_id=source_config.source_id,
            provider=raw_response.provider,
            source_type=raw_response.source_type,
            query=raw_response.query,
            fetched_at=raw_response.fetched_at,
            saved_at=utc_now_iso(),
            status=raw_response.status,
            raw_data=raw_response.raw_data,
            error=raw_response.error,
            metadata=raw_response.metadata,
        )
        file_path = self.root_path / self._build_file_name(saved_record)
        temp_file_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
        payload_text = json.dumps(
            self._to_json_value(saved_record),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

        try:
            temp_file_path.write_text(payload_text, encoding="utf-8")
            temp_file_path.replace(file_path)
        except OSError:
            if temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
            raise

        return saved_record

    def load_raw_response(self, record_id: str) -> SavedRawRecord:
        """Load one saved raw record by id."""
        safe_record_id = clean_text(record_id)
        if not safe_record_id:
            raise FileNotFoundError("Saved raw record id is required.")

        for file_path in sorted(self.root_path.glob("*.json")):
            saved_record = self._try_load_saved_record(file_path)
            if saved_record is None:
                continue

            if saved_record.record_id == safe_record_id:
                return saved_record

        raise FileNotFoundError(f"No saved raw record found for id: {safe_record_id}")

    def list_raw_responses(self) -> list[SavedRawRecord]:
        """Return all saved raw records in a stable order."""
        if not self.root_path.exists():
            return []

        saved_records: list[SavedRawRecord] = []

        for file_path in sorted(self.root_path.glob("*.json")):
            saved_record = self._try_load_saved_record(file_path)
            if saved_record is None:
                continue

            saved_records.append(saved_record)

        return saved_records

    def _try_load_saved_record(self, file_path: Path) -> SavedRawRecord | None:
        """Try to load one JSON file into a saved raw record."""
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            return self._build_saved_record(payload)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _build_saved_record(self, payload: dict[str, Any]) -> SavedRawRecord:
        """Turn JSON data back into a saved raw record."""
        if not isinstance(payload, dict):
            raise ValueError("Saved raw record payload must be a dictionary.")

        return SavedRawRecord(
            record_id=clean_text(payload.get("record_id")),
            source_id=clean_text(payload.get("source_id")),
            provider=self._coerce_provider(payload.get("provider")),
            source_type=self._coerce_source_type(payload.get("source_type")),
            query=payload.get("query"),
            fetched_at=clean_text(payload.get("fetched_at")),
            saved_at=clean_text(payload.get("saved_at")),
            status=self._coerce_status(payload.get("status")),
            raw_data=payload.get("raw_data"),
            error=self._coerce_error(payload.get("error")),
            metadata=self._coerce_metadata(payload.get("metadata")),
        )

    def _coerce_provider(self, value: object) -> ProviderKind:
        """Turn a saved provider string back into the enum."""
        return ProviderKind(clean_text(value).lower())

    def _coerce_source_type(self, value: object) -> SourceKind:
        """Turn a saved source-type string back into the enum."""
        return SourceKind(clean_text(value).lower())

    def _coerce_status(self, value: object) -> FetchStatus:
        """Turn a saved status string back into the enum."""
        return FetchStatus(clean_text(value).lower())

    def _coerce_error(self, value: object) -> ProviderError | None:
        """Turn a saved error dict back into a provider error."""
        if value is None:
            return None

        if isinstance(value, ProviderError):
            return value

        if not isinstance(value, dict):
            return ProviderError(
                code="unknown_error",
                message=clean_text(value) or "Unknown saved error",
            )

        return ProviderError(
            code=clean_text(value.get("code")) or "unknown_error",
            message=clean_text(value.get("message")) or "Unknown error",
        )

    def _coerce_metadata(self, value: object) -> dict[str, Any]:
        """Turn saved metadata into a plain dictionary."""
        if value is None:
            return {}

        if isinstance(value, dict):
            return dict(value)

        return {"raw_metadata": value}

    def _build_file_name(self, saved_record: SavedRawRecord) -> str:
        """Build a readable JSON filename for one saved record."""
        safe_provider = self._slug_text(saved_record.provider.value)
        safe_source_id = self._slug_text(saved_record.source_id)
        safe_fetched_at = self._slug_text(saved_record.fetched_at)
        short_record_id = saved_record.record_id[:8]

        return f"{safe_provider}__{safe_source_id}__{safe_fetched_at}__{short_record_id}.json"

    def _slug_text(self, value: str) -> str:
        """Turn text into a simple filename-safe chunk."""
        cleaned_value = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
        cleaned_value = cleaned_value.strip("-")

        if cleaned_value:
            return cleaned_value.lower()

        return "unknown"

    def _to_json_value(self, value: Any) -> Any:
        """Turn nested model data into JSON-safe values."""
        if hasattr(value, "model_dump"):
            return self._to_json_value(value.model_dump())

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, dict):
            json_ready_dict: dict[str, Any] = {}

            for key, nested_value in value.items():
                json_ready_dict[str(key)] = self._to_json_value(nested_value)

            return json_ready_dict

        if isinstance(value, list):
            return [self._to_json_value(item) for item in value]

        return value


def save_raw_response(
    source_config: SourceConfig,
    raw_response: RawProviderResponse,
) -> SavedRawRecord:
    """Save one raw response using the default storage path from settings."""
    repository = FileRawStorageRepository(get_settings().raw_storage_path)
    return repository.save_raw_response(source_config=source_config, raw_response=raw_response)


def load_raw_response(record_id: str) -> SavedRawRecord:
    """Load one raw response from the default storage path."""
    repository = FileRawStorageRepository(get_settings().raw_storage_path)
    return repository.load_raw_response(record_id)


def list_raw_responses() -> list[SavedRawRecord]:
    """List all raw responses from the default storage path."""
    repository = FileRawStorageRepository(get_settings().raw_storage_path)
    return repository.list_raw_responses()


def save_raw_response_safely(
    source_config: SourceConfig,
    raw_response: RawProviderResponse,
) -> SavedRawRecord | None:
    """Try to save a raw response without crashing the fetch path."""
    try:
        return save_raw_response(source_config=source_config, raw_response=raw_response)
    except Exception:
        return None
