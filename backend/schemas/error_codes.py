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
