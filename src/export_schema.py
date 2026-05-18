import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, ensure_directories
from src.db import get_conn


def export_schema() -> pd.DataFrame:
    ensure_directories()
    db = get_conn()
    rows = []
    try:
        if db.backend == "duckdb":
            tables = db.read_df("SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name")
            for table in tables["table_name"]:
                cols = db.read_df(f"PRAGMA table_info('{table}')")
                for col in cols.itertuples():
                    rows.append(
                        {
                            "table_name": table,
                            "column_name": col.name,
                            "data_type": col.type,
                            "nullable": "",
                            "row_count": db.get_table_row_count(table),
                        }
                    )
        else:
            tables = db.read_df("SELECT name AS table_name FROM sqlite_master WHERE type='table' ORDER BY name")
            for table in tables["table_name"]:
                cols = db.read_df(f"PRAGMA table_info({table})")
                for col in cols.itertuples():
                    rows.append(
                        {
                            "table_name": table,
                            "column_name": col.name,
                            "data_type": col.type,
                            "nullable": not bool(col.notnull),
                            "row_count": db.get_table_row_count(table),
                        }
                    )
    finally:
        db.close()
    report = pd.DataFrame(rows)
    report.to_csv(PROCESSED_DIR / "database_schema_report.csv", index=False)
    return report


if __name__ == "__main__":
    export_schema()
