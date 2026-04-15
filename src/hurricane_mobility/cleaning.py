"""Data cleaning and optimization helpers."""

from __future__ import annotations

import pandas as pd

from .lookups import EXPECTED_COLUMNS


def optimize_google_mobility(
    df: pd.DataFrame,
    expected_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Optimize dtypes and column order for the Google mobility DataFrame.

    Converts name-like columns to ``category``, zero-pads FIPS codes,
    and reorders columns to *expected_columns* + ``year``.
    """
    expected_columns = expected_columns or EXPECTED_COLUMNS
    final_cols = expected_columns + ["year"]
    out = df[[c for c in final_cols if c in df.columns]].copy()

    for col in [
        "country_region_code", "country_region", "sub_region_1",
        "sub_region_2", "metro_area", "iso_3166_2_code", "place_id",
    ]:
        if col in out.columns and out[col].dtype == "string":
            out[col] = out[col].astype("category")

    if "census_fips_code" in out.columns:
        mask = pd.notna(out["census_fips_code"])
        out.loc[mask, "census_fips_code"] = (
            out.loc[mask, "census_fips_code"].str.zfill(5)
        )

    return out
