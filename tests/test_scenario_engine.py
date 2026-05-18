from src.db import get_conn


def test_scenario_region_year_features_non_empty():
    db = get_conn()
    try:
        assert db.get_table_row_count("scenario_region_year_features") > 0
    finally:
        db.close()
