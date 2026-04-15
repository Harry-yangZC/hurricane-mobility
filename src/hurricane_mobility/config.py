from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
GOOGLE_MOBILITY_DIR = RAW_DIR / "google_mobility"
BTS_CSV = RAW_DIR / "bts_daily_mobility.csv"
HURRICANES_CSV = RAW_DIR / "hurricanes_2019_2024.csv"
POP_2019_CSV = RAW_DIR / "nst-est2019.csv"
POP_2024_CSV = RAW_DIR / "NST-EST2024-POP.csv"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"


def ensure_dirs() -> None:
    """Create output directories if they do not exist."""
    for d in (PROCESSED_DIR, FIGURES_DIR, TABLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
