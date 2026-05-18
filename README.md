# EV-AI-CCUS Regional Energy Pressure Intelligence System

## Project Overview

This project integrates electric vehicle demand, AI data center electricity demand, and CCUS project capacity into a reproducible regional energy pressure analysis pipeline.

The core research question is whether new electricity demand from EV adoption and AI data centers creates regional pressure, and whether CCUS capacity can act as a mitigation-readiness proxy.

## Data Sources

- `IEA-EV-Data-2023.csv`, `IEA-EV-Data-2024.csv`, `IEA-EV-Data-2025.xlsx`: IEA EV sales, stock, charging, electricity demand, and scenario data.
- `Data_Energy_and_AI.xlsx`: AI data center installed capacity, electricity consumption, PUE, load factor, and scenarios.
- `IEA-CCUS-2026.xlsx`: IEA CCUS project database with status, sector, country/region, and annual capture capacity.

Raw data is copied to `data/raw/`. The original files in the repository root are preserved.

## Project Structure

```text
data/raw/          Raw source files
data/processed/    Feature tables, model outputs, quality reports
data/warehouse/    Local analytical database: energy_ai.duckdb
src/ingest/        EV, AI, and CCUS ingestion modules
src/features/      Region-year-scenario feature engineering
src/models/        Baseline regression, clustering, classification
src/visualization/ Static HTML/SVG dashboard and Streamlit app
tests/             Pytest smoke tests
results/           Static dashboards and charts
```

## Installation

```bash
pip install -r requirements.txt
```

On Windows, use the project virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional research dependencies live in `requirements-optional.txt`.

DuckDB is the default database backend. A sqlite fallback exists only for emergency compatibility and is enabled only when `ALLOW_SQLITE_FALLBACK=1` is explicitly set.

## How To Run Pipeline

```bash
.\.venv\Scripts\python.exe scripts\check_env.py
.\.venv\Scripts\python.exe src\pipeline.py --step all
.\.venv\Scripts\python.exe src\pipeline.py --step env
.\.venv\Scripts\python.exe src\pipeline.py --step schema
.\.venv\Scripts\python.exe src\pipeline.py --step ingest
.\.venv\Scripts\python.exe src\pipeline.py --step features
.\.venv\Scripts\python.exe src\pipeline.py --step scenarios
.\.venv\Scripts\python.exe src\pipeline.py --step models
.\.venv\Scripts\python.exe src\pipeline.py --step explain
.\.venv\Scripts\python.exe src\pipeline.py --step dashboard
.\.venv\Scripts\python.exe src\pipeline.py --step quality
```

The main MVP output is:

```text
data/processed/ml_region_year_features.csv
data/processed/data_quality_report.csv
data/processed/model_regression_metrics.csv
data/processed/region_clusters.csv
data/processed/environment_report.csv
data/processed/database_schema_report.csv
data/processed/scenario_region_year_features.csv
data/processed/scenario_comparison_2030.csv
data/processed/model_feature_importance.csv
results/ev_ai_ccus_dashboard.html
```

## How To Run Dashboard

Static dashboard:

```text
results/ev_ai_ccus_dashboard.html
```

Streamlit dashboard:

```bash
streamlit run src/visualization/dashboard_streamlit.py
```

Windows venv command:

```powershell
.\.venv\Scripts\streamlit.exe run src\visualization\dashboard_streamlit.py
```

## Database Schema

Fact tables:

- `fact_ev`
- `fact_ai_energy`
- `fact_ccus_project`
- `dim_region`

Feature tables:

- `feature_ev_region_year`
- `feature_ai_region_year`
- `feature_ccus_region_year`
- `ml_region_year_features`

## Feature Table Explanation

`ml_region_year_features` is built at:

```text
common_region + year + ev_scenario + ai_scenario
```

Key derived metrics include:

- `combined_electricity_demand_twh`
- `ev_share_of_combined_demand`
- `ai_share_of_combined_demand`
- `ccus_capacity_per_twh_demand`
- `regional_pressure_score`
- `pressure_class`

`scenario_region_year_features` expands the core feature table by CCUS scenario:

- `operating_only`
- `active_projects`
- `all_announced`

The pressure score uses configurable weights from `config/pressure_score_weights.json` and stores component columns:

- `demand_pressure_component`
- `ev_growth_pressure_component`
- `ai_growth_pressure_component`
- `ccus_buffer_component`

## ML Tasks

- Baseline regression predicts `combined_electricity_demand_twh`.
- Clustering groups regional pressure patterns.
- Classification maps pressure scores into Low, Medium, High, and Critical pressure classes.

## Known Limitations

- Current regression and clustering models are lightweight numpy baselines so the project can run in restricted environments.
- When scikit-learn is installed, the environment is ready for richer model classes, but the current committed baseline keeps deterministic numpy logic for reproducibility.
- CCUS capacity is treated as a mitigation-readiness proxy, not as a strict physical offset for electricity demand.
- Region mapping is intentionally conservative and should be expanded before publication-level analysis.
- AI regional workbook has limited scenario coverage outside world-level scenario rows.

## Future Work

- Install full scientific stack and add scikit-learn RandomForest/GradientBoosting models.
- Add electricity generation mix, renewable share, carbon intensity, GDP, population, and electricity prices.
- Add SHAP explainability and richer scenario optimization.
- Expand Streamlit into an interactive exploration app.
