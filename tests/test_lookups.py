"""Smoke tests for lookup tables and constants."""

from hurricane_mobility.lookups import (
    BAND_SPECS,
    EXPECTED_COLUMNS,
    GOOGLE_METRICS,
    STATE_CODE_TO_NAME,
    STATE_NAME_TO_CODE,
)


def test_state_codes_count():
    assert len(STATE_NAME_TO_CODE) == 51  # 50 states + DC


def test_state_codes_are_two_letters():
    for code in STATE_NAME_TO_CODE.values():
        assert len(code) == 2 and code.isalpha() and code.isupper()


def test_state_codes_unique():
    codes = list(STATE_NAME_TO_CODE.values())
    assert len(codes) == len(set(codes))


def test_reverse_mapping_roundtrips():
    for name, code in STATE_NAME_TO_CODE.items():
        assert STATE_CODE_TO_NAME[code] == name


def test_band_specs_length():
    assert len(BAND_SPECS) == 10


def test_expected_columns_length():
    assert len(EXPECTED_COLUMNS) == 15


def test_google_metrics_length():
    assert len(GOOGLE_METRICS) == 6
