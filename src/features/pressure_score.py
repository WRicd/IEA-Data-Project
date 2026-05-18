import json
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS_PATH = ROOT / "config" / "pressure_score_weights.json"


def pressure_class(score: float) -> str:
    if score < 25:
        return "Low Pressure"
    if score < 50:
        return "Medium Pressure"
    if score < 75:
        return "High Pressure"
    return "Critical Pressure"


def add_pressure_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ev_growth_rate"] = out.groupby(["common_region", "ev_scenario"])["ev_electricity_twh"].pct_change().replace([np.inf, -np.inf], np.nan)
    out["ai_growth_rate"] = out.groupby(["common_region", "ai_scenario"])["ai_electricity_twh"].pct_change().replace([np.inf, -np.inf], np.nan)
    for col in ["combined_electricity_demand_twh", "ev_growth_rate", "ai_growth_rate", "ccus_capacity_per_twh_demand"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    weights = {"demand": 0.35, "ev_growth": 0.2, "ai_growth": 0.2, "ccus_buffer": 0.25}
    if WEIGHTS_PATH.exists():
        weights.update(json.loads(WEIGHTS_PATH.read_text(encoding="utf-8")))
    out["demand_pressure_component"] = out["combined_electricity_demand_twh"].rank(pct=True) * 100
    out["ev_growth_pressure_component"] = out["ev_growth_rate"].rank(pct=True) * 100
    out["ai_growth_pressure_component"] = out["ai_growth_rate"].rank(pct=True) * 100
    out["ccus_buffer_component"] = out["ccus_capacity_per_twh_demand"].rank(pct=True) * 100
    raw_score = (
        weights["demand"] * out["demand_pressure_component"]
        + weights["ev_growth"] * out["ev_growth_pressure_component"]
        + weights["ai_growth"] * out["ai_growth_pressure_component"]
        - weights["ccus_buffer"] * out["ccus_buffer_component"]
    )
    if raw_score.max() == raw_score.min():
        out["regional_pressure_score"] = 50.0
    else:
        out["regional_pressure_score"] = (raw_score - raw_score.min()) / (raw_score.max() - raw_score.min()) * 100
    out["regional_pressure_score"] = out["regional_pressure_score"].clip(0, 100)
    out["pressure_class"] = out["regional_pressure_score"].map(pressure_class)
    return out
