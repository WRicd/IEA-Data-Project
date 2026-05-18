from datetime import datetime
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import AI_ENERGY_PATH, CCUS_PATH, EV_2023_PATH, EV_2024_PATH, EV_2025_PATH, PROCESSED_DIR, ensure_directories
from src.db import get_conn


def _row(name, status, details="", row_count=0, severity="INFO"):
    return {
        "check_name": name,
        "severity": severity,
        "status": status,
        "details": details,
        "row_count": row_count,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def run_quality_checks() -> pd.DataFrame:
    ensure_directories()
    rows = []
    for path in [EV_2023_PATH, EV_2024_PATH, EV_2025_PATH, AI_ENERGY_PATH, CCUS_PATH]:
        rows.append(_row(f"raw_file_exists:{path.name}", "PASS" if path.exists() else "FAIL", str(path), severity="ERROR" if not path.exists() else "INFO"))
    for workbook, sheets in [(AI_ENERGY_PATH, ["Regional Data", "World Data"]), (CCUS_PATH, None)]:
        try:
            xl = pd.ExcelFile(workbook)
            ok = all(s in xl.sheet_names for s in sheets) if sheets else bool(xl.sheet_names)
            rows.append(_row(f"workbook_readable:{workbook.name}", "PASS" if ok else "FAIL", ",".join(xl.sheet_names), severity="ERROR" if not ok else "INFO"))
        except Exception as exc:
            rows.append(_row(f"workbook_readable:{workbook.name}", "FAIL", str(exc), severity="ERROR"))
    db = get_conn()
    try:
        rows.append(_row("database_backend", "PASS" if db.backend == "duckdb" else "FAIL", f"backend={db.backend}", severity="CRITICAL" if db.backend != "duckdb" else "INFO"))
        for table in ["fact_ev", "fact_ai_energy", "fact_ccus_project", "feature_ev_region_year", "feature_ai_region_year", "feature_ccus_region_year", "ml_region_year_features"]:
            count = db.get_table_row_count(table)
            rows.append(_row(f"table_non_empty:{table}", "PASS" if count > 0 else "FAIL", table, count, severity="ERROR" if count == 0 else "INFO"))
        if db.table_exists("fact_ai_energy"):
            metrics = set(db.read_df("SELECT DISTINCT metric FROM fact_ai_energy")["metric"])
            required = {"Total electricity consumption (TWh)", "Power usage effectiveness", "Load factor (%)"}
            ok = required.issubset(metrics)
            rows.append(_row("ai_required_metrics", "PASS" if ok else "FAIL", ",".join(sorted(required - metrics)), severity="ERROR" if not ok else "INFO"))
        if db.table_exists("fact_ccus_project"):
            ccus = db.read_df("SELECT COUNT(*) AS n, SUM(capacity_mtpa) AS mtpa FROM fact_ccus_project")
            ok = int(ccus.iloc[0]["n"]) > 0 and float(ccus.iloc[0]["mtpa"] or 0) > 0
            rows.append(_row("ccus_capacity_numeric", "PASS" if ok else "FAIL", f"mtpa={ccus.iloc[0]['mtpa']}", int(ccus.iloc[0]["n"]), severity="ERROR" if not ok else "INFO"))
        if db.table_exists("ml_region_year_features"):
            stats = db.read_df("SELECT MIN(regional_pressure_score) AS min_score, MAX(regional_pressure_score) AS max_score, COUNT(*) AS n FROM ml_region_year_features")
            min_score, max_score, n = stats.iloc[0]["min_score"], stats.iloc[0]["max_score"], int(stats.iloc[0]["n"])
            ok = 0 <= min_score <= 100 and 0 <= max_score <= 100 and n > 0
            rows.append(_row("pressure_score_range", "PASS" if ok else "FAIL", f"min={min_score}, max={max_score}", n, severity="ERROR" if not ok else "INFO"))
        if db.table_exists("scenario_region_year_features"):
            count = db.get_table_row_count("scenario_region_year_features")
            rows.append(_row("scenario_region_year_features_non_empty", "PASS" if count > 0 else "FAIL", "", count, severity="ERROR" if count == 0 else "INFO"))
    finally:
        db.close()
    report = pd.DataFrame(rows)
    report.to_csv(PROCESSED_DIR / "data_quality_report.csv", index=False)
    return report


if __name__ == "__main__":
    run_quality_checks()
