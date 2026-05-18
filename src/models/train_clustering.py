import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, RESULTS_DIR, ensure_directories
from src.db import get_conn


CLUSTER_FEATURES = [
    "ev_electricity_twh",
    "ai_electricity_twh",
    "combined_electricity_demand_twh",
    "ccus_capacity_per_twh_demand",
    "ev_share_of_combined_demand",
    "ai_share_of_combined_demand",
    "regional_pressure_score",
]


def _kmeans(x: np.ndarray, k: int = 4, iterations: int = 50):
    rng = np.random.default_rng(42)
    k = min(k, len(x))
    centers = x[rng.choice(len(x), size=k, replace=False)]
    labels = np.zeros(len(x), dtype=int)
    for _ in range(iterations):
        dist = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dist.argmin(axis=1)
        new_centers = np.array([x[labels == i].mean(axis=0) if np.any(labels == i) else centers[i] for i in range(k)])
        if np.allclose(new_centers, centers):
            break
        centers = new_centers
    return labels


def train_clustering() -> pd.DataFrame:
    ensure_directories()
    db = get_conn()
    try:
        df = db.read_df("SELECT * FROM ml_region_year_features")
    finally:
        db.close()
    focus = df[df["year"].eq(df["year"].max())].copy()
    if focus.empty:
        focus = df.copy()
    x = focus[CLUSTER_FEATURES].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=float)
    std = x.std(axis=0)
    std[std == 0] = 1
    x_scaled = (x - x.mean(axis=0)) / std
    try:
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA

        labels = KMeans(n_clusters=min(4, len(x_scaled)), random_state=42, n_init=10).fit_predict(x_scaled)
        coords = PCA(n_components=2, random_state=42).fit_transform(x_scaled)
    except Exception:
        labels = _kmeans(x_scaled, k=4)
        coords = x_scaled[:, :2] if x_scaled.shape[1] >= 2 else np.column_stack([x_scaled[:, 0], np.zeros(len(x_scaled))])
    clusters = focus[["common_region", "year", "ev_scenario", "ai_scenario"] + CLUSTER_FEATURES].copy()
    clusters["cluster"] = labels
    clusters["pca_x"] = coords[:, 0]
    clusters["pca_y"] = coords[:, 1]
    clusters.to_csv(PROCESSED_DIR / "region_clusters.csv", index=False)
    _write_cluster_html(clusters)
    logging.info("model training completed: clustering")
    return clusters


def _write_cluster_html(clusters: pd.DataFrame) -> None:
    rows = "\n".join(
        f"<tr><td>{r.common_region}</td><td>{r.year}</td><td>{r.cluster}</td><td>{r.regional_pressure_score:.1f}</td><td>{r.combined_electricity_demand_twh:.1f}</td></tr>"
        for r in clusters.sort_values("regional_pressure_score", ascending=False).itertuples()
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Cluster Scatter</title>
<style>body{{font-family:Arial;margin:24px}}table{{border-collapse:collapse}}td,th{{padding:8px 10px;border-bottom:1px solid #ddd}}</style></head>
<body><h1>Regional Cluster Summary</h1><table><thead><tr><th>Region</th><th>Year</th><th>Cluster</th><th>Pressure</th><th>Demand TWh</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""
    (RESULTS_DIR / "cluster_scatter.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    train_clustering()
