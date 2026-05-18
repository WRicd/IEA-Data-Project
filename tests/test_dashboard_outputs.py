from pathlib import Path


def test_dashboard_outputs_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in [
        "results/ev_ai_ccus_dashboard.html",
        "results/pressure_ranking_2030.html",
        "results/ccus_buffer_ratio_2030.html",
        "results/scenario_comparison_2030.html",
        "results/feature_importance.html",
        "results/cluster_scatter.html",
    ]:
        path = root / rel
        assert path.exists()
        assert path.stat().st_size > 0
