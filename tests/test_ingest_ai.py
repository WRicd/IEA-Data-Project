from src.db import get_conn


def test_fact_ai_energy_non_empty():
    db = get_conn()
    try:
        assert db.get_table_row_count("fact_ai_energy") > 0
    finally:
        db.close()
