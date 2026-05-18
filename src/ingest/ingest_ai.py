import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import AI_ENERGY_PATH, PROCESSED_DIR, ensure_directories
from src.db import get_conn
from src.transform.region_mapping import common_region
from src.transform.scenario_mapping import normalize_ai_scenario


METRIC_RANGES = {
    "Total installed capacity (GW)": range(5, 14),
    "IT installed capacity (GW)": range(15, 24),
    "Power usage effectiveness": range(30, 39),
    "Load factor (%)": range(40, 49),
    "Total electricity consumption (TWh)": range(56, 65),
    "IT electricity consumption (TWh)": range(66, 75),
}
REGIONAL_YEAR_COLS = {2020: 2, 2023: 3, 2024: 4, 2030: 6}
WORLD_SCENARIO_COLS = {
    ("Historical", 2020): 3,
    ("Historical", 2023): 4,
    ("Historical", 2024): 5,
    ("Base Case", 2030): 7,
    ("Base Case", 2035): 8,
    ("Lift-Off", 2030): 10,
    ("Lift-Off", 2035): 11,
    ("High Efficiency", 2030): 13,
    ("High Efficiency", 2035): 14,
    ("Headwinds", 2030): 16,
    ("Headwinds", 2035): 17,
}


def metric_unit(metric: str) -> str:
    if "(GW)" in metric:
        return "GW"
    if "(TWh)" in metric:
        return "TWh"
    if "(%)" in metric:
        return "percent"
    return "ratio"


def load_ai_energy() -> pd.DataFrame:
    regional = pd.read_excel(AI_ENERGY_PATH, sheet_name="Regional Data", header=None)
    world = pd.read_excel(AI_ENERGY_PATH, sheet_name="World Data", header=None)
    records = []
    for metric, rows in METRIC_RANGES.items():
        for row_idx in rows:
            region = regional.iat[row_idx, 1]
            if pd.isna(region):
                continue
            for year, col_idx in REGIONAL_YEAR_COLS.items():
                value = regional.iat[row_idx, col_idx]
                if not pd.isna(value):
                    records.append(
                        {
                            "region": str(region),
                            "common_region": common_region(region),
                            "metric": metric,
                            "scenario": "Base Case" if year == 2030 else "Historical",
                            "year": int(year),
                            "unit": metric_unit(metric),
                            "value": float(value),
                        }
                    )
    for metric, row_idx in [
        ("Total electricity consumption (TWh)", 23),
        ("IT electricity consumption (TWh)", 27),
        ("Total installed capacity (GW)", 4),
        ("IT installed capacity (GW)", 8),
        ("Power usage effectiveness", 13),
        ("Load factor (%)", 18),
    ]:
        for (scenario, year), col_idx in WORLD_SCENARIO_COLS.items():
            value = world.iat[row_idx, col_idx]
            if not pd.isna(value):
                scenario = normalize_ai_scenario(scenario)
                records.append(
                    {
                        "region": "World",
                        "common_region": "World",
                        "metric": metric,
                        "scenario": scenario if year >= 2030 else "Historical",
                        "year": int(year),
                        "unit": metric_unit(metric),
                        "value": float(value),
                    }
                )
    return pd.DataFrame(records).drop_duplicates()


def ingest_ai() -> pd.DataFrame:
    ensure_directories()
    logging.info("input file loaded: AI energy")
    df = load_ai_energy()
    db = get_conn()
    try:
        db.write_df("fact_ai_energy", df)
        logging.info("table created: fact_ai_energy row_count=%s", len(df))
    finally:
        db.close()
    df.to_csv(PROCESSED_DIR / "fact_ai_energy.csv", index=False)
    return df


if __name__ == "__main__":
    ingest_ai()
