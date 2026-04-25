"""Tests for small shared utility helpers."""

from __future__ import annotations

from datetime import datetime
import math

import pytest

from backend.utils.time import utc_now_iso
from backend.utils.validation import is_valid_aircraft_id
from backend.utils.validation import has_valid_bounding_box
from backend.utils.validation import has_valid_coordinates
from backend.utils.validation import is_valid_domain_name
from backend.utils.validation import is_valid_ipv4_address
from backend.utils.validation import is_valid_place_name
from backend.utils.values import clean_int
from backend.utils.values import clean_text


def test_utc_now_iso_returns_parseable_timestamp() -> None:
    """The timestamp helper should return a real ISO time string."""
    timestamp = utc_now_iso()
    parsed_timestamp = datetime.fromisoformat(timestamp)

    assert parsed_timestamp.tzinfo is not None


def test_clean_text_strips_whitespace() -> None:
    """Text cleaning should strip outer whitespace."""
    assert clean_text("  hello  ") == "hello"


def test_clean_text_returns_empty_string_for_none() -> None:
    """Missing text should become an empty string."""
    assert clean_text(None) == ""


def test_clean_int_uses_default_for_bad_values() -> None:
    """Bad integer inputs should fall back to the default value."""
    assert clean_int("not-a-number", default=12) == 12


def test_clean_int_reads_string_numbers() -> None:
    """String digits should become real integers."""
    assert clean_int("45", default=12) == 45


def test_is_valid_ipv4_address_accepts_real_ipv4() -> None:
    """A normal IPv4 address should pass validation."""
    assert is_valid_ipv4_address("8.8.8.8") is True


def test_is_valid_ipv4_address_rejects_out_of_range_ip() -> None:
    """An out-of-range IPv4 address should fail validation."""
    assert is_valid_ipv4_address("999.8.8.8") is False


def test_is_valid_domain_name_accepts_normal_domain() -> None:
    """A simple domain should pass validation."""
    assert is_valid_domain_name("portal.example.com") is True


def test_is_valid_domain_name_rejects_url_like_value() -> None:
    """A domain validator should reject full URLs."""
    assert is_valid_domain_name("https://portal.example.com") is False


def test_is_valid_domain_name_rejects_ip_address_string() -> None:
    """An IP address should not pass as a domain name."""
    assert is_valid_domain_name("8.8.8.8") is False


def test_is_valid_domain_name_rejects_spaces() -> None:
    """Domains with spaces should fail validation."""
    assert is_valid_domain_name("portal example.com") is False


def test_is_valid_domain_name_rejects_numeric_top_level_label() -> None:
    """A fake domain with a numeric final label should fail validation."""
    assert is_valid_domain_name("portal.example.123") is False


def test_is_valid_aircraft_id_accepts_simple_callsign() -> None:
    """A simple aircraft id should pass validation."""
    assert is_valid_aircraft_id("AAL123") is True


def test_is_valid_aircraft_id_rejects_spaces() -> None:
    """Aircraft ids with spaces should fail validation."""
    assert is_valid_aircraft_id("AAL 123") is False


def test_is_valid_aircraft_id_rejects_control_characters() -> None:
    """Aircraft ids with control characters should fail validation."""
    assert is_valid_aircraft_id("AAL123\n") is False


def test_is_valid_place_name_accepts_simple_city_name() -> None:
    """A normal place name should pass validation."""
    assert is_valid_place_name("Indianapolis") is True


def test_is_valid_place_name_rejects_url_like_value() -> None:
    """A place-name validator should reject URLs."""
    assert is_valid_place_name("https://example.com") is False


def test_is_valid_place_name_rejects_control_characters() -> None:
    """A place-name validator should reject control characters."""
    assert is_valid_place_name("Indy\tTown") is False


def test_has_valid_coordinates_accepts_in_range_values() -> None:
    """Coordinates inside the earth range should pass validation."""
    assert has_valid_coordinates({"lat": 39.7684, "lon": -86.1581}) is True


def test_has_valid_coordinates_rejects_out_of_range_latitude() -> None:
    """Coordinates outside the earth range should fail validation."""
    assert has_valid_coordinates({"lat": 120, "lon": -86.1581}) is False


def test_has_valid_bounding_box_accepts_ordered_bounds() -> None:
    """A bounding box with valid ranges should pass validation."""
    assert has_valid_bounding_box({"lamin": 39.0, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0}) is True


def test_has_valid_coordinates_rejects_nan_values() -> None:
    """NaN coordinate values should fail validation."""
    assert has_valid_coordinates({"lat": math.nan, "lon": -86.1581}) is False


def test_has_valid_coordinates_rejects_infinite_values() -> None:
    """Infinite coordinate values should fail validation."""
    assert has_valid_coordinates({"lat": math.inf, "lon": -86.1581}) is False


def test_has_valid_bounding_box_rejects_reversed_latitude_range() -> None:
    """A bounding box where min is greater than max should fail validation."""
    assert has_valid_bounding_box({"lamin": 40.0, "lamax": 39.0, "lomin": -87.0, "lomax": -86.0}) is False


def test_has_valid_bounding_box_rejects_zero_area_boxes() -> None:
    """A bounding box should describe an area, not a single line."""
    assert has_valid_bounding_box({"lamin": 39.0, "lamax": 39.0, "lomin": -87.0, "lomax": -86.0}) is False


def test_has_valid_bounding_box_rejects_nan_values() -> None:
    """NaN bounding-box values should fail validation."""
    assert has_valid_bounding_box({"lamin": math.nan, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0}) is False


@pytest.mark.parametrize(
    ("validator", "bad_value"),
    [
        (is_valid_ipv4_address, None),
        (is_valid_ipv4_address, object()),
        (is_valid_ipv4_address, []),
        (is_valid_domain_name, None),
        (is_valid_domain_name, {"domain": "example.com"}),
        (is_valid_domain_name, 123),
        (is_valid_aircraft_id, None),
        (is_valid_aircraft_id, {"callsign": "AAL123"}),
        (is_valid_aircraft_id, 12.5),
        (is_valid_place_name, None),
        (is_valid_place_name, {"city": "Indy"}),
        (is_valid_place_name, True),
        (has_valid_coordinates, None),
        (has_valid_coordinates, []),
        (has_valid_coordinates, "39,-86"),
        (has_valid_bounding_box, None),
        (has_valid_bounding_box, []),
        (has_valid_bounding_box, "39,-86,40,-85"),
    ],
)
def test_validation_helpers_fail_safely_for_weird_inputs(validator: object, bad_value: object) -> None:
    """Weird inputs should return False instead of raising exceptions."""
    assert validator(bad_value) is False
