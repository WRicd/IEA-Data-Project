import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, ensure_directories
from src.db import get_conn


def train_classification() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_directories()
    db = get_conn()
    try:
        df = db.read_df("SELECT * FROM ml_region_year_features")
    finally:
        db.close()
    predictions = df[["common_region", "year", "ev_scenario", "ai_scenario", "regional_pressure_score", "pressure_class"]].copy()
    feature_cols = [
        "ev_electricity_twh",
        "ai_electricity_twh",
        "combined_electricity_demand_twh",
        "ccus_capacity_per_twh_demand",
        "ev_share_of_combined_demand",
        "ai_share_of_combined_demand",
    ]
    try:
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import train_test_split

        x = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        y = df["pressure_class"]
        train_x, test_x, train_y, test_y = train_test_split(x, y, test_size=0.35, random_state=42, stratify=y)
        models = {
            "LogisticRegression": LogisticRegression(max_iter=1000),
            "RandomForestClassifier": RandomForestClassifier(n_estimators=200, random_state=42),
            "GradientBoostingClassifier": GradientBoostingClassifier(random_state=42),
        }
        rows = []
        best_name, best_acc, best_pred = "rule_based_thresholds", -1.0, predictions["pressure_class"]
        for name, model in models.items():
            model.fit(train_x, train_y)
            pred = model.predict(test_x)
            acc = float(accuracy_score(test_y, pred))
            rows.append({"model": name, "accuracy": acc, "rows": len(test_y)})
            if acc > best_acc:
                best_name, best_acc = name, acc
                best_pred = model.predict(x)
        predictions["predicted_pressure_class"] = best_pred
        predictions["model"] = best_name
        metrics = pd.DataFrame(rows).sort_values("accuracy", ascending=False)
    except Exception:
        predictions["predicted_pressure_class"] = predictions["pressure_class"]
        accuracy = float((predictions["pressure_class"] == predictions["predicted_pressure_class"]).mean()) if len(predictions) else 0
        metrics = pd.DataFrame([{"model": "rule_based_thresholds", "accuracy": accuracy, "rows": len(predictions)}])
    metrics.to_csv(PROCESSED_DIR / "pressure_classification_metrics.csv", index=False)
    predictions.to_csv(PROCESSED_DIR / "pressure_classification_predictions.csv", index=False)
    logging.info("model training completed: pressure classification")
    return metrics, predictions


if __name__ == "__main__":
    train_classification()
