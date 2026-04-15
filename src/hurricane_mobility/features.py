"""Feature engineering: distance-band shares, per-capita metrics, baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .lookups import BAND_SPECS


# ---------------------------------------------------------------------------
# BTS distance-band shares
# ---------------------------------------------------------------------------

_TRIP_COLS = [
    "Number of Trips <1", "Number of Trips 1-3", "Number of Trips 3-5",
    "Number of Trips 5-10", "Number of Trips 10-25", "Number of Trips 25-50",
    "Number of Trips 50-100", "Number of Trips 100-250",
    "Number of Trips 250-500", "Number of Trips >=500",
]

_LD_COLS = [
    "Number of Trips 100-250", "Number of Trips 250-500",
    "Number of Trips >=500",
]
_MD_COLS = ["Number of Trips 25-50", "Number of Trips 50-100"]
_SD_COLS = [
    "Number of Trips <1", "Number of Trips 1-3", "Number of Trips 3-5",
    "Number of Trips 5-10", "Number of Trips 10-25",
]


def compute_distance_band_shares(bts: pd.DataFrame) -> pd.DataFrame:
    """Add per-band trip shares and short/medium/long aggregates to *bts*."""
    bts = bts.copy()
    bts["trips_total"] = bts["Number of Trips"].astype("float64")
    for c in _TRIP_COLS:
        bts[c + " share"] = (
            bts[c].astype("float64") / bts["trips_total"]
        ).replace([np.inf, -np.inf], np.nan)

    bts["long_distance_share"] = (
        bts[_LD_COLS].astype("float64").sum(axis=1) / bts["trips_total"]
    )
    bts["medium_distance_share"] = (
        bts[_MD_COLS].astype("float64").sum(axis=1) / bts["trips_total"]
    )
    bts["short_distance_share"] = (
        bts[_SD_COLS].astype("float64").sum(axis=1) / bts["trips_total"]
    )

    keep = (
        ["date", "State FIPS", "State Postal Code",
         "Population Staying at Home", "Population Not Staying at Home",
         "Number of Trips",
         "long_distance_share", "medium_distance_share",
         "short_distance_share"]
        + [c + " share" for c in _TRIP_COLS]
    )
    return bts[keep].copy()


# ---------------------------------------------------------------------------
# Population join and per-capita metrics
# ---------------------------------------------------------------------------

def join_population(bts: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """Merge population into BTS on ``(state_code, year)``."""
    bts = bts.copy()
    bts["date"] = pd.to_datetime(bts["date"], errors="coerce")
    bts["year"] = bts["date"].dt.year

    if "State Postal Code" in bts.columns:
        bts["state_code"] = bts["State Postal Code"].astype("string")

    pop = pop.copy()
    pop["year"] = pd.to_numeric(pop["year"], errors="coerce")
    pop["state_code"] = pop["state_code"].astype("string")

    bts["year"] = bts["year"].astype("Int64")
    pop["year"] = pop["year"].astype("Int64")

    bts = bts.merge(
        pop[["state_code", "year", "population"]],
        on=["state_code", "year"],
        how="left",
    )
    return bts


def compute_per_capita_metrics(bts: pd.DataFrame) -> pd.DataFrame:
    """Add trips_per_1000, stay_home_share, and per-band per-1000 columns."""
    bts = bts.copy()
    valid = (
        bts["population"].notna()
        & bts["Number of Trips"].notna()
        & (bts["population"] > 0)
    )
    pop = bts.loc[valid, "population"].astype("float64")
    trips = bts.loc[valid, "Number of Trips"].astype("float64")

    bts.loc[valid, "trips_per_1000"] = (trips / pop) * 1000.0
    bts.loc[valid, "stay_home_share"] = (
        bts.loc[valid, "Population Staying at Home"].astype("float64") / pop
    )
    bts.loc[valid, "not_stay_home_share"] = (
        bts.loc[valid, "Population Not Staying at Home"].astype("float64") / pop
    )

    for key, share_col, _label in BAND_SPECS:
        per1000_col = f"{key}_per_1000"
        share_valid = valid & bts[share_col].notna()
        bts.loc[share_valid, per1000_col] = (
            bts.loc[share_valid, share_col].astype("float64")
            * bts.loc[share_valid, "Number of Trips"].astype("float64")
            / bts.loc[share_valid, "population"].astype("float64")
        ) * 1000.0

    # Aggregate short/medium/long per-1000
    bts.loc[valid, "short_trips_per_1000"] = (
        bts.loc[valid, "short_distance_share"].astype("float64") * trips / pop
    ) * 1000.0
    bts.loc[valid, "medium_trips_per_1000"] = (
        bts.loc[valid, "medium_distance_share"].astype("float64") * trips / pop
    ) * 1000.0
    bts.loc[valid, "long_trips_per_1000"] = (
        bts.loc[valid, "long_distance_share"].astype("float64") * trips / pop
    ) * 1000.0

    return bts


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def weighted_mean(series: pd.Series, weights: pd.Series) -> float:
    """Population-weighted mean, ignoring NaN pairs."""
    mask = series.notna() & weights.notna()
    w = weights[mask]
    if w.sum() == 0:
        return float("nan")
    return float((series[mask] * w).sum() / w.sum())


# ---------------------------------------------------------------------------
# Baseline construction for hurricane-day comparison
# ---------------------------------------------------------------------------

def build_state_baseline(
    bts: pd.DataFrame,
    hur: pd.DataFrame,
    st_code: str,
) -> pd.DataFrame:
    """Return BTS rows for *st_code* excluding +/-3 days around any landfall."""
    state_df = bts[bts["state_code"] == st_code].copy()
    state_df["date"] = pd.to_datetime(state_df["date"])

    exclude = pd.Series(False, index=state_df.index)
    hur_st = hur.dropna(subset=["state_code", "landfall_date"])
    hur_st = hur_st[hur_st["state_code"].astype("string") == st_code]
    for _, r in hur_st.iterrows():
        lf = pd.to_datetime(r["landfall_date"])
        exclude |= state_df["date"].between(
            lf - pd.Timedelta(days=3), lf + pd.Timedelta(days=3)
        )
    return state_df.loc[~exclude].copy()


def compute_baseline_series(
    bts: pd.DataFrame,
    hur: pd.DataFrame,
    st_code: str,
    start_md: str,
    end_md: str,
    exclude_year: int,
    yoy_years: list[int],
    share_metrics: list[str] | None = None,
    band_ratio_metrics: list[str] | None = None,
) -> dict[str, pd.Series]:
    """MM-DD mean baseline across *yoy_years* excluding *exclude_year*."""
    share_metrics = share_metrics or ["stay_home_share", "not_stay_home_share"]
    band_ratio_metrics = band_ratio_metrics or [
        "short_trips_per_1000", "medium_trips_per_1000", "long_trips_per_1000",
    ]
    baseline = build_state_baseline(bts, hur, st_code)
    idx_any = pd.date_range(
        pd.Timestamp(f"{exclude_year}-{start_md}"),
        pd.Timestamp(f"{exclude_year}-{end_md}"),
        freq="D",
    )
    mmdd = [(d.month, d.day) for d in idx_any]
    all_metrics = share_metrics + band_ratio_metrics + ["trips_per_1000"]

    results: dict[str, pd.Series] = {}
    for m in all_metrics:
        vals = []
        for mm, dd in mmdd:
            years = [y for y in yoy_years if y != exclude_year]
            per_day: list[float] = []
            for y in years:
                d = pd.Timestamp(y, mm, dd)
                row = baseline.loc[baseline["date"] == d]
                if row.empty or m not in row.columns:
                    continue
                if m in band_ratio_metrics:
                    den = row["trips_per_1000"].astype("float64")
                    with np.errstate(divide="ignore", invalid="ignore"):
                        val = (
                            row[m].astype("float64") / den
                        ).replace([np.inf, -np.inf], np.nan)
                    per_day.append(float(val.values[0]))
                else:
                    per_day.append(float(row[m].astype("float64").values[0]))
            vals.append(np.nanmean(per_day) if per_day else np.nan)
        results[m] = pd.Series(
            vals,
            index=pd.DatetimeIndex(
                [pd.Timestamp(2001, mm, dd) for mm, dd in mmdd]
            ),
        )
    return results
