from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
RESULTS_DIR = ROOT / "results"
LOG_DIR = ROOT / "logs"

DB_PATH = WAREHOUSE_DIR / "energy_ai.duckdb"

EV_2023_PATH = RAW_DIR / "IEA-EV-Data-2023.csv"
EV_2024_PATH = RAW_DIR / "IEA-EV-Data-2024.csv"
EV_2025_PATH = RAW_DIR / "IEA-EV-Data-2025.xlsx"
AI_ENERGY_PATH = RAW_DIR / "Data_Energy_and_AI.xlsx"
CCUS_PATH = RAW_DIR / "IEA-CCUS-2026.xlsx"


def ensure_directories() -> None:
    for path in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, WAREHOUSE_DIR, RESULTS_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
