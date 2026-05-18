import argparse
import logging
import sys
import uuid

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import LOG_DIR, ensure_directories
from src.features.build_ml_features import build_features
from src.ingest.ingest_ai import ingest_ai
from src.ingest.ingest_ccus import ingest_ccus
from src.ingest.ingest_ev import ingest_ev
from src.models.train_baseline_regression import train_baseline_regression
from src.models.train_classification import train_classification
from src.models.train_clustering import train_clustering
from src.quality_checks import run_quality_checks
from src.db import get_conn, write_pipeline_metadata
from src.export_schema import export_schema
from src.features.scenario_engine import build_scenarios
from src.transform.region_mapping import REGION_ROWS
from src.visualization.static_charts import generate_static_dashboard


def setup_logging() -> None:
    ensure_directories()
    logging.basicConfig(
        filename=LOG_DIR / "pipeline.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def run_ingest() -> None:
    ingest_ev()
    ingest_ai()
    ingest_ccus()
    import pandas as pd

    dim_region = pd.DataFrame(
        REGION_ROWS, columns=["raw_region", "common_region", "iso3", "region_group", "is_country"]
    )
    db = get_conn()
    try:
        db.write_df("dim_region", dim_region)
        dim_region.to_csv(ROOT / "data" / "processed" / "dim_region.csv", index=False)
        logging.info("table created: dim_region row_count=%s", len(dim_region))
    finally:
        db.close()


def run_models() -> None:
    train_baseline_regression()
    train_clustering()
    train_classification()


def run_explain() -> None:
    # Explainability files are emitted by the regression trainer.
    train_baseline_regression()


def run_step(step: str) -> None:
    pipeline_run_id = str(uuid.uuid4())
    logging.info("pipeline start: step=%s run_id=%s", step, pipeline_run_id)
    write_pipeline_metadata(pipeline_run_id, step)
    if step in {"all", "env"}:
        from scripts.check_env import main as check_env_main

        check_env_main()
    if step in {"all", "ingest"}:
        run_ingest()
    if step in {"all", "features"}:
        build_features()
    if step in {"all", "scenarios"}:
        build_scenarios()
    if step in {"all", "models"}:
        run_models()
    if step in {"all", "explain"}:
        run_explain()
    if step in {"all", "dashboard"}:
        generate_static_dashboard()
    if step in {"all", "schema"}:
        export_schema()
    if step in {"all", "quality"}:
        run_quality_checks()
    write_pipeline_metadata(pipeline_run_id, f"{step}:end")
    logging.info("pipeline end: step=%s run_id=%s", step, pipeline_run_id)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="EV-AI-CCUS energy pressure pipeline")
    parser.add_argument("--step", choices=["all", "env", "schema", "ingest", "features", "scenarios", "models", "explain", "dashboard", "quality"], default="all")
    args = parser.parse_args(argv)
    setup_logging()
    run_step(args.step)


if __name__ == "__main__":
    main()
