from src.db import get_conn


def test_fact_ccus_project_non_empty():
    db = get_conn()
    try:
        assert db.get_table_row_count("fact_ccus_project") > 0
    finally:
        db.close()
