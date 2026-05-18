from src.db import get_conn


def test_world_cumulative_ccus_capacity_positive():
    db = get_conn()
    try:
        df = db.read_df(
            "SELECT cumulative_ccus_capacity_mtpa FROM feature_ccus_region_year WHERE common_region='World' AND year=2030"
        )
    finally:
        db.close()
    assert not df.empty
    assert float(df.iloc[0]["cumulative_ccus_capacity_mtpa"]) > 0
