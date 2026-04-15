"""Data loading functions for all raw data sources."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .lookups import (
    DTYPE_SPEC,
    EXPECTED_COLUMNS,
    STATE_ALIAS_TO_FULL,
    STATE_NAME_TO_CODE,
)


# ---------------------------------------------------------------------------
# Google Community Mobility Reports
# ---------------------------------------------------------------------------

def load_us_mobility_csv(path: Path) -> pd.DataFrame:
    """Load a single US mobility CSV with enforced schema and parsed date."""
    df = pd.read_csv(
        path,
        usecols=list(EXPECTED_COLUMNS),
        dtype=dict(DTYPE_SPEC),
        parse_dates=["date"],
    )
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in {path.name}: {missing}")
    return df


def load_all_google_mobility(raw_dir: Path) -> pd.DataFrame:
    """Load and concatenate all US mobility CSVs (2020-2022) from *raw_dir*."""
    csv_files = sorted(
        p for p in raw_dir.glob("*.csv")
        if p.name.startswith(("2020_", "2021_", "2022_"))
    )
    if not csv_files:
        raise FileNotFoundError(f"No mobility CSVs found in {raw_dir}")

    frames: list[pd.DataFrame] = []
    for p in csv_files:
        print(f"Loading {p.name}")
        df = load_us_mobility_csv(p)
        df["year"] = df["date"].dt.year.astype("Int64")
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# BTS Daily Mobility Statistics
# ---------------------------------------------------------------------------

_BTS_USECOLS = [
    "Geographic Level", "Date", "State FIPS", "State Postal Code",
    "Population Staying at Home", "Population Not Staying at Home",
    "Number of Trips", "Number of Trips <1", "Number of Trips 1-3",
    "Number of Trips 3-5", "Number of Trips 5-10", "Number of Trips 10-25",
    "Number of Trips 25-50", "Number of Trips 50-100",
    "Number of Trips 100-250", "Number of Trips 250-500",
    "Number of Trips >=500",
]

_BTS_STR_COLS = {
    "Geographic Level", "Date", "State FIPS", "State Postal Code",
}

_BTS_NUMERIC_COLS = [
    "Population Staying at Home", "Population Not Staying at Home",
    "Number of Trips", "Number of Trips <1", "Number of Trips 1-3",
    "Number of Trips 3-5", "Number of Trips 5-10", "Number of Trips 10-25",
    "Number of Trips 25-50", "Number of Trips 50-100",
    "Number of Trips 100-250", "Number of Trips 250-500",
    "Number of Trips >=500",
]


def load_bts(path: Path) -> pd.DataFrame:
    """Load BTS Daily Mobility CSV, filtered to state-level rows."""
    bts = pd.read_csv(path, usecols=_BTS_USECOLS, dtype="string")
    bts = bts[bts["Geographic Level"] == "State"].copy()
    for col in _BTS_NUMERIC_COLS:
        bts[col] = (
            bts[col]
            .str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
            .astype("Int64")
        )
    bts["date"] = pd.to_datetime(bts["Date"], format="%Y/%m/%d", errors="coerce")
    return bts


# ---------------------------------------------------------------------------
# Hurricanes
# ---------------------------------------------------------------------------

def _parse_landfall_date(raw_text: str, year: int) -> pd.Timestamp | None:
    """Parse a landfall date string, prepending *year* if needed."""
    raw_text = str(raw_text).strip()
    # Try full date first (e.g. "2020-08-27" or "Aug 27, 2020")
    try:
        ts = pd.to_datetime(raw_text, errors="raise")
        if ts.year >= 1900:
            return ts
    except Exception:
        pass
    # "Month Day" text without year (e.g. "July 13", "Sep 6")
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return pd.to_datetime(f"{raw_text} {year}", format=fmt)
        except Exception:
            continue
    return None


def load_hurricanes(path: Path) -> pd.DataFrame:
    """Load hurricane catalogue from CSV or Excel and return tidy DataFrame."""
    if path.suffix in (".xlsx", ".xls"):
        hur = pd.read_excel(path, sheet_name=0)
    else:
        hur = pd.read_csv(path)

    hur.columns = hur.columns.str.strip()
    rename_map = {
        "Year": "year",
        "Hurricane": "storm_name",
        "Hurricane ": "storm_name",
        "States": "landfall_states_raw",
        "Landfall date": "landfall_date_raw",
    }
    hur = hur.rename(columns=rename_map)

    hur["landfall_date"] = hur.apply(
        lambda r: _parse_landfall_date(
            r["landfall_date_raw"],
            int(r["year"]) if pd.notna(r.get("year")) else 0,
        ),
        axis=1,
    )
    hur["landfall_date"] = pd.to_datetime(hur["landfall_date"], errors="coerce")
    hur["start_date"] = hur["landfall_date"] - pd.Timedelta(days=7)
    hur["end_date"] = hur["landfall_date"] + pd.Timedelta(days=7)

    # Split multi-state rows
    if "landfall_states_raw" in hur.columns:
        hur["landfall_states_raw"] = hur["landfall_states_raw"].astype("string")
        hur = hur.assign(
            landfall_state=hur["landfall_states_raw"].str.split(r"[;,]")
        )
        hur = hur.explode("landfall_state", ignore_index=True)
        hur["landfall_state"] = (
            hur["landfall_state"].astype("string").str.strip().str.title()
        )
        hur["landfall_state"] = hur["landfall_state"].replace(STATE_ALIAS_TO_FULL)

    hur["state_code"] = (
        hur["landfall_state"].astype("string").map(STATE_NAME_TO_CODE)
    )

    cols_out = [
        "year", "storm_name", "landfall_state", "state_code",
        "landfall_date", "start_date", "end_date",
    ]
    cols_out = [c for c in cols_out if c in hur.columns]
    return (
        hur[cols_out]
        .dropna(subset=["landfall_state", "landfall_date"])
        .copy()
    )


# ---------------------------------------------------------------------------
# State population  (US Census Bureau CSV files)
# ---------------------------------------------------------------------------

# Title-cased state names used by STATE_NAME_TO_CODE use "Of" while the
# Census Bureau uses "of".  This map handles that and any other mismatches.
_CENSUS_STATE_FIXES: dict[str, str] = {
    "District of Columbia": "District Of Columbia",
}


def _read_census_pop_csv(
    path: Path,
    year_cols: list[str],
) -> pd.DataFrame:
    """Parse a Census Bureau population-estimates CSV.

    Returns a long DataFrame with columns ``state``, ``year``, ``population``.
    """
    raw = pd.read_csv(path, header=None, dtype="string")

    # The header row containing year labels is row index 3 (0-based).
    headers = raw.iloc[3].fillna("").tolist()

    # Map column positions for the requested years
    col_map: dict[str, int] = {}
    for yr in year_cols:
        for ci, h in enumerate(headers):
            if h.strip() == yr:
                col_map[yr] = ci
                break
    missing = [y for y in year_cols if y not in col_map]
    if missing:
        raise ValueError(
            f"Year column(s) {missing} not found in {path.name}. "
            f"Header row: {headers[:10]}"
        )

    # State rows start with a leading dot in column 0
    geo_col = raw.iloc[:, 0].fillna("")
    state_mask = geo_col.str.startswith(".")
    state_df = raw.loc[state_mask].copy()

    # Clean state name: strip dots and whitespace, apply title case
    state_df["state"] = (
        state_df.iloc[:, 0]
        .str.replace(r"^\.+", "", regex=True)
        .str.strip()
    )
    state_df["state"] = state_df["state"].replace(_CENSUS_STATE_FIXES)

    # Melt selected year columns into long format
    frames: list[pd.DataFrame] = []
    for yr, ci in col_map.items():
        chunk = state_df[["state"]].copy()
        chunk["year"] = int(yr)
        pop_str = state_df.iloc[:, ci].str.replace(",", "", regex=False)
        chunk["population"] = pd.to_numeric(pop_str, errors="coerce").astype("Int64")
        frames.append(chunk)

    return pd.concat(frames, ignore_index=True)


def load_population(path_2019: Path, path_2024: Path) -> pd.DataFrame:
    """Load state population estimates from two Census Bureau CSVs.

    *path_2019*: NST-EST2019 CSV (provides July-1 2019 estimates).
    *path_2024*: NST-EST2024-POP CSV (provides July-1 2020-2024 estimates).

    Returns a long DataFrame: ``state_code``, ``state``, ``year``, ``population``
    (one row per state-year, 51 states x 6 years = 306 rows).
    """
    for p in (path_2019, path_2024):
        if not p.exists():
            raise FileNotFoundError(
                f"Population file not found: {p}\n"
                "Please place the Census population CSV at the expected path."
            )

    pop_2019 = _read_census_pop_csv(path_2019, ["2019"])
    pop_2024 = _read_census_pop_csv(path_2024, ["2020", "2021", "2022", "2023", "2024"])

    pop = pd.concat([pop_2019, pop_2024], ignore_index=True)
    pop["state_code"] = pop["state"].map(STATE_NAME_TO_CODE)

    return (
        pop[["state_code", "state", "year", "population"]]
        .dropna(subset=["state_code", "year", "population"])
        .reset_index(drop=True)
        .copy()
    )
