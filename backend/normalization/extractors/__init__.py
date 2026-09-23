"""Provider-specific shared-artifact extractors and their registry."""

from __future__ import annotations

from collections.abc import Callable

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.extractors.collector import build_output_record
from backend.normalization.extractors.crt_sh import extract_crt_sh_artifacts
from backend.normalization.extractors.generic import extract_csv_upload_artifacts
from backend.normalization.extractors.generic import extract_manual_input_artifacts
from backend.normalization.extractors.generic import extract_webhook_artifacts
from backend.normalization.extractors.ipinfo import extract_ipinfo_artifacts
from backend.normalization.extractors.nominatim import extract_nominatim_artifacts
from backend.normalization.extractors.opensky import extract_opensky_artifacts
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import ProviderKind

SharedArtifactExtractor = Callable[[NormalizedRecord], NormalizedRecord]

SHARED_EXTRACTOR_BY_PROVIDER: dict[ProviderKind, SharedArtifactExtractor] = {
    ProviderKind.IPINFO: extract_ipinfo_artifacts,
    ProviderKind.CRT_SH: extract_crt_sh_artifacts,
    ProviderKind.NOMINATIM: extract_nominatim_artifacts,
    ProviderKind.OPENSKY: extract_opensky_artifacts,
    ProviderKind.WEBHOOK: extract_webhook_artifacts,
    ProviderKind.CSV_UPLOAD: extract_csv_upload_artifacts,
    ProviderKind.MANUAL_INPUT: extract_manual_input_artifacts,
}

__all__ = [
    "ArtifactCollector",
    "SHARED_EXTRACTOR_BY_PROVIDER",
    "SharedArtifactExtractor",
    "build_bad_normalized_data_record",
    "build_output_record",
]
