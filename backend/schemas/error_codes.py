"""Shared error codes for the source layer."""

from enum import Enum


class ErrorCode(str, Enum):
    """Short machine-friendly error codes."""

    EMPTY_QUERY = "empty_query"
    BAD_QUERY_TYPE = "bad_query_type"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNSUPPORTED_PROVIDER = "unsupported_provider"
    INVALID_SOURCE_REQUEST = "invalid_source_request"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    UNEXPECTED_SOURCE_ERROR = "unexpected_source_error"
    INVALID_SETTINGS = "invalid_settings"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_NETWORK_ERROR = "provider_network_error"
    PROVIDER_HTTP_ERROR = "provider_http_error"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_BAD_RESPONSE = "provider_bad_response"
    NORMALIZATION_UNSUPPORTED_PROVIDER = "normalization_unsupported_provider"
    NORMALIZATION_BAD_RAW_DATA = "normalization_bad_raw_data"
    STORAGE_SAVE_FAILED = "storage_save_failed"
