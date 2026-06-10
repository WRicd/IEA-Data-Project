# EV-AI-CCUS Regional Energy Pressure Intelligence System

## Overview

This project combines electric vehicle demand, AI data center electricity demand, and CCUS project capacity into a reproducible regional energy pressure analysis workflow.

The main research question is:

> Do EV adoption and AI data center expansion create regional electricity pressure, and can CCUS capacity act as a mitigation-readiness proxy?

## Current Deliverables

The current final presentation artifact is:

```text
EV_AI_CCUS_Interactive_Dashboard.html
```

It is a standalone interactive HTML dashboard at the repository root. It supports year, region, EV scenario, AI scenario, and CCUS scenario filters, plus hover tooltips and synchronized tables.

Final PNG exports are stored in `results/`:

```text
results/pressure_ranking_2030.png
results/combined_demand_by_region.png
results/ev_ai_mix_2030.png
results/ccus_buffer_ratio_2030.png
results/scenario_pressure_comparison_2030.png
results/feature_importance.png
results/cluster_scatter.png
```

Older SVG and prototype HTML outputs have been removed from `results/`.

## Data Sources

Canonical source files live in `data/raw/`. Any same-named CSV/XLSX files in the repository root are duplicate convenience copies and are not required by the current pipeline.

| File | Description |
| --- | --- |
| `IEA-EV-Data-2023.csv` | IEA EV data, 2023 release |
| `IEA-EV-Data-2024.csv` | IEA EV data, 2024 release |
| `IEA-EV-Data-2025.xlsx` | IEA EV data, 2025 release, `GEVO_EV_2025` sheet |
| `Data_Energy_and_AI.xlsx` | AI data center capacity, electricity consumption, PUE, load factor, and scenarios |
| `IEA-CCUS-2026.xlsx` | IEA CCUS project database |

## Project Structure

```text
config/
  pressure_score_weights.json

data/
  raw/          Raw source files copied from the repository root
  interim/      Reserved for intermediate files
  processed/    Fact tables, feature tables, quality reports, model outputs
  warehouse/    DuckDB analytical database

logs/           Pipeline logs
results/        Final PNG chart exports
scripts/        Environment, pipeline, dashboard, and test helpers
src/            Main pipeline source code
tests/          Pytest smoke and integration tests

EV_AI_CCUS_Interactive_Dashboard.html
starter_ev_ai_project.py
requirements.txt
requirements-optional.txt
```

`starter_ev_ai_project.py` is kept as a legacy exploratory reference. The modular pipeline lives under `src/`.

## Installation

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional research dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
```

DuckDB is the primary database backend. SQLite fallback is only allowed when `ALLOW_SQLITE_FALLBACK=1` is explicitly set.

## Pipeline Commands

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
.\.venv\Scripts\python.exe src\pipeline.py --step all
```

Individual steps:

```powershell
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

Convenience scripts:

```powershell
.\scripts\run_pipeline.ps1
.\scripts\run_tests.ps1
.\scripts\run_dashboard.ps1
```

## Main Data Outputs

Key files in `data/processed/`:

| File | Purpose |
| --- | --- |
| `fact_ev.csv` | Ingested EV fact table |
| `fact_ai_energy.csv` | Ingested AI energy fact table |
| `fact_ccus_project.csv` | Standardized CCUS project fact table |
| `feature_ev_region_year.csv` | EV region-year features |
| `feature_ai_region_year.csv` | AI region-year features |
| `feature_ccus_region_year.csv` | CCUS region-year cumulative capacity |
| `ml_region_year_features.csv` | Core ML-ready feature table |
| `scenario_region_year_features.csv` | Scenario-expanded region-year features |
| `scenario_comparison_2030.csv` | 2030 scenario comparison table |
| `model_regression_metrics.csv` | Regression model metrics |
| `model_feature_importance.csv` | Model feature importance |
| `region_clusters.csv` | Regional clustering output |
| `data_quality_report.csv` | Data quality report |
| `environment_report.csv` | Environment validation report |
| `database_schema_report.csv` | Database schema report |

## Database

The main warehouse is:

```text
data/warehouse/energy_ai.duckdb
```

Main tables:

```text
fact_ev
fact_ai_energy
fact_ccus_project
dim_region
feature_ev_region_year
feature_ai_region_year
feature_ccus_region_year
ml_region_year_features
scenario_region_year_features
scenario_comparison_2030
pipeline_metadata
```

## Pressure Score

The regional pressure score is normalized to 0-100. Higher values indicate higher pressure.

The current formula combines:

```text
demand_pressure_component
ev_growth_pressure_component
ai_growth_pressure_component
ccus_buffer_component
```

Weights live in:

```text
config/pressure_score_weights.json
```

Default weights:

```text
demand: 0.35
ev_growth: 0.20
ai_growth: 0.20
ccus_buffer: 0.25
```

Pressure classes:

| Score | Class |
| --- | --- |
| `< 25` | Low Pressure |
| `25-49` | Medium Pressure |
| `50-74` | High Pressure |
| `>= 75` | Critical Pressure |

## Models

When scikit-learn is available, the project uses:

| Task | Models |
| --- | --- |
| Regression | Ridge, RandomForestRegressor, GradientBoostingRegressor |
| Clustering | KMeans with PCA coordinates |
| Classification | LogisticRegression, RandomForestClassifier, GradientBoostingClassifier |

Numpy fallbacks are retained for restricted environments.

## Tests

Run tests after the pipeline has produced the DuckDB database:

```powershell
.\.venv\Scripts\pytest.exe
```

The tests validate the database backend, non-empty fact and feature tables, CCUS standardization, pressure score ranges, scenario engine output, and dashboard files.

## Notes On Cleanup

The old root-level `processed/` folder and Anaconda file-browser cache are obsolete and can be removed. The canonical processed outputs now live under `data/processed/`.

`.pytest_cache/` is ignored. If Windows leaves an ACL-locked empty `.pytest_cache` directory behind, it is safe to leave it in place because it is not part of the project.

## Known Limitations

- CCUS capacity is a mitigation-readiness proxy, not a physical offset for electricity demand.
- Region mapping is intentionally conservative and should be expanded before publication-level analysis.
- AI regional scenario coverage is limited outside the workbook's world-level scenario rows.
- The final interactive HTML is static and self-contained; it does not refresh automatically when CSV files change.

## Future Work

- Add power mix, renewable share, carbon intensity, GDP, population, and electricity price data.
- Add SHAP or permutation-based explainability.
- Add richer Streamlit drill-down pages.
- Add CI checks for environment, pipeline, tests, and dashboard generation.
