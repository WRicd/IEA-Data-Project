import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import AI_ENERGY_PATH, CCUS_PATH, EV_2023_PATH, EV_2024_PATH, EV_2025_PATH, PROCESSED_DIR, ensure_directories
from src.db import get_conn


REQUIRED_LIBS = ["pandas", "numpy", "openpyxl", "duckdb", "pyarrow", "sklearn", "matplotlib", "plotly", "streamlit", "pytest"]


def row(name, status, details):
    return {
        "check_name": name,
        "status": status,
        "details": details,
        "python_executable": sys.executable,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def main():
    ensure_directories()
    rows = [row("python_executable", "PASS" if ".venv" in sys.executable else "WARN", sys.executable)]
    for lib in REQUIRED_LIBS:
        try:
            mod = __import__(lib)
            rows.append(row(f"library:{lib}", "PASS", getattr(mod, "__version__", "")))
        except Exception as exc:
            rows.append(row(f"library:{lib}", "FAIL", str(exc)))
    try:
        db = get_conn()
        try:
            rows.append(row("database_backend", "PASS" if db.backend == "duckdb" else "FAIL", db.backend))
        finally:
            db.close()
    except Exception as exc:
        rows.append(row("database_backend", "FAIL", str(exc)))
    for path in [EV_2023_PATH, EV_2024_PATH, EV_2025_PATH, AI_ENERGY_PATH, CCUS_PATH]:
        rows.append(row(f"raw_file:{path.name}", "PASS" if path.exists() else "FAIL", str(path)))
    report = pd.DataFrame(rows)
    report.to_csv(PROCESSED_DIR / "environment_report.csv", index=False)
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
