"""Smoke tests for feature engineering functions."""

import numpy as np
import pandas as pd

from hurricane_mobility.features import compute_distance_band_shares, weighted_mean


def test_weighted_mean_basic():
    s = pd.Series([10.0, 20.0, 30.0])
    w = pd.Series([1.0, 1.0, 1.0])
    assert weighted_mean(s, w) == 20.0


def test_weighted_mean_with_nan():
    s = pd.Series([10.0, np.nan, 30.0])
    w = pd.Series([1.0, 1.0, 1.0])
    assert weighted_mean(s, w) == 20.0


def test_distance_band_shares_sum_near_one():
    bts = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=3),
        "State FIPS": ["01"] * 3,
        "State Postal Code": ["AL"] * 3,
        "Population Staying at Home": [100] * 3,
        "Population Not Staying at Home": [900] * 3,
        "Number of Trips": [1000] * 3,
        "Number of Trips <1": [100] * 3,
        "Number of Trips 1-3": [200] * 3,
        "Number of Trips 3-5": [150] * 3,
        "Number of Trips 5-10": [150] * 3,
        "Number of Trips 10-25": [100] * 3,
        "Number of Trips 25-50": [100] * 3,
        "Number of Trips 50-100": [50] * 3,
        "Number of Trips 100-250": [80] * 3,
        "Number of Trips 250-500": [50] * 3,
        "Number of Trips >=500": [20] * 3,
    })
    for c in bts.columns:
        if c.startswith("Number of") or c.startswith("Population"):
            bts[c] = bts[c].astype("Int64")
    result = compute_distance_band_shares(bts)
    total = (
        result["short_distance_share"]
        + result["medium_distance_share"]
        + result["long_distance_share"]
    )
    np.testing.assert_allclose(total.values, 1.0, atol=1e-10)
