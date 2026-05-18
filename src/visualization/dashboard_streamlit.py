from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover - import-time message for missing optional dep
    raise SystemExit("Streamlit is not installed. Run `pip install -r requirements.txt` first.") from exc


ROOT = Path(__file__).resolve().parents[2]
FEATURE_PATH = ROOT / "data" / "processed" / "ml_region_year_features.csv"
CLUSTER_PATH = ROOT / "data" / "processed" / "region_clusters.csv"
QUALITY_PATH = ROOT / "data" / "processed" / "data_quality_report.csv"
SCENARIO_PATH = ROOT / "data" / "processed" / "scenario_region_year_features.csv"
IMPORTANCE_PATH = ROOT / "data" / "processed" / "model_feature_importance.csv"

st.set_page_config(page_title="EV-AI-CCUS Dashboard", layout="wide")
st.title("EV-AI-CCUS Regional Energy Pressure Intelligence System")

df = pd.read_csv(FEATURE_PATH)
clusters = pd.read_csv(CLUSTER_PATH) if CLUSTER_PATH.exists() else pd.DataFrame()
quality = pd.read_csv(QUALITY_PATH) if QUALITY_PATH.exists() else pd.DataFrame()
scenario_df = pd.read_csv(SCENARIO_PATH) if SCENARIO_PATH.exists() else pd.DataFrame()
importance = pd.read_csv(IMPORTANCE_PATH) if IMPORTANCE_PATH.exists() else pd.DataFrame()

year = st.sidebar.selectbox("Year", sorted(df["year"].unique()), index=len(sorted(df["year"].unique())) - 1)
ev_scenario = st.sidebar.selectbox("EV scenario", sorted(df["ev_scenario"].unique()))
ai_scenario = st.sidebar.selectbox("AI scenario", sorted(df["ai_scenario"].unique()))

view = df[(df["year"] == year) & (df["ev_scenario"] == ev_scenario) & (df["ai_scenario"] == ai_scenario)]

tabs = st.tabs(["Overview", "Data Quality", "Scenario Explorer", "Regional Pressure Ranking", "CCUS Explorer", "Model Results", "Raw Tables"])

with tabs[0]:
    st.metric("Rows", len(view))
    st.metric("Max pressure", f"{view['regional_pressure_score'].max():.1f}")
    left, right = st.columns(2)
    left.bar_chart(view.set_index("common_region")["regional_pressure_score"])
    right.scatter_chart(view, x="combined_electricity_demand_twh", y="regional_pressure_score", color="pressure_class")

with tabs[1]:
    st.dataframe(quality, use_container_width=True)

with tabs[2]:
    if not scenario_df.empty:
        ccus_scenario = st.sidebar.selectbox("CCUS scenario", sorted(scenario_df["ccus_scenario"].unique()))
        sv = scenario_df[
            (scenario_df["year"] == year)
            & (scenario_df["ev_scenario"] == ev_scenario)
            & (scenario_df["ai_scenario"] == ai_scenario)
            & (scenario_df["ccus_scenario"] == ccus_scenario)
        ]
        st.dataframe(sv.sort_values("regional_pressure_score", ascending=False), use_container_width=True)
        st.download_button("Download scenario CSV", sv.to_csv(index=False), file_name="scenario_filtered.csv")

with tabs[3]:
    st.dataframe(view.sort_values("regional_pressure_score", ascending=False), use_container_width=True)
    st.download_button("Download filtered CSV", view.to_csv(index=False), file_name="ev_ai_ccus_filtered.csv")

with tabs[4]:
    cols = ["common_region", "year", "cumulative_ccus_capacity_mtpa", "ccus_capacity_per_twh_demand", "regional_pressure_score"]
    st.dataframe(view[[c for c in cols if c in view.columns]].sort_values("ccus_capacity_per_twh_demand", ascending=False), use_container_width=True)

with tabs[5]:
    st.dataframe(importance, use_container_width=True)
    if not clusters.empty:
        st.subheader("Regional clusters")
        st.dataframe(clusters, use_container_width=True)

with tabs[6]:
    st.dataframe(df, use_container_width=True)
