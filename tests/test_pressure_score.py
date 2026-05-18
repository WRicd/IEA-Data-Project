from src.db import get_conn


def test_pressure_score_and_class_valid():
    allowed = {"Low Pressure", "Medium Pressure", "High Pressure", "Critical Pressure"}
    db = get_conn()
    try:
        df = db.read_df("SELECT regional_pressure_score, pressure_class FROM ml_region_year_features")
    finally:
        db.close()
    assert df["regional_pressure_score"].between(0, 100).all()
    assert set(df["pressure_class"]).issubset(allowed)
