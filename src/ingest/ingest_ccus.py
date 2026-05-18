import logging
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CCUS_PATH, PROCESSED_DIR, ensure_directories
from src.db import get_conn
from src.transform.region_mapping import common_region, region_group


def _norm_col(name) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def choose_project_sheet(xl: pd.ExcelFile) -> str:
    best_sheet = xl.sheet_names[0]
    best_score = -1
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet, nrows=20)
        norm_cols = {_norm_col(c) for c in df.columns}
        score = len(df) * len(df.columns)
        score += 100 if {"project_name", "country_or_economy", "project_status"} & norm_cols else 0
        if score > best_score:
            best_sheet, best_score = sheet, score
    return best_sheet


def first_existing(df: pd.DataFrame, names: list[str]):
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series([None] * len(df))


def load_ccus_projects() -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(CCUS_PATH)
    profile_rows = []
    for sheet in xl.sheet_names:
        sample = pd.read_excel(xl, sheet_name=sheet, nrows=5)
        for col in sample.columns:
            profile_rows.append({"sheet_name": sheet, "column_name": str(col), "normalized_column": _norm_col(col)})
    profile = pd.DataFrame(profile_rows)

    sheet = choose_project_sheet(xl)
    raw = pd.read_excel(xl, sheet_name=sheet)
    raw.columns = [_norm_col(c) for c in raw.columns]

    estimated = pd.to_numeric(first_existing(raw, ["estimated_capacity_by_iea_mt_co2_yr"]), errors="coerce")
    announced = pd.to_numeric(first_existing(raw, ["announced_capacity_mt_co2_yr"]), errors="coerce")
    capacity_mtpa = estimated.fillna(announced)

    country = first_existing(raw, ["country_or_economy", "country"])
    region = first_existing(raw, ["region"])
    status = first_existing(raw, ["project_status", "status"])
    sector = first_existing(raw, ["sector"])
    project_type = first_existing(raw, ["project_type"])
    fate = first_existing(raw, ["fate_of_carbon"])

    out = pd.DataFrame(
        {
            "project_name": first_existing(raw, ["project_name"]),
            "country": country,
            "common_region": country.map(common_region).fillna(region.map(common_region)),
            "region_group": region.fillna(country.map(region_group)),
            "status": status.astype(str).str.strip(),
            "sector": sector,
            "capture_type": project_type,
            "transport_type": None,
            "storage_type": fate.where(fate.astype(str).str.contains("storage|EOR", case=False, na=False)),
            "utilization_type": fate.where(fate.astype(str).str.contains("util", case=False, na=False)),
            "start_year": pd.to_numeric(first_existing(raw, ["operation"]), errors="coerce").astype("Int64"),
            "announced_year": pd.to_numeric(first_existing(raw, ["announcement"]), errors="coerce").astype("Int64"),
            "capacity_tpa": capacity_mtpa * 1_000_000,
            "capacity_mtpa": capacity_mtpa,
            "latitude": None,
            "longitude": None,
            "raw_status": status,
            "raw_sector": sector,
            "source_file": CCUS_PATH.name,
        }
    )
    status_l = out["status"].astype(str).str.lower()
    out["status_standardized"] = "other"
    out.loc[status_l.str.contains("operat", na=False), "status_standardized"] = "operational"
    out.loc[status_l.str.contains("construction", na=False), "status_standardized"] = "under_construction"
    out.loc[status_l.str.contains("plan|develop", na=False), "status_standardized"] = "planned"
    out.loc[status_l.str.contains("cancel|suspend|decommission", na=False), "status_standardized"] = "cancelled_or_suspended"
    out["common_region"] = out["common_region"].fillna(out["region_group"]).fillna("Unknown")
    out["region_group"] = out["region_group"].fillna(out["common_region"])
    return out, profile


def ingest_ccus() -> pd.DataFrame:
    ensure_directories()
    logging.info("input file loaded: CCUS projects")
    df, profile = load_ccus_projects()
    profile.to_csv(PROCESSED_DIR / "ccus_columns_profile.csv", index=False)
    mapping_report = pd.DataFrame(
        [
            ("Project name", "project_name"),
            ("Country or economy", "country"),
            ("Region", "region_group"),
            ("Project status", "status"),
            ("Project status", "status_standardized"),
            ("Sector", "sector"),
            ("Project type", "capture_type"),
            ("Fate of carbon", "storage_type/utilization_type"),
            ("Operation", "start_year"),
            ("Announcement", "announced_year"),
            ("Estimated capacity by IEA (Mt CO2/yr)", "capacity_mtpa"),
            ("Announced capacity (Mt CO2/yr)", "capacity_mtpa fallback"),
        ],
        columns=["source_column", "standard_field"],
    )
    mapping_report.to_csv(PROCESSED_DIR / "ccus_column_mapping_report.csv", index=False)
    db = get_conn()
    try:
        db.write_df("fact_ccus_project", df)
        logging.info("table created: fact_ccus_project row_count=%s", len(df))
    finally:
        db.close()
    df.to_csv(PROCESSED_DIR / "fact_ccus_project.csv", index=False)
    return df


if __name__ == "__main__":
    ingest_ccus()
