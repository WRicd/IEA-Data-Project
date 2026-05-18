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
from src.models.evaluate import regression_metrics


FEATURES = [
    "ev_sales",
    "ev_stock",
    "ev_electricity_twh",
    "ai_capacity_gw",
    "ai_pue",
    "ai_load_factor",
    "cumulative_ccus_capacity_tpa",
    "year",
]


def _design_matrix(df: pd.DataFrame, region_levels=None, scenario_levels=None):
    region_levels = region_levels or sorted(df["common_region"].astype(str).unique())
    scenario_values = (df["ev_scenario"].astype(str) + "|" + df["ai_scenario"].astype(str))
    scenario_levels = scenario_levels or sorted(scenario_values.unique())
    numeric = df[FEATURES].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=float)
    mean = numeric.mean(axis=0)
    std = numeric.std(axis=0)
    std[std == 0] = 1
    numeric = (numeric - mean) / std
    cols = [np.ones(len(df)), numeric]
    for level in region_levels:
        cols.append((df["common_region"].astype(str).to_numpy() == level).astype(float).reshape(-1, 1))
    for level in scenario_levels:
        cols.append((scenario_values.to_numpy() == level).astype(float).reshape(-1, 1))
    return np.column_stack(cols), region_levels, scenario_levels, mean, std


def _predict(df, beta, region_levels, scenario_levels, mean, std):
    scenario_values = df["ev_scenario"].astype(str) + "|" + df["ai_scenario"].astype(str)
    numeric = df[FEATURES].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=float)
    numeric = (numeric - mean) / std
    cols = [np.ones(len(df)), numeric]
    for level in region_levels:
        cols.append((df["common_region"].astype(str).to_numpy() == level).astype(float).reshape(-1, 1))
    for level in scenario_levels:
        cols.append((scenario_values.to_numpy() == level).astype(float).reshape(-1, 1))
    return np.column_stack(cols) @ beta


def train_baseline_regression() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_directories()
    db = get_conn()
    try:
        df = db.read_df("SELECT * FROM ml_region_year_features")
    finally:
        db.close()
    df = df.dropna(subset=["combined_electricity_demand_twh"]).copy()
    if df.empty:
        raise ValueError("ml_region_year_features is empty")
    train = df[df["year"] < df["year"].max()].copy()
    test = df[df["year"] == df["year"].max()].copy()
    if train.empty or test.empty:
        train = df.copy()
        test = df.copy()
    try:
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        from sklearn.linear_model import Ridge

        x_all = pd.get_dummies(df[FEATURES + ["common_region", "ev_scenario", "ai_scenario"]], columns=["common_region", "ev_scenario", "ai_scenario"]).fillna(0)
        x_train = x_all.loc[train.index]
        x_test = x_all.loc[test.index]
        y = train["combined_electricity_demand_twh"].to_numpy(dtype=float)
        models = {
            "Ridge": Ridge(alpha=1.0),
            "RandomForestRegressor": RandomForestRegressor(n_estimators=200, random_state=42, min_samples_leaf=1),
            "GradientBoostingRegressor": GradientBoostingRegressor(random_state=42),
        }
        metric_rows = []
        pred_frames = []
        importance_frames = []
        for name, model in models.items():
            model.fit(x_train, y)
            pred = np.clip(model.predict(x_test), 0, None)
            metric_rows.append({"model": name, **regression_metrics(test["combined_electricity_demand_twh"], pred)})
            pf = test[["common_region", "year", "ev_scenario", "ai_scenario", "combined_electricity_demand_twh"]].copy()
            pf["model"] = name
            pf["prediction"] = pred
            pred_frames.append(pf)
            if hasattr(model, "feature_importances_"):
                importance = model.feature_importances_
            elif hasattr(model, "coef_"):
                importance = np.abs(model.coef_)
            else:
                importance = np.zeros(x_train.shape[1])
            importance_frames.append(pd.DataFrame({"model": name, "feature": x_train.columns, "importance": importance}))
        metrics = pd.DataFrame(metric_rows).sort_values("RMSE")
        predictions = pd.concat(pred_frames, ignore_index=True)
        importance = pd.concat(importance_frames, ignore_index=True).sort_values(["model", "importance"], ascending=[True, False])
        model_label = str(metrics.iloc[0]["model"])
    except Exception:
        x, region_levels, scenario_levels, mean, std = _design_matrix(train)
        y = train["combined_electricity_demand_twh"].to_numpy(dtype=float)
        alpha = 1.0
        penalty = np.eye(x.shape[1]) * alpha
        penalty[0, 0] = 0
        beta = np.linalg.pinv(x.T @ x + penalty) @ x.T @ y
        pred = np.clip(_predict(test, beta, region_levels, scenario_levels, mean, std), 0, None)
        predictions = test[["common_region", "year", "ev_scenario", "ai_scenario", "combined_electricity_demand_twh"]].copy()
        predictions["model"] = "ridge_numpy"
        predictions["prediction"] = pred
        metrics = pd.DataFrame([{"model": "ridge_numpy", **regression_metrics(predictions["combined_electricity_demand_twh"], predictions["prediction"])}])
        importance_rows = []
        for feature in FEATURES:
            corr = df[[feature, "combined_electricity_demand_twh"]].corr(numeric_only=True).iloc[0, 1]
            importance_rows.append({"model": "ridge_numpy", "feature": feature, "importance": abs(float(corr)) if pd.notna(corr) else 0.0})
        importance = pd.DataFrame(importance_rows).sort_values("importance", ascending=False)
        model_label = "ridge_numpy"
    metrics.to_csv(PROCESSED_DIR / "model_regression_metrics.csv", index=False)
    predictions.to_csv(PROCESSED_DIR / "model_regression_predictions.csv", index=False)
    importance.to_csv(PROCESSED_DIR / "model_feature_importance.csv", index=False)
    explainability = predictions.copy()
    explainability["residual"] = explainability["prediction"] - explainability["combined_electricity_demand_twh"]
    explainability["absolute_error"] = explainability["residual"].abs()
    explainability["best_model"] = model_label
    explainability.to_csv(PROCESSED_DIR / "model_explainability.csv", index=False)
    logging.info("model training completed: baseline regression")
    return metrics, predictions


if __name__ == "__main__":
    train_baseline_regression()
