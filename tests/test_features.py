from src.db import get_conn


def test_ml_features_non_empty_and_scores_valid():
    db = get_conn()
    try:
        assert db.get_table_row_count("ml_region_year_features") > 0
        df = db.read_df(
            "SELECT combined_electricity_demand_twh, regional_pressure_score FROM ml_region_year_features"
        )
    finally:
        db.close()
    assert df["combined_electricity_demand_twh"].notna().any()
    assert df["regional_pressure_score"].between(0, 100).all()
