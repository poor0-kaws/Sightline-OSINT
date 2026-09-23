"""Router for provider-specific raw-record normalizers."""

from __future__ import annotations

from collections.abc import Callable

from backend.normalization.crt_sh_normalizer import normalize_crt_sh_record
from backend.normalization.csv_upload_normalizer import normalize_csv_upload_record
from backend.normalization.extraction import extract_shared_artifacts
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


Normalizer = Callable[[SavedRawRecord], NormalizedRecord]

NORMALIZER_BY_PROVIDER: dict[ProviderKind, Normalizer] = {
    ProviderKind.IPINFO: normalize_ipinfo_record,
    ProviderKind.CRT_SH: normalize_crt_sh_record,
    ProviderKind.NOMINATIM: normalize_nominatim_record,
    ProviderKind.OPENSKY: normalize_opensky_record,
    ProviderKind.WEBHOOK: normalize_webhook_record,
    ProviderKind.CSV_UPLOAD: normalize_csv_upload_record,
    ProviderKind.MANUAL_INPUT: normalize_manual_input_record,
}


def normalize_saved_raw_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Route one saved raw record to the correct provider-specific normalizer."""
    normalizer = NORMALIZER_BY_PROVIDER.get(saved_raw_record.provider)
    if normalizer is not None:
        return extract_shared_artifacts(normalizer(saved_raw_record))

    requested_provider = _get_provider_text(saved_raw_record)
    metadata = dict(saved_raw_record.metadata)
    if requested_provider:
        metadata["requested_provider"] = requested_provider

    return extract_shared_artifacts(
        NormalizedRecord(
            provider=_get_safe_provider(saved_raw_record),
            source_type=saved_raw_record.source_type,
            case_id=saved_raw_record.case_id,
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
