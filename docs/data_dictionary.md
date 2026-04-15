# Data Dictionary

## Raw Data

### Google COVID-19 Community Mobility Reports

**Files:** `data/raw/google_mobility/2020_US_Region_Mobility_Report.csv` through `2022_...csv`

| Column | Type | Description |
|---|---|---|
| country_region_code | string | ISO 3166-1 alpha-2 country code (always `US`) |
| country_region | string | Country name (always `United States`) |
| sub_region_1 | string | State name (null for national rows) |
| sub_region_2 | string | County name (null for state/national rows) |
| metro_area | string | Metro area (always null in US data) |
| iso_3166_2_code | string | ISO 3166-2 state code (e.g., `US-AL`) |
| census_fips_code | string | 5-digit FIPS code (zero-padded) |
| place_id | string | Google Place ID |
| date | date | Observation date |
| retail_and_recreation_percent_change_from_baseline | Int64 | % change vs Jan-Feb 2020 median |
| grocery_and_pharmacy_percent_change_from_baseline | Int64 | % change vs baseline |
| parks_percent_change_from_baseline | Int64 | % change vs baseline |
| transit_stations_percent_change_from_baseline | Int64 | % change vs baseline |
| workplaces_percent_change_from_baseline | Int64 | % change vs baseline |
| residential_percent_change_from_baseline | Int64 | % change vs baseline |

### BTS Daily Mobility Statistics

**File:** `data/raw/bts_daily_mobility.csv`

| Column | Type | Description |
|---|---|---|
| Geographic Level | string | `State` or `National` |
| Date | string | Date in `YYYY/MM/DD` format |
| State FIPS | string | 2-digit state FIPS code |
| State Postal Code | string | 2-letter postal code |
| Population Staying at Home | Int64 | People not leaving home |
| Population Not Staying at Home | Int64 | People who made at least one trip |
| Number of Trips | Int64 | Total trip count |
| Number of Trips \<1 | Int64 | Trips under 1 mile |
| Number of Trips 1-3 | Int64 | Trips 1-3 miles |
| Number of Trips 3-5 | Int64 | Trips 3-5 miles |
| Number of Trips 5-10 | Int64 | Trips 5-10 miles |
| Number of Trips 10-25 | Int64 | Trips 10-25 miles |
| Number of Trips 25-50 | Int64 | Trips 25-50 miles |
| Number of Trips 50-100 | Int64 | Trips 50-100 miles |
| Number of Trips 100-250 | Int64 | Trips 100-250 miles |
| Number of Trips 250-500 | Int64 | Trips 250-500 miles |
| Number of Trips >=500 | Int64 | Trips 500+ miles |

### Hurricanes in USA 2019-2024

**File:** `data/raw/hurricanes_2019_2024.csv`

| Column | Type | Description |
|---|---|---|
| Year | int | Landfall year |
| Hurricane | string | Storm name |
| Category | int | Saffir-Simpson category at landfall |
| States | string | Affected state(s), comma-separated |
| Landfall date | string | Date of landfall |

### State Population Estimates 2019-2024

Two CSV files from the US Census Bureau Population Estimates Program.

**File 1:** `data/raw/nst-est2019.csv` (Vintage 2019 -- provides 2019 estimate)

- Rows 1-4: multi-row metadata header
- Rows 5-9: national and regional aggregates (to skip)
- Rows 10-60: state rows, names prefixed with `.` (e.g., `.Alabama`)
- Numbers formatted with thousands commas (e.g., `"4,903,185"`)

| Column (row 4 header) | Type | Description |
|---|---|---|
| Geographic Area | string | State name with leading dot |
| 2019 | string | July 1, 2019 population estimate |

**File 2:** `data/raw/NST-EST2024-POP.csv` (Vintage 2024 -- provides 2020-2024 estimates)

- Same layout as File 1

| Column (row 4 header) | Type | Description |
|---|---|---|
| Geographic Area | string | State name with leading dot |
| 2020 through 2024 | string | July 1 population estimates per year |

## Processed Data

All outputs are Apache Parquet files in `data/processed/`.

### us_mobility_2020_2022.parquet

Cleaned Google mobility data (~2.5M rows). Same columns as raw plus `year` (Int64). Name-like columns stored as `category` dtype.

### bts_state_daily.parquet

State-level daily BTS data with computed columns:

| Added Column | Description |
|---|---|
| \<band\> share | Trip count in band / total trips (10 columns) |
| short_distance_share | Sum of bands <= 25 mi / total |
| medium_distance_share | Sum of bands 25-100 mi / total |
| long_distance_share | Sum of bands >= 100 mi / total |

### hurricanes_2019_2024.parquet

One row per hurricane-state pair with columns: `year`, `storm_name`, `landfall_state`, `state_code`, `landfall_date`, `start_date` (landfall - 7d), `end_date` (landfall + 7d).

### state_population_2019_2024.parquet

Long-format annual population: `state_code`, `state`, `year`, `population`.
