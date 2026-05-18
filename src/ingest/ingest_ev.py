import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import EV_2023_PATH, EV_2024_PATH, EV_2025_PATH, PROCESSED_DIR, ensure_directories
from src.db import get_conn
from src.transform.region_mapping import common_region


EV_COLUMNS = [
    "version",
    "region",
    "common_region",
    "aggregate_group",
    "category",
    "parameter",
    "mode",
    "powertrain",
    "year",
    "unit",
    "value",
]


def _load_csv(path, version: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "region": "region",
            "category": "category",
            "parameter": "parameter",
            "mode": "mode",
            "powertrain": "powertrain",
            "year": "year",
            "unit": "unit",
            "value": "value",
        }
    )
    df["version"] = version
    df["aggregate_group"] = None
    return df


def _load_2025(path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="GEVO_EV_2025")
    df = df.rename(
        columns={
            "region_country": "region",
            "category": "category",
            "parameter": "parameter",
            "mode": "mode",
            "powertrain": "powertrain",
            "year": "year",
            "unit": "unit",
            "value": "value",
            "Aggregate group": "aggregate_group",
        }
    )
    df["version"] = "2025"
    return df


def load_ev_data() -> pd.DataFrame:
    frames = [_load_csv(EV_2023_PATH, "2023"), _load_csv(EV_2024_PATH, "2024"), _load_2025(EV_2025_PATH)]
    df = pd.concat(frames, ignore_index=True)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["common_region"] = df["region"].map(common_region)
    return df[EV_COLUMNS].copy()


def ingest_ev() -> pd.DataFrame:
    ensure_directories()
    logging.info("input file loaded: EV data")
    df = load_ev_data()
    db = get_conn()
    try:
        db.write_df("fact_ev", df)
        logging.info("table created: fact_ev row_count=%s", len(df))
    finally:
        db.close()
    df.to_csv(PROCESSED_DIR / "fact_ev.csv", index=False)
    return df


if __name__ == "__main__":
    ingest_ev()
