"""Router for provider-specific raw-record normalizers."""

from __future__ import annotations

from backend.normalization.crt_sh_normalizer import normalize_crt_sh_record
from backend.normalization.ipinfo_normalizer import normalize_ipinfo_record
from backend.normalization.nominatim_normalizer import normalize_nominatim_record
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

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.ERROR,
        error=ProviderError(
            code=ErrorCode.NORMALIZATION_UNSUPPORTED_PROVIDER.value,
            message=f"No normalizer exists for provider: {saved_raw_record.provider.value}",
        ),
        normalized_data=None,
        metadata=dict(saved_raw_record.metadata),
    )
