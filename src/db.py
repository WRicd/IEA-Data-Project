import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import DB_PATH, ensure_directories


try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover - depends on local environment
    duckdb = None


class Database:
    def __init__(self, path: Path = DB_PATH):
        ensure_directories()
        self.path = path
        allow_sqlite = os.environ.get("ALLOW_SQLITE_FALLBACK") == "1"
        if duckdb is not None:
            self.backend = "duckdb"
            try:
                self.conn = duckdb.connect(str(path))
            except Exception:
                if path.exists():
                    backup = path.with_suffix(f".sqlite_fallback_{int(time.time())}.bak")
                    path.replace(backup)
                self.conn = duckdb.connect(str(path))
        elif allow_sqlite:
            self.backend = "sqlite"
            self.conn = sqlite3.connect(str(path))
        else:
            raise RuntimeError(
                "DuckDB is not installed. Install requirements.txt or set ALLOW_SQLITE_FALLBACK=1."
            )

    def close(self) -> None:
        self.conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] | None = None):
        if params is None:
            return self.conn.execute(sql)
        return self.conn.execute(sql, params)

    def write_df(self, table_name: str, df: pd.DataFrame) -> None:
        if self.backend == "duckdb":
            self.conn.register("_df_to_write", df)
            self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _df_to_write")
            self.conn.unregister("_df_to_write")
        else:
            df.to_sql(table_name, self.conn, if_exists="replace", index=False)

    def read_df(self, sql: str) -> pd.DataFrame:
        if self.backend == "duckdb":
            return self.conn.execute(sql).fetchdf()
        return pd.read_sql_query(sql, self.conn)

    def table_exists(self, table_name: str) -> bool:
        if self.backend == "duckdb":
            df = self.conn.execute(
                "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchdf()
        else:
            df = pd.read_sql_query(
                "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name = ?",
                self.conn,
                params=(table_name,),
            )
        return int(df.iloc[0]["n"]) > 0

    def get_table_row_count(self, table_name: str) -> int:
        if not self.table_exists(table_name):
            return 0
        return int(self.read_df(f"SELECT COUNT(*) AS n FROM {table_name}").iloc[0]["n"])


def get_conn(path: Path = DB_PATH) -> Database:
    return Database(path)


def table_exists(table_name: str) -> bool:
    db = get_conn()
    try:
        return db.table_exists(table_name)
    finally:
        db.close()


def get_table_row_count(table_name: str) -> int:
    db = get_conn()
    try:
        return db.get_table_row_count(table_name)
    finally:
        db.close()


def write_pipeline_metadata(pipeline_run_id: str, step: str) -> None:
    import platform
    from datetime import datetime

    db = get_conn()
    try:
        row = pd.DataFrame(
            [
                {
                    "pipeline_run_id": pipeline_run_id,
                    "step": step,
                    "backend": db.backend,
                    "python_version": platform.python_version(),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            ]
        )
        if db.table_exists("pipeline_metadata"):
            existing = db.read_df("SELECT * FROM pipeline_metadata")
            row = pd.concat([existing, row], ignore_index=True)
        db.write_df("pipeline_metadata", row)
    finally:
        db.close()
