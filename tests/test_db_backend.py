from src.db import get_conn


def test_database_backend_is_duckdb():
    db = get_conn()
    try:
        assert db.backend == "duckdb"
    finally:
        db.close()
