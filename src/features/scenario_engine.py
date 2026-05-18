import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, ensure_directories
from src.db import get_conn
from src.features.pressure_score import pressure_class


CCUS_SCENARIO_MULTIPLIER = {
    "operating_only": 0.45,
    "active_projects": 0.75,
    "all_announced": 1.0,
}


def build_scenarios() -> pd.DataFrame:
    ensure_directories()
    db = get_conn()
    try:
        base = db.read_df("SELECT * FROM ml_region_year_features")
    finally:
        db.close()
    frames = []
    for scenario, multiplier in CCUS_SCENARIO_MULTIPLIER.items():
        df = base.copy()
        df["ccus_scenario"] = scenario
        df["ccus_capacity_tpa"] = df["cumulative_ccus_capacity_tpa"] * multiplier
        df["ccus_capacity_mtpa"] = df["cumulative_ccus_capacity_mtpa"] * multiplier
        denom = df["combined_electricity_demand_twh"].replace(0, pd.NA)
        df["ccus_buffer_ratio"] = (df["ccus_capacity_tpa"] / denom).fillna(0)
        # Re-score within each scenario while preserving demand/growth components from the feature table.
        raw = (
            df["demand_pressure_component"] * 0.35
            + df["ev_growth_pressure_component"] * 0.2
            + df["ai_growth_pressure_component"] * 0.2
            - df["ccus_buffer_ratio"].rank(pct=True).fillna(0) * 100 * 0.25
        )
        if raw.max() == raw.min():
            df["regional_pressure_score"] = 50.0
        else:
            df["regional_pressure_score"] = (raw - raw.min()) / (raw.max() - raw.min()) * 100
        df["regional_pressure_score"] = df["regional_pressure_score"].clip(0, 100)
        df["pressure_class"] = df["regional_pressure_score"].map(pressure_class)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    wanted = [
        "common_region",
        "year",
        "ev_scenario",
        "ai_scenario",
        "ccus_scenario",
        "ev_electricity_twh",
        "ai_electricity_twh",
        "combined_electricity_demand_twh",
        "ccus_capacity_tpa",
        "ccus_capacity_mtpa",
        "ccus_buffer_ratio",
        "regional_pressure_score",
        "pressure_class",
    ]
    out[wanted].to_csv(PROCESSED_DIR / "scenario_region_year_features.csv", index=False)
    comp = out[out["year"].eq(2030)].copy()
    comp["scenario_name"] = comp["ev_scenario"] + " / " + comp["ai_scenario"] + " / " + comp["ccus_scenario"]
    comp["rank"] = comp.groupby("scenario_name")["regional_pressure_score"].rank(ascending=False, method="dense").astype(int)
    comp_out = comp[
        [
            "common_region",
            "scenario_name",
            "combined_electricity_demand_twh",
            "ccus_buffer_ratio",
            "regional_pressure_score",
            "pressure_class",
            "rank",
        ]
    ].sort_values(["scenario_name", "rank"])
    comp_out.to_csv(PROCESSED_DIR / "scenario_comparison_2030.csv", index=False)
    db = get_conn()
    try:
        db.write_df("scenario_region_year_features", out[wanted])
        db.write_df("scenario_comparison_2030", comp_out)
    finally:
        db.close()
    return out[wanted]


if __name__ == "__main__":
    build_scenarios()
