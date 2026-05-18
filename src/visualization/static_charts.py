from html import escape
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, RESULTS_DIR, ensure_directories
from src.db import get_conn


def _svg(width, height, title, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fff"/><text x="{width/2:.0f}" y="32" text-anchor="middle" font-family="Arial" font-size="20" font-weight="700" fill="#222">{escape(title)}</text>{body}</svg>'


def _bar_svg(df, label_col, value_col, title, path, color="#2f6f73", width=920, height=520):
    df = df[[label_col, value_col]].dropna().sort_values(value_col, ascending=False).head(12)
    left, top, plot_w, bar_h, gap = 190, 60, 650, 24, 10
    max_v = max(float(df[value_col].max()), 1)
    body = []
    for i, row in enumerate(df.itertuples(index=False)):
        label, value = str(row[0]), float(row[1])
        y = top + i * (bar_h + gap)
        w = value / max_v * plot_w
        body.append(f'<text x="{left-8}" y="{y+17}" text-anchor="end" font-family="Arial" font-size="12" fill="#333">{escape(label)}</text>')
        body.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" fill="{color}"/>')
        body.append(f'<text x="{left+w+6:.1f}" y="{y+17}" font-family="Arial" font-size="12" fill="#333">{value:,.1f}</text>')
    path.write_text(_svg(width, height, title, "\n".join(body)), encoding="utf-8")


def _scatter_svg(df, path):
    focus = df[df["year"].eq(2030)].copy()
    if focus.empty:
        focus = df.copy()
    width, height = 920, 560
    left, top, plot_w, plot_h = 90, 70, 680, 380
    x = focus["combined_electricity_demand_twh"].astype(float)
    y = focus["regional_pressure_score"].astype(float)
    x_max = max(x.max() * 1.1, 1)
    body = [f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fbfbfb" stroke="#ddd"/>']
    for r in focus.itertuples():
        cx = left + float(r.combined_electricity_demand_twh) / x_max * plot_w
        cy = top + plot_h - float(r.regional_pressure_score) / 100 * plot_h
        color = "#b94e48" if r.regional_pressure_score >= 75 else "#d1893b" if r.regional_pressure_score >= 50 else "#2f6f73"
        body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{color}" opacity="0.82"/>')
        body.append(f'<text x="{cx+12:.1f}" y="{cy+4:.1f}" font-family="Arial" font-size="11" fill="#333">{escape(str(r.common_region))}</text>')
    body.append(f'<text x="{left+plot_w/2:.0f}" y="{top+plot_h+42}" text-anchor="middle" font-family="Arial" font-size="13">Combined electricity demand (TWh)</text>')
    body.append(f'<text x="{left-55}" y="{top+plot_h/2:.0f}" text-anchor="middle" font-family="Arial" font-size="13" transform="rotate(-90 {left-55},{top+plot_h/2:.0f})">Pressure score</text>')
    path.write_text(_svg(width, height, "2030 combined demand vs regional pressure", "\n".join(body)), encoding="utf-8")


def generate_static_dashboard() -> None:
    ensure_directories()
    db = get_conn()
    try:
        ml = db.read_df("SELECT * FROM ml_region_year_features")
        ccus = db.read_df("SELECT * FROM feature_ccus_region_year")
        clusters = pd.read_csv(PROCESSED_DIR / "region_clusters.csv") if (PROCESSED_DIR / "region_clusters.csv").exists() else pd.DataFrame()
        metadata = db.read_df("SELECT * FROM pipeline_metadata") if db.table_exists("pipeline_metadata") else pd.DataFrame()
    finally:
        db.close()
    focus = ml[ml["year"].eq(2030)].copy()
    if focus.empty:
        focus = ml.copy()
    _bar_svg(focus, "common_region", "regional_pressure_score", "EV-AI-CCUS pressure ranking", RESULTS_DIR / "ev_ai_ccus_pressure_ranking.svg", "#b94e48")
    _scatter_svg(ml, RESULTS_DIR / "ev_ai_ccus_2030_scatter.svg")
    ccus_2030 = ccus[ccus["year"].eq(2030)]
    _bar_svg(ccus_2030, "common_region", "cumulative_ccus_capacity_mtpa", "CCUS cumulative capacity by region", RESULTS_DIR / "ccus_capacity_by_region.svg", "#6f5a9c")
    _bar_svg(focus, "common_region", "regional_pressure_score", "Regional pressure score", RESULTS_DIR / "regional_pressure_score.svg", "#d1893b")
    _bar_svg(focus, "common_region", "combined_electricity_demand_twh", "Scenario comparison: EV + AI demand", RESULTS_DIR / "scenario_comparison.svg", "#5c6b73")
    _write_supporting_html(focus, clusters)
    _write_dashboard(focus, clusters, metadata)


def _write_supporting_html(focus: pd.DataFrame, clusters: pd.DataFrame) -> None:
    def write_table(path, title, df):
        html = df.to_html(index=False, classes="table", border=0)
        path.write_text(
            f"""<!doctype html><html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:Arial;margin:24px}}table{{border-collapse:collapse}}td,th{{padding:8px 10px;border-bottom:1px solid #ddd;text-align:right}}td:first-child,th:first-child{{text-align:left}}</style></head>
<body><h1>{escape(title)}</h1>{html}</body></html>""",
            encoding="utf-8",
        )

    write_table(RESULTS_DIR / "pressure_ranking_2030.html", "2030 Pressure Ranking", focus.sort_values("regional_pressure_score", ascending=False))
    write_table(RESULTS_DIR / "ccus_buffer_ratio_2030.html", "2030 CCUS Buffer Ratio", focus.sort_values("ccus_capacity_per_twh_demand", ascending=False))
    scenario_path = PROCESSED_DIR / "scenario_comparison_2030.csv"
    if scenario_path.exists():
        write_table(RESULTS_DIR / "scenario_comparison_2030.html", "2030 Scenario Comparison", pd.read_csv(scenario_path).head(80))
    importance_path = PROCESSED_DIR / "model_feature_importance.csv"
    if importance_path.exists():
        write_table(RESULTS_DIR / "feature_importance.html", "Model Feature Importance", pd.read_csv(importance_path))


def _write_dashboard(focus: pd.DataFrame, clusters: pd.DataFrame, metadata: pd.DataFrame) -> None:
    quality_path = PROCESSED_DIR / "data_quality_report.csv"
    quality = pd.read_csv(quality_path) if quality_path.exists() else pd.DataFrame()
    backend = metadata["backend"].iloc[-1] if not metadata.empty and "backend" in metadata else "unknown"
    run_time = metadata["created_at"].iloc[-1] if not metadata.empty and "created_at" in metadata else ""
    quality_summary = ", ".join(f"{k}: {v}" for k, v in quality["status"].value_counts().to_dict().items()) if not quality.empty else "not run"
    cards = [
        ("Database backend", str(backend)),
        ("Pipeline timestamp", str(run_time)),
        ("Quality summary", quality_summary),
        ("Regions", str(focus["common_region"].nunique())),
        ("Rows", f"{len(focus):,}"),
        ("Max pressure", f"{focus['regional_pressure_score'].max():.1f}"),
        ("Max demand TWh", f"{focus['combined_electricity_demand_twh'].max():.1f}"),
    ]
    card_html = "".join(f'<div class="card"><span>{escape(k)}</span><strong>{escape(v)}</strong></div>' for k, v in cards)
    rows = "".join(
        f"<tr><td>{escape(str(r.common_region))}</td><td>{r.ev_electricity_twh:,.1f}</td><td>{r.ai_electricity_twh:,.1f}</td><td>{r.combined_electricity_demand_twh:,.1f}</td><td>{r.ccus_capacity_per_twh_demand:,.1f}</td><td>{r.regional_pressure_score:.1f}</td><td>{escape(str(r.pressure_class))}</td></tr>"
        for r in focus.sort_values("regional_pressure_score", ascending=False).itertuples()
    )
    cluster_rows = ""
    if not clusters.empty:
        cluster_rows = "".join(
            f"<tr><td>{escape(str(r.common_region))}</td><td>{int(r.cluster)}</td><td>{r.regional_pressure_score:.1f}</td></tr>"
            for r in clusters.sort_values("regional_pressure_score", ascending=False).head(30).itertuples()
        )
    figures = [
        "ev_ai_ccus_pressure_ranking.svg",
        "ev_ai_ccus_2030_scatter.svg",
        "ccus_capacity_by_region.svg",
        "regional_pressure_score.svg",
        "scenario_comparison.svg",
    ]
    figure_html = "".join(f'<section><img src="{name}" alt="{name}"></section>' for name in figures)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>EV-AI-CCUS Dashboard</title>
<style>body{{font-family:Arial;margin:0;background:#f6f7f5;color:#222}}header{{background:#fff;padding:28px 34px;border-bottom:1px solid #ddd}}main{{max-width:1180px;margin:auto;padding:24px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card,section{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px;margin:14px 0}}.card span{{display:block;color:#666;font-size:12px}}.card strong{{font-size:24px}}img{{width:100%;height:auto}}table{{width:100%;border-collapse:collapse;background:#fff}}td,th{{padding:8px 10px;border-bottom:1px solid #e5e5e5;text-align:right}}td:first-child,th:first-child{{text-align:left}}</style></head>
<body><header><h1>EV-AI-CCUS Regional Energy Pressure Intelligence System</h1><p>Static MVP dashboard generated from DuckDB feature tables.</p></header><main><div class="cards">{card_html}</div>
<section><h2>Pressure Ranking</h2><table><thead><tr><th>Region</th><th>EV TWh</th><th>AI TWh</th><th>Combined TWh</th><th>CCUS buffer</th><th>Score</th><th>Class</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Regional Clusters</h2><table><thead><tr><th>Region</th><th>Cluster</th><th>Pressure score</th></tr></thead><tbody>{cluster_rows}</tbody></table></section>
<section><h2>Research Links</h2><p><a href="pressure_ranking_2030.html">Pressure ranking</a> | <a href="ccus_buffer_ratio_2030.html">CCUS buffer</a> | <a href="scenario_comparison_2030.html">Scenario comparison</a> | <a href="feature_importance.html">Feature importance</a> | <a href="cluster_scatter.html">Cluster scatter</a></p></section>{figure_html}</main></body></html>"""
    (RESULTS_DIR / "ev_ai_ccus_dashboard.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    generate_static_dashboard()
