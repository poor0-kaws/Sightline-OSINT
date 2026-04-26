"""Router for provider-specific raw-record normalizers."""

from __future__ import annotations

from backend.normalization.crt_sh_normalizer import normalize_crt_sh_record
from backend.normalization.csv_upload_normalizer import normalize_csv_upload_record
from backend.normalization.ipinfo_normalizer import normalize_ipinfo_record
from backend.normalization.manual_input_normalizer import normalize_manual_input_record
from backend.normalization.nominatim_normalizer import normalize_nominatim_record
from backend.normalization.opensky_normalizer import normalize_opensky_record
from backend.normalization.webhook_normalizer import normalize_webhook_record
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.storage import SavedRawRecord


def normalize_saved_raw_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Route one saved raw record to the correct provider-specific normalizer."""
    if saved_raw_record.provider == ProviderKind.IPINFO:
        return normalize_ipinfo_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.CRT_SH:
        return normalize_crt_sh_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.NOMINATIM:
        return normalize_nominatim_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.OPENSKY:
        return normalize_opensky_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.WEBHOOK:
        return normalize_webhook_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.CSV_UPLOAD:
        return normalize_csv_upload_record(saved_raw_record)

    if saved_raw_record.provider == ProviderKind.MANUAL_INPUT:
        return normalize_manual_input_record(saved_raw_record)

    requested_provider = _get_provider_text(saved_raw_record)
    metadata = dict(saved_raw_record.metadata)
    if requested_provider:
        metadata["requested_provider"] = requested_provider

    return NormalizedRecord(
        provider=_get_safe_provider(saved_raw_record),
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.ERROR,
        error=ProviderError(
            code=ErrorCode.NORMALIZATION_UNSUPPORTED_PROVIDER.value,
            message=f"No normalizer exists for provider: {requested_provider or 'unknown'}",
        ),
        normalized_data=None,
        metadata=metadata,
    )


def _get_safe_provider(saved_raw_record: SavedRawRecord) -> ProviderKind:
    """Return a safe enum provider for normalized error records."""
    if isinstance(saved_raw_record.provider, ProviderKind):
        return saved_raw_record.provider

    return ProviderKind.IPINFO


def _get_provider_text(saved_raw_record: SavedRawRecord) -> str:
    """Return a readable provider label for messages and metadata."""
    provider = saved_raw_record.provider
    if isinstance(provider, ProviderKind):
        return provider.value

    return str(provider).strip()
