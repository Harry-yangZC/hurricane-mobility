"""Shared constants and lookup tables used across the pipeline."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Google Community Mobility Reports -- schema
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS: list[str] = [
    "country_region_code",
    "country_region",
    "sub_region_1",
    "sub_region_2",
    "metro_area",
    "iso_3166_2_code",
    "census_fips_code",
    "place_id",
    "date",
    "retail_and_recreation_percent_change_from_baseline",
    "grocery_and_pharmacy_percent_change_from_baseline",
    "parks_percent_change_from_baseline",
    "transit_stations_percent_change_from_baseline",
    "workplaces_percent_change_from_baseline",
    "residential_percent_change_from_baseline",
]

DTYPE_SPEC: dict[str, str] = {
    "country_region_code": "string",
    "country_region": "string",
    "sub_region_1": "string",
    "sub_region_2": "string",
    "metro_area": "string",
    "iso_3166_2_code": "string",
    "census_fips_code": "string",
    "place_id": "string",
    "retail_and_recreation_percent_change_from_baseline": "Int64",
    "grocery_and_pharmacy_percent_change_from_baseline": "Int64",
    "parks_percent_change_from_baseline": "Int64",
    "transit_stations_percent_change_from_baseline": "Int64",
    "workplaces_percent_change_from_baseline": "Int64",
    "residential_percent_change_from_baseline": "Int64",
}

GOOGLE_METRICS: list[str] = [
    "retail_and_recreation_percent_change_from_baseline",
    "grocery_and_pharmacy_percent_change_from_baseline",
    "parks_percent_change_from_baseline",
    "transit_stations_percent_change_from_baseline",
    "workplaces_percent_change_from_baseline",
    "residential_percent_change_from_baseline",
]

# ---------------------------------------------------------------------------
# BTS Daily Mobility Statistics -- columns to plot
# ---------------------------------------------------------------------------

BTS_METRICS: list[str] = [
    "Number of Trips",
    "Population Staying at Home",
    "Population Not Staying at Home",
    "long_distance_share",
    "medium_distance_share",
    "short_distance_share",
]

# ---------------------------------------------------------------------------
# Distance-band specs for per-capita trip analysis
# ---------------------------------------------------------------------------

BAND_SPECS: list[tuple[str, str, str]] = [
    ("lt1", "Number of Trips <1 share", "<1 mi"),
    ("1_3", "Number of Trips 1-3 share", "1\u20133 mi"),
    ("3_5", "Number of Trips 3-5 share", "3\u20135 mi"),
    ("5_10", "Number of Trips 5-10 share", "5\u201310 mi"),
    ("10_25", "Number of Trips 10-25 share", "10\u201325 mi"),
    ("25_50", "Number of Trips 25-50 share", "25\u201350 mi"),
    ("50_100", "Number of Trips 50-100 share", "50\u2013100 mi"),
    ("100_250", "Number of Trips 100-250 share", "100\u2013250 mi"),
    ("250_500", "Number of Trips 250-500 share", "250\u2013500 mi"),
    ("500_plus", "Number of Trips >=500 share", "\u2265500 mi"),
]

BAND_PER1000_COLS: list[str] = [f"{k}_per_1000" for k, _, _ in BAND_SPECS]
BAND_LABELS: dict[str, str] = {f"{k}_per_1000": lab for k, _, lab in BAND_SPECS}

# ---------------------------------------------------------------------------
# State name / code lookups (single source of truth)
# ---------------------------------------------------------------------------

STATE_NAME_TO_CODE: dict[str, str] = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District Of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

STATE_CODE_TO_NAME: dict[str, str] = {v: k for k, v in STATE_NAME_TO_CODE.items()}

STATE_ALIAS_TO_FULL: dict[str, str] = {
    "N Carolina": "North Carolina",
    "S Carolina": "South Carolina",
    "N Dakota": "North Dakota",
    "S Dakota": "South Dakota",
    "W Virginia": "West Virginia",
}

# ---------------------------------------------------------------------------
# Census regions (state ordering for heatmaps)
# ---------------------------------------------------------------------------

CENSUS_REGIONS: dict[str, list[str]] = {
    "Northeast": [
        "Connecticut", "Maine", "Massachusetts", "New Hampshire",
        "Rhode Island", "Vermont", "New Jersey", "New York", "Pennsylvania",
    ],
    "Midwest": [
        "Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin",
        "Iowa", "Kansas", "Minnesota", "Missouri", "Nebraska",
        "North Dakota", "South Dakota",
    ],
    "South": [
        "Delaware", "District of Columbia", "Florida", "Georgia",
        "Maryland", "North Carolina", "South Carolina", "Virginia",
        "West Virginia", "Alabama", "Kentucky", "Mississippi", "Tennessee",
        "Arkansas", "Louisiana", "Oklahoma", "Texas",
    ],
    "West": [
        "Arizona", "Colorado", "Idaho", "Montana", "Nevada",
        "New Mexico", "Utah", "Wyoming", "Alaska", "California",
        "Hawaii", "Oregon", "Washington",
    ],
}
