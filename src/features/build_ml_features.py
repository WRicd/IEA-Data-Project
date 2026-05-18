import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, ensure_directories
from src.db import get_conn
from src.features.pressure_score import add_pressure_scores
from src.transform.scenario_mapping import normalize_ai_scenario, normalize_ev_scenario


def build_ev_features(fact_ev: pd.DataFrame) -> pd.DataFrame:
    ev = fact_ev[
        (fact_ev["version"].astype(str) == "2025")
        & fact_ev["category"].isin(["Historical", "Projection-STEPS"])
        & fact_ev["common_region"].notna()
    ].copy()
    ev["ev_scenario"] = ev["category"].map(normalize_ev_scenario)
    keys = ["common_region", "year", "ev_scenario"]

    def sum_filter(parameter, mode=None, powertrain=None):
        subset = ev[ev["parameter"].eq(parameter)]
        if mode is not None:
            subset = subset[subset["mode"].eq(mode)]
        if powertrain is not None:
            subset = subset[subset["powertrain"].eq(powertrain)]
        return subset.groupby(keys)["value"].sum()

    feature = pd.DataFrame(index=ev.groupby(keys).size().index).reset_index()
    series_map = {
        "ev_sales": sum_filter("EV sales"),
        "ev_stock": sum_filter("EV stock"),
        "ev_electricity_twh": sum_filter("Electricity demand") / 1000,
        "ev_sales_cars": sum_filter("EV sales", mode="Cars"),
        "ev_stock_cars": sum_filter("EV stock", mode="Cars"),
        "ev_sales_bev": sum_filter("EV sales", powertrain="BEV"),
        "ev_sales_phev": sum_filter("EV sales", powertrain="PHEV"),
        "ev_sales_fcev": sum_filter("EV sales", powertrain="FCEV"),
    }
    for col, series in series_map.items():
        feature[col] = feature.set_index(keys).index.map(series).fillna(0).to_numpy()
    return feature


def build_ai_features(fact_ai: pd.DataFrame) -> pd.DataFrame:
    ai = fact_ai.copy()
    ai["ai_scenario"] = ai["scenario"].map(normalize_ai_scenario)
    pivot = (
        ai.pivot_table(
            index=["common_region", "year", "ai_scenario"],
            columns="metric",
            values="value",
            aggfunc="sum",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return pivot.rename(
        columns={
            "Total electricity consumption (TWh)": "ai_electricity_twh",
            "IT electricity consumption (TWh)": "ai_it_electricity_twh",
            "Total installed capacity (GW)": "ai_capacity_gw",
            "IT installed capacity (GW)": "ai_it_capacity_gw",
            "Power usage effectiveness": "ai_pue",
            "Load factor (%)": "ai_load_factor",
        }
    )


def build_ccus_features(fact_ccus: pd.DataFrame, min_year: int = 2010, max_year: int = 2035) -> pd.DataFrame:
    ccus = fact_ccus.copy()
    ccus["year"] = pd.to_numeric(ccus["start_year"].fillna(ccus["announced_year"]), errors="coerce").fillna(min_year).astype(int)
    ccus["capacity_tpa"] = pd.to_numeric(ccus["capacity_tpa"], errors="coerce").fillna(0)
    ccus["status_l"] = ccus["status"].astype(str).str.lower()
    rows = []
    regions = sorted(
        set(ccus["common_region"].dropna())
        | set(ccus.get("region_group", pd.Series(dtype=str)).dropna())
        | {"World", "China", "Europe", "North America", "United States", "Asia Pacific", "Middle East"}
    )
    for region in regions:
        if region == "World":
            r = ccus
        else:
            r = ccus[ccus["common_region"].eq(region) | ccus.get("region_group", pd.Series(dtype=str)).eq(region)]
        cumulative = 0.0
        for year in range(min_year, max_year + 1):
            annual = r[r["year"].eq(year)]
            annual_capacity = annual["capacity_tpa"].sum()
            cumulative += annual_capacity
            rows.append(
                {
                    "common_region": region,
                    "year": year,
                    "ccus_project_count": int(len(annual)),
                    "annual_ccus_capacity_tpa": annual_capacity,
                    "annual_ccus_capacity_mtpa": annual_capacity / 1_000_000,
                    "cumulative_ccus_capacity_tpa": cumulative,
                    "cumulative_ccus_capacity_mtpa": cumulative / 1_000_000,
                    "operating_project_count": int(annual["status_l"].str.contains("operat", na=False).sum()),
                    "planned_project_count": int(annual["status_l"].str.contains("plan", na=False).sum()),
                    "under_construction_project_count": int(annual["status_l"].str.contains("construction", na=False).sum()),
                }
            )
    return pd.DataFrame(rows)


def build_ml_features(ev_feature: pd.DataFrame, ai_feature: pd.DataFrame, ccus_feature: pd.DataFrame) -> pd.DataFrame:
    ev_ai = ev_feature.merge(ai_feature, on=["common_region", "year"], how="inner")
    out = ev_ai.merge(ccus_feature, on=["common_region", "year"], how="left")
    ccus_cols = [c for c in ccus_feature.columns if c not in ["common_region", "year"]]
    out[ccus_cols] = out[ccus_cols].fillna(0)
    numeric_cols = [c for c in out.columns if c not in ["common_region", "ev_scenario", "ai_scenario"]]
    out[numeric_cols] = out[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    out["combined_electricity_demand_twh"] = out["ev_electricity_twh"] + out["ai_electricity_twh"]
    denom = out["combined_electricity_demand_twh"].replace(0, np.nan)
    out["ev_share_of_combined_demand"] = (out["ev_electricity_twh"] / denom).fillna(0)
    out["ai_share_of_combined_demand"] = (out["ai_electricity_twh"] / denom).fillna(0)
    out["ccus_capacity_per_twh_demand"] = (out["cumulative_ccus_capacity_tpa"] / denom).fillna(0)
    out["ev_ai_growth_pressure_score"] = 0.0
    out["ccus_buffer_score"] = out["ccus_capacity_per_twh_demand"].rank(pct=True).fillna(0) * 100
    out = add_pressure_scores(out)
    return out


def build_features() -> pd.DataFrame:
    ensure_directories()
    db = get_conn()
    try:
        fact_ev = db.read_df("SELECT * FROM fact_ev")
        fact_ai = db.read_df("SELECT * FROM fact_ai_energy")
        fact_ccus = db.read_df("SELECT * FROM fact_ccus_project")
        ev_feature = build_ev_features(fact_ev)
        ai_feature = build_ai_features(fact_ai)
        ccus_feature = build_ccus_features(fact_ccus)
        ml_feature = build_ml_features(ev_feature, ai_feature, ccus_feature)
        for table_name, df in [
            ("feature_ev_region_year", ev_feature),
            ("feature_ai_region_year", ai_feature),
            ("feature_ccus_region_year", ccus_feature),
            ("ml_region_year_features", ml_feature),
        ]:
            db.write_df(table_name, df)
            df.to_csv(PROCESSED_DIR / f"{table_name}.csv", index=False)
            logging.info("table created: %s row_count=%s", table_name, len(df))
    finally:
        db.close()
    return ml_feature


if __name__ == "__main__":
    build_features()
