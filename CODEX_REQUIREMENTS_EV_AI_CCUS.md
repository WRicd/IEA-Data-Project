---

# CODEX_REQUIREMENTS_PHASE2_EV_AI_CCUS.md

## 1. 阶段目标

当前项目已经完成 Phase 1 MVP：

```text
EV / AI / CCUS ingest
fact tables
feature tables
ml_region_year_features
pressure score
baseline regression
clustering
classification
static dashboard
sqlite fallback
quality report
pipeline.py --step all
```

下一阶段目标是将项目从 **可跑通的 MVP** 升级为 **可验证、可解释、可交互、可研究复现的能源 AI 分析系统**。

本阶段重点不是马上做深度学习，而是：

```text
1. 固定 DuckDB 作为主数据库后端
2. 强化数据质量与 schema validation
3. 改进 CCUS 区域聚合逻辑
4. 改进 pressure score 的计算口径
5. 增加情景矩阵 scenario engine
6. 增加模型解释性与特征重要性
7. 增加 Streamlit dashboard 的研究交互能力
8. 增加 pytest 覆盖率与命令脚本
```

DuckDB 应作为默认分析数据库，因为它可以直接查询 pandas DataFrame、Arrow 和 Polars 对象，适合本项目这种 Python + SQL + ML 的本地分析型工作流。([DuckDB][1])
Streamlit 继续作为交互式 dashboard 框架，官方文档支持通过 pip/conda 等方式安装和运行应用。([Streamlit 文档][2])
pytest 用于测试体系，官方文档说明其适合从小型测试扩展到复杂功能测试，并支持标准测试发现规则。([pytest 文档][3])

---

# 2. 当前项目状态

Codex 已完成第一阶段重构，并已生成：

```text
data/raw/
data/processed/
data/warehouse/
src/
src/ingest/
src/features/
src/models/
src/visualization/
tests/
logs/
```

已实现入口：

```bash
python src/pipeline.py --step all
python src/pipeline.py --step ingest
python src/pipeline.py --step features
python src/pipeline.py --step models
python src/pipeline.py --step dashboard
```

已生成关键输出：

```text
data/warehouse/energy_ai.duckdb
data/processed/ml_region_year_features.csv
data/processed/data_quality_report.csv
data/processed/model_regression_metrics.csv
data/processed/region_clusters.csv
results/ev_ai_ccus_dashboard.html
```

已知情况：

```text
1. Codex 环境缺少 duckdb / sklearn / matplotlib / plotly / streamlit / pytest
2. 当前代码实现了 sqlite fallback
3. 当前 pipeline 已经能在 fallback 模式下跑通
4. CCUS World 聚合已修正为全项目累计能力
5. 区域聚合已开始考虑 CCUS region group
6. 当前 ml_region_year_features 约 43 行
```

---

# 3. 环境要求

## 3.1 必须使用项目本地虚拟环境

后续所有开发命令必须优先使用：

```powershell
.\.venv\Scripts\python.exe
```

不要使用 Codex 临时 runtime，除非用户明确说明。

Codex 执行 Python 命令时应使用：

```powershell
.\.venv\Scripts\python.exe src\pipeline.py --step all
```

而不是：

```powershell
python src\pipeline.py --step all
```

---

## 3.2 requirements.txt 必须更新

`requirements.txt` 至少包含：

```txt
pandas>=2.0
numpy>=1.24
openpyxl>=3.1
duckdb>=1.0
pyarrow>=15.0
scikit-learn>=1.4
matplotlib>=3.8
plotly>=5.20
streamlit>=1.35
pytest>=8.0
```

可选依赖单独放入：

```text
requirements-optional.txt
```

内容：

```txt
xgboost
lightgbm
shap
umap-learn
hdbscan
```

---

## 3.3 新增环境检查脚本

新增：

```text
scripts/check_env.py
```

功能：

1. 检查当前 Python 可执行路径
2. 检查关键库是否安装
3. 检查 DuckDB 是否可用
4. 检查是否错误使用 sqlite fallback
5. 检查 raw 数据文件是否存在
6. 输出环境报告

运行方式：

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

输出：

```text
data/processed/environment_report.csv
```

字段：

```text
check_name
status
details
python_executable
created_at
```

验收标准：

```text
duckdb_available = PASS
database_backend = duckdb
```

---

# 4. 数据库后端要求

## 4.1 DuckDB 作为主后端

`src/db.py` 需要调整为：

```text
默认使用 DuckDB
仅当用户显式设置 ALLOW_SQLITE_FALLBACK=1 时才允许 fallback
```

当前 sqlite fallback 可以保留，但必须避免静默 fallback。

建议逻辑：

```text
if duckdb installed:
    backend = duckdb
elif ALLOW_SQLITE_FALLBACK == "1":
    backend = sqlite
else:
    raise RuntimeError("DuckDB is not installed. Install requirements.txt or set ALLOW_SQLITE_FALLBACK=1.")
```

---

## 4.2 数据库元信息表

新增表：

```sql
CREATE TABLE IF NOT EXISTS pipeline_metadata (
    key TEXT,
    value TEXT,
    created_at TEXT
);
```

需要写入：

```text
database_backend
pipeline_run_id
pipeline_started_at
pipeline_completed_at
git_commit_optional
python_version
```

---

## 4.3 数据库 schema 导出

新增脚本：

```text
src/export_schema.py
```

运行：

```powershell
.\.venv\Scripts\python.exe src\export_schema.py
```

输出：

```text
data/processed/database_schema_report.csv
```

字段：

```text
table_name
column_name
data_type
nullable
row_count
```

---

# 5. 数据质量 Phase 2 要求

当前已有 `data_quality_report.csv`，下一阶段需要扩展。

## 5.1 新增质量检查项

`src/quality_checks.py` 增加以下检查：

### EV 检查

```text
fact_ev row count > 0
version includes 2025
year min/max valid
value non-null ratio
required parameters exist:
  EV sales
  EV stock
  Electricity demand
```

### AI 检查

```text
fact_ai_energy row count > 0
metric includes:
  Total electricity consumption (TWh)
  Total installed capacity (GW)
  Power usage effectiveness
  Load factor (%)
scenario includes:
  Historical / Base / Base Case / Lift-Off / High Efficiency / Headwinds
```

### CCUS 检查

```text
fact_ccus_project row count > 0
capacity_tpa numeric ratio
capacity_mtpa numeric ratio
country/common_region non-null ratio
status distribution
start_year coverage
World cumulative capacity > 0
```

### Feature 检查

```text
ml_region_year_features row count > 0
combined_electricity_demand_twh not all null
regional_pressure_score between 0 and 100
pressure_class not null
2030 rows exist
World 2030 row exists
```

---

## 5.2 质量等级

每个检查新增 severity：

```text
INFO
WARN
ERROR
CRITICAL
```

输出字段改为：

```text
check_name
status
severity
details
row_count
created_at
```

验收标准：

```text
CRITICAL = 0
ERROR <= 1
```

---

# 6. CCUS 数据处理 Phase 2

Codex 已经读取 `IEA-CCUS-2026.xlsx` 并实现基本 ingest。下一步要加强 CCUS 标准化。

## 6.1 CCUS 列名映射报告

保留并扩展：

```text
data/processed/ccus_columns_profile.csv
```

新增：

```text
data/processed/ccus_column_mapping_report.csv
```

字段：

```text
raw_column
standard_column
mapping_confidence
mapping_rule
sample_values
```

---

## 6.2 CCUS status 标准化

新增标准 status：

```text
operating
under_construction
planned
announced
cancelled
suspended
unknown
```

新增字段：

```text
standard_status
is_active_project
is_operating_project
is_future_project
```

规则：

```text
operating -> active + operating
under_construction / planned / announced -> active + future
cancelled / suspended -> inactive
unknown -> unknown
```

---

## 6.3 CCUS 年份逻辑

新增标准年份字段：

```text
announced_year
start_year
operation_year
expected_operation_year
```

优先级：

```text
operation_year > start_year > expected_operation_year > announced_year
```

用于年度聚合的字段命名为：

```text
effective_year
```

---

## 6.4 CCUS capacity 逻辑

标准字段：

```text
capacity_tpa
capacity_mtpa
```

转换规则：

```text
capacity_mtpa = capacity_tpa / 1_000_000
capacity_tpa = capacity_mtpa * 1_000_000
```

如果原始字段单位不明确：

```text
1. 通过列名判断 Mt / Mtpa / tpa / ktpa
2. 通过数值范围辅助判断
3. 记录 warning
```

---

## 6.5 CCUS 区域聚合

`feature_ccus_region_year` 需要同时支持：

```text
country level
region group level
World level
```

输出字段：

```text
common_region
year
ccus_project_count
active_ccus_project_count
operating_project_count
future_project_count
annual_ccus_capacity_tpa
annual_active_ccus_capacity_tpa
annual_operating_ccus_capacity_tpa
cumulative_ccus_capacity_tpa
cumulative_active_ccus_capacity_tpa
cumulative_operating_ccus_capacity_tpa
```

要求：

```text
World = all active projects summed
Region group = all countries in group summed
Country = individual country summed
```

---

# 7. Scenario Engine 需求

新增模块：

```text
src/features/scenario_engine.py
```

目标：构建 EV / AI / CCUS 情景矩阵。

## 7.1 情景维度

EV scenario：

```text
Historical
Projection-STEPS
```

AI scenario：

```text
Historical
Base
Base Case
Lift-Off
High Efficiency
Headwinds
```

CCUS scenario：

```text
operating_only
active_projects
all_announced
```

---

## 7.2 输出表

新增：

```text
scenario_region_year_features
```

粒度：

```text
common_region + year + ev_scenario + ai_scenario + ccus_scenario
```

字段包含：

```text
common_region
year
ev_scenario
ai_scenario
ccus_scenario
ev_electricity_twh
ai_electricity_twh
combined_electricity_demand_twh
ccus_capacity_tpa
ccus_capacity_mtpa
ccus_buffer_ratio
regional_pressure_score
pressure_class
```

输出 CSV：

```text
data/processed/scenario_region_year_features.csv
```

---

## 7.3 Scenario 比较输出

新增：

```text
data/processed/scenario_comparison_2030.csv
```

对比指标：

```text
common_region
scenario_name
combined_electricity_demand_twh
ccus_buffer_ratio
regional_pressure_score
pressure_class
rank
```

---

# 8. Pressure Score Phase 2

当前 `regional_pressure_score` 已有 MVP 版本。下一阶段要使其更透明。

## 8.1 拆分分数构成

新增字段：

```text
demand_pressure_component
growth_pressure_component
ccus_buffer_component
ai_share_component
ev_share_component
regional_pressure_score
```

---

## 8.2 计算方式

建议第一版：

```text
demand_pressure_component =
percentile_rank(combined_electricity_demand_twh)

growth_pressure_component =
average(
  percentile_rank(ev_growth_rate),
  percentile_rank(ai_growth_rate)
)

ccus_buffer_component =
100 - percentile_rank(ccus_buffer_ratio)

regional_pressure_score =
0.40 * demand_pressure_component
+ 0.25 * growth_pressure_component
+ 0.25 * ccus_buffer_component
+ 0.10 * max(ai_share_component, ev_share_component)
```

最终 score 限制：

```text
0 <= score <= 100
```

---

## 8.3 可配置权重

新增配置文件：

```text
config/pressure_score_weights.yml
```

内容：

```yaml
demand_pressure_component: 0.40
growth_pressure_component: 0.25
ccus_buffer_component: 0.25
sector_share_component: 0.10
```

如果不安装 `pyyaml`，可先用 JSON：

```text
config/pressure_score_weights.json
```

---

# 9. 模型 Phase 2

当前模型层使用纯 pandas/numpy baseline。下一阶段如果 scikit-learn 已安装，则启用 sklearn 模型；如果没有，保留 fallback。

## 9.1 Regression

更新：

```text
src/models/train_baseline_regression.py
```

要求：

如果 sklearn 可用：

```text
Ridge
RandomForestRegressor
GradientBoostingRegressor
```

如果 sklearn 不可用：

```text
numpy baseline
```

输出：

```text
data/processed/model_regression_metrics.csv
data/processed/model_regression_predictions.csv
data/processed/model_feature_importance.csv
```

指标：

```text
MAE
RMSE
R2
MAPE
model_name
train_rows
test_rows
```

---

## 9.2 Clustering

更新：

```text
src/models/train_clustering.py
```

如果 sklearn 可用：

```text
StandardScaler
KMeans
PCA
GaussianMixture optional
```

如果 sklearn 不可用：

```text
numpy fallback clustering
```

输出：

```text
data/processed/region_clusters.csv
data/processed/cluster_centers.csv
results/cluster_scatter.html
```

---

## 9.3 Classification

更新：

```text
src/models/train_classification.py
```

如果 sklearn 可用：

```text
LogisticRegression
RandomForestClassifier
GradientBoostingClassifier
```

如果 sklearn 不可用：

```text
rule-based classification only
```

输出：

```text
data/processed/pressure_classification_metrics.csv
data/processed/pressure_classification_predictions.csv
```

---

## 9.4 Model Explainability

新增：

```text
src/models/explain_features.py
```

第一阶段不强制使用 SHAP。必须至少输出：

```text
permutation_importance 或 model feature_importance_
```

输出：

```text
data/processed/model_explainability.csv
results/feature_importance.html
```

---

# 10. 可视化 Phase 2

## 10.1 Static HTML Dashboard

更新：

```text
results/ev_ai_ccus_dashboard.html
```

新增内容：

```text
1. Database backend card
2. Pipeline run timestamp
3. Data quality summary
4. 2030 pressure ranking
5. Scenario comparison table
6. CCUS active / operating capacity comparison
7. Feature importance chart
8. Cluster scatter plot link
```

---

## 10.2 Plotly 图表

新增或更新：

```text
results/pressure_ranking_2030.html
results/ccus_buffer_ratio_2030.html
results/scenario_comparison_2030.html
results/feature_importance.html
results/cluster_scatter.html
```

要求：

```text
所有 HTML 可直接双击打开
不依赖外部服务器
```

---

## 10.3 Streamlit Dashboard

更新：

```text
src/visualization/dashboard_streamlit.py
```

页面结构：

```text
Overview
Data Quality
Scenario Explorer
Regional Pressure Ranking
CCUS Explorer
Model Results
Raw Tables
```

Sidebar filters：

```text
year
common_region
ev_scenario
ai_scenario
ccus_scenario
pressure_class
```

功能：

```text
1. 展示 key metrics
2. 展示 pressure ranking
3. 展示 scenario comparison
4. 展示 feature importance
5. 展示 cluster scatter
6. 下载当前筛选数据 CSV
7. 显示当前数据库 backend
```

运行方式：

```powershell
.\.venv\Scripts\streamlit.exe run src\visualization\dashboard_streamlit.py
```

---

# 11. Pipeline Phase 2

## 11.1 新增 pipeline steps

`src/pipeline.py` 支持：

```bash
python src/pipeline.py --step env
python src/pipeline.py --step schema
python src/pipeline.py --step ingest
python src/pipeline.py --step features
python src/pipeline.py --step scenarios
python src/pipeline.py --step models
python src/pipeline.py --step explain
python src/pipeline.py --step dashboard
python src/pipeline.py --step quality
python src/pipeline.py --step all
```

---

## 11.2 all 执行顺序

```text
1. env
2. ingest
3. features
4. scenarios
5. models
6. explain
7. dashboard
8. schema
9. quality
```

---

## 11.3 pipeline run id

每次运行生成：

```text
pipeline_run_id
```

格式：

```text
YYYYMMDD_HHMMSS
```

所有关键输出可以记录该 run id。

---

# 12. Windows 脚本

新增：

```text
scripts/setup_env.ps1
scripts/run_pipeline.ps1
scripts/run_dashboard.ps1
scripts/run_tests.ps1
```

## 12.1 setup_env.ps1

功能：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 12.2 run_pipeline.ps1

```powershell
.\.venv\Scripts\python.exe src\pipeline.py --step all
```

---

## 12.3 run_dashboard.ps1

```powershell
.\.venv\Scripts\streamlit.exe run src\visualization\dashboard_streamlit.py
```

---

## 12.4 run_tests.ps1

```powershell
.\.venv\Scripts\pytest.exe
```

---

# 13. 测试 Phase 2

扩展 tests。

新增：

```text
tests/test_environment.py
tests/test_db_backend.py
tests/test_ccus_standardization.py
tests/test_scenario_engine.py
tests/test_pressure_score.py
tests/test_dashboard_outputs.py
```

## 13.1 必须测试

```text
1. DuckDB backend is used when installed
2. sqlite fallback only allowed when explicitly enabled
3. fact_ev rows > 0
4. fact_ai_energy rows > 0
5. fact_ccus_project rows > 0
6. World cumulative CCUS capacity > 0
7. scenario_region_year_features rows > 0
8. regional_pressure_score between 0 and 100
9. pressure_class belongs to allowed classes
10. dashboard html exists
11. model outputs exist
```

---

# 14. README Phase 2

更新 README.md，新增：

```text
Environment setup on Windows
How to activate .venv
How to verify DuckDB backend
How to run pipeline
How to run tests
How to run Streamlit dashboard
Database backend behavior
sqlite fallback explanation
Scenario engine explanation
Pressure score formula
Known limitations
```

---

# 15. Known Limitations 必须写入 README

必须明确：

```text
1. 当前 IEA EV / AI 数据年份较稀疏，不适合直接训练复杂深度学习模型
2. CCUS capacity 是 mitigation readiness proxy，不等同于直接抵消 EV/AI 用电排放
3. CCUS buffer ratio 不是物理碳平衡公式
4. 区域映射仍有不确定性
5. 没有接入电网碳强度、发电结构、天气、电价前，不应过度解读 grid pressure
6. SQLite fallback 仅用于开发环境临时跑通，不应用作正式分析后端
```

---

# 16. 本阶段验收标准

完成 Phase 2 后，以下命令必须通过：

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

```powershell
.\.venv\Scripts\python.exe src\pipeline.py --step all
```

```powershell
.\.venv\Scripts\pytest.exe
```

```powershell
.\.venv\Scripts\streamlit.exe run src\visualization\dashboard_streamlit.py
```

---

## 16.1 必须生成的文件

```text
data/processed/environment_report.csv
data/processed/database_schema_report.csv
data/processed/data_quality_report.csv
data/processed/ccus_column_mapping_report.csv
data/processed/scenario_region_year_features.csv
data/processed/scenario_comparison_2030.csv
data/processed/model_feature_importance.csv
data/processed/model_explainability.csv

results/ev_ai_ccus_dashboard.html
results/pressure_ranking_2030.html
results/ccus_buffer_ratio_2030.html
results/scenario_comparison_2030.html
results/feature_importance.html
results/cluster_scatter.html
```

---

## 16.2 质量报告要求

```text
CRITICAL = 0
ERROR <= 1
DuckDB backend = PASS
World CCUS cumulative capacity > 0
regional_pressure_score min >= 0
regional_pressure_score max <= 100
scenario_region_year_features rows > 0
```

---

# 17. 给 Codex 的下一步执行 Prompt

可以直接复制下面这段给 Codex：

```text
请根据 CODEX_REQUIREMENTS_PHASE2_EV_AI_CCUS.md 继续开发当前项目。

重要约束：
1. 后续所有命令都使用 .venv\Scripts\python.exe，不要使用 Codex 临时 runtime。
2. DuckDB 必须作为默认数据库后端。
3. sqlite fallback 只能在环境变量 ALLOW_SQLITE_FALLBACK=1 时启用，不能静默 fallback。
4. 不要删除 starter_ev_ai_project.py。
5. 保留当前已经跑通的 MVP 功能。
6. 本阶段不要强行实现深度学习。
7. 优先完成环境检查、DuckDB 后端确认、CCUS 标准化、scenario engine、pressure score 拆分、sklearn 模型增强、Plotly/Streamlit dashboard。

请完成：
1. 更新 requirements.txt，新增 requirements-optional.txt。
2. 新增 scripts/check_env.py，并输出 data/processed/environment_report.csv。
3. 修改 src/db.py，默认 DuckDB，sqlite fallback 仅在 ALLOW_SQLITE_FALLBACK=1 时启用。
4. 新增 pipeline_metadata 表，记录 backend、pipeline_run_id、时间戳和 Python 版本。
5. 新增 src/export_schema.py，输出 data/processed/database_schema_report.csv。
6. 扩展 src/quality_checks.py，增加 severity 和 Phase 2 检查项。
7. 改进 CCUS ingest：输出 ccus_column_mapping_report.csv，标准化 status、年份、capacity，并支持 World / region group / country 聚合。
8. 新增 src/features/scenario_engine.py，生成 scenario_region_year_features 和 scenario_comparison_2030。
9. 改进 pressure score：拆分 demand/growth/ccus/sector share components，并支持 config/pressure_score_weights.json。
10. 如果 scikit-learn 可用，则使用 Ridge、RandomForest、GradientBoosting、KMeans、PCA；否则保留 numpy fallback。
11. 新增模型解释性输出 model_feature_importance.csv 和 model_explainability.csv。
12. 增强 results/ev_ai_ccus_dashboard.html，并新增 Plotly HTML 图。
13. 增强 src/visualization/dashboard_streamlit.py，增加 Scenario Explorer、Data Quality、Model Results、Raw Tables 页面。
14. 新增 scripts/run_pipeline.ps1、scripts/run_dashboard.ps1、scripts/run_tests.ps1、scripts/setup_env.ps1。
15. 扩展 pytest tests，确保 .venv 环境下 pytest 可以通过。
16. 运行：
   .venv\Scripts\python.exe scripts\check_env.py
   .venv\Scripts\python.exe src\pipeline.py --step all
   .venv\Scripts\pytest.exe
并汇总结果。
```

---

# 18. 下一阶段完成后的研究方向

Phase 2 完成后，再进入 Phase 3：

```text
1. 接入电力结构 / renewable share / carbon intensity
2. 接入 GDP / population / industrial electricity demand
3. 接入 ERA5 / NASA POWER 天气数据
4. 做真正的 emission impact modeling
5. 做 SHAP explainability
6. 做 region similarity graph
7. 最后再考虑 Temporal Fusion Transformer / GNN
```