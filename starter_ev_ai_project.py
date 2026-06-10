from pathlib import Path
from html import escape

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
PROCESSED_DIR = ROOT / "processed"
RAW_DIR = ROOT / "data" / "raw"

IEA_2023 = RAW_DIR / "IEA-EV-Data-2023.csv"
IEA_2024 = RAW_DIR / "IEA-EV-Data-2024.csv"
IEA_2025 = RAW_DIR / "IEA-EV-Data-2025.xlsx"
AI_ENERGY = RAW_DIR / "Data_Energy_and_AI.xlsx"

COMMON_REGION_MAP = {
    "World": "World",
    "China": "China",
    "Europe": "Europe",
    "North America": "North America",
    "USA": "United States",
    "United States": "United States",
    "Asia Pacific": "Asia Pacific",
    "Central and South America": "Central and South America",
    "Africa": "Africa",
    "Middle East": "Middle East",
}

PALETTE = ["#2f6f73", "#d1893b", "#6f5a9c", "#b94e48", "#5c6b73", "#3f7cac"]


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(exist_ok=True)


def load_iea_csv(path: Path, version: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "region": "Region",
            "category": "Category",
            "parameter": "Parameter",
            "mode": "Mode",
            "powertrain": "Powertrain",
            "year": "Year",
            "unit": "Unit",
            "value": "Value",
        }
    )
    df["Version"] = version
    df["Aggregate group"] = np.nan
    return df[
        [
            "Version",
            "Region",
            "Aggregate group",
            "Category",
            "Parameter",
            "Mode",
            "Powertrain",
            "Year",
            "Unit",
            "Value",
        ]
    ]


def load_iea_2025(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="GEVO_EV_2025")
    df = df.rename(
        columns={
            "region_country": "Region",
            "category": "Category",
            "parameter": "Parameter",
            "mode": "Mode",
            "powertrain": "Powertrain",
            "year": "Year",
            "unit": "Unit",
            "value": "Value",
        }
    )
    df["Version"] = "2025"
    return df[
        [
            "Version",
            "Region",
            "Aggregate group",
            "Category",
            "Parameter",
            "Mode",
            "Powertrain",
            "Year",
            "Unit",
            "Value",
        ]
    ]


def load_all_ev() -> pd.DataFrame:
    ev = pd.concat(
        [
            load_iea_csv(IEA_2023, "2023"),
            load_iea_csv(IEA_2024, "2024"),
            load_iea_2025(IEA_2025),
        ],
        ignore_index=True,
    )
    ev["Year"] = ev["Year"].astype(int)
    ev["Value"] = pd.to_numeric(ev["Value"], errors="coerce")
    ev["CommonRegion"] = ev["Region"].map(COMMON_REGION_MAP)
    return ev


def profile_ev_versions(ev: pd.DataFrame) -> pd.DataFrame:
    profile = (
        ev.groupby("Version")
        .agg(
            rows=("Value", "size"),
            regions=("Region", "nunique"),
            parameters=("Parameter", "nunique"),
            modes=("Mode", "nunique"),
            powertrains=("Powertrain", "nunique"),
            min_year=("Year", "min"),
            max_year=("Year", "max"),
        )
        .reset_index()
    )
    profile.to_csv(PROCESSED_DIR / "ev_dataset_profile.csv", index=False)
    return profile


def parse_ai_regional(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Regional Data", header=None)
    metric_ranges = {
        "Total installed capacity (GW)": range(5, 14),
        "IT installed capacity (GW)": range(15, 24),
        "Power usage effectiveness": range(30, 39),
        "Load factor (%)": range(40, 49),
        "Total electricity consumption (TWh)": range(56, 65),
        "IT electricity consumption (TWh)": range(66, 75),
    }
    year_cols = {2020: 2, 2023: 3, 2024: 4, 2030: 6}
    records = []
    for metric, rows in metric_ranges.items():
        for row_idx in rows:
            region = raw.iat[row_idx, 1]
            if pd.isna(region):
                continue
            for year, col_idx in year_cols.items():
                value = raw.iat[row_idx, col_idx]
                if not pd.isna(value):
                    records.append(
                        {
                            "Region": str(region),
                            "Metric": metric,
                            "Scenario": "Base Case",
                            "Year": year,
                            "Value": float(value),
                        }
                    )
    ai = pd.DataFrame(records)
    ai.to_csv(PROCESSED_DIR / "ai_energy_regional_long.csv", index=False)
    return ai


def parse_ai_world_scenarios(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="World Data", header=None)
    scenario_cols = {
        ("Historical", 2020): 3,
        ("Historical", 2023): 4,
        ("Historical", 2024): 5,
        ("Base", 2030): 7,
        ("Base", 2035): 8,
        ("Lift-Off", 2030): 10,
        ("Lift-Off", 2035): 11,
        ("High Efficiency", 2030): 13,
        ("High Efficiency", 2035): 14,
        ("Headwinds", 2030): 16,
        ("Headwinds", 2035): 17,
    }
    world = pd.DataFrame(
        [
            {
                "Region": "World",
                "Metric": "Total electricity consumption (TWh)",
                "Scenario": scenario,
                "Year": year,
                "Value": float(raw.iat[23, col_idx]),
            }
            for (scenario, year), col_idx in scenario_cols.items()
        ]
    )
    world.to_csv(PROCESSED_DIR / "ai_world_scenarios.csv", index=False)
    return world


def svg_doc(width: int, height: int, title: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{width / 2:.0f}" y="32" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#222">{escape(title)}</text>
{body}
</svg>
"""


def axis_ticks(max_value: float, count: int = 5) -> list[float]:
    if max_value <= 0:
        return [0]
    raw_step = max_value / count
    magnitude = 10 ** np.floor(np.log10(raw_step))
    step = np.ceil(raw_step / magnitude) * magnitude
    return [float(step * i) for i in range(count + 1)]


def fmt_short(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}k"
    if abs(value) >= 100:
        return f"{value:.0f}"
    return f"{value:.1f}"


def save_version_coverage_plot(profile: pd.DataFrame) -> None:
    width, height = 920, 380
    left, top, plot_w, plot_h = 70, 70, 780, 230
    metrics = [("rows", "Rows"), ("regions", "Regions"), ("max_year", "Max year")]
    group_w = plot_w / len(metrics)
    body = []
    for mi, (metric, label) in enumerate(metrics):
        sub_left = left + mi * group_w + 20
        max_v = float(profile[metric].max())
        body.append(f'<text x="{sub_left + group_w / 2 - 20:.0f}" y="64" text-anchor="middle" font-family="Arial" font-size="13" fill="#555">{label}</text>')
        for i, row in profile.reset_index(drop=True).iterrows():
            bar_w = 48
            x = sub_left + i * 68
            bar_h = (row[metric] / max_v) * (plot_h - 35)
            y = top + plot_h - bar_h
            body.append(f'<rect x="{x:.0f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="3" fill="{PALETTE[i]}"/>')
            body.append(f'<text x="{x + bar_w / 2:.0f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial" font-size="11" fill="#333">{fmt_short(row[metric])}</text>')
            body.append(f'<text x="{x + bar_w / 2:.0f}" y="{top + plot_h + 18:.0f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">{escape(str(row["Version"]))}</text>')
    Path(RESULTS_DIR / "starter_0_iea_version_coverage.svg").write_text(
        svg_doc(width, height, "IEA EV dataset coverage by release", "\n".join(body)),
        encoding="utf-8",
    )


def ev_electricity_twh(ev: pd.DataFrame) -> pd.DataFrame:
    filtered = ev[
        (ev["Version"] == "2025")
        & (ev["Parameter"] == "Electricity demand")
        & (ev["Category"].isin(["Historical", "Projection-STEPS"]))
        & (ev["Year"].isin([2024, 2030]))
        & (ev["CommonRegion"].notna())
    ].copy()
    filtered["Scenario"] = np.where(
        filtered["Category"].eq("Historical"), "Historical", "STEPS"
    )
    grouped = (
        filtered.groupby(["CommonRegion", "Year", "Scenario"], as_index=False)["Value"]
        .sum()
        .rename(columns={"CommonRegion": "Region", "Value": "EV electricity (GWh)"})
    )
    grouped["EV electricity (TWh)"] = grouped["EV electricity (GWh)"] / 1000
    return grouped


def compare_ev_ai_loads(ev: pd.DataFrame, ai: pd.DataFrame) -> pd.DataFrame:
    ev_twh = ev_electricity_twh(ev)
    ai_total = ai[ai["Metric"] == "Total electricity consumption (TWh)"][
        ["Region", "Year", "Value"]
    ].rename(columns={"Value": "AI data center electricity (TWh)"})
    wide_ev = ev_twh.pivot_table(
        index="Region", columns="Year", values="EV electricity (TWh)", aggfunc="sum"
    ).reindex(columns=[2024, 2030]).rename(columns={2024: "EV_2024_TWh", 2030: "EV_2030_TWh"})
    wide_ai = ai_total.pivot_table(
        index="Region",
        columns="Year",
        values="AI data center electricity (TWh)",
        aggfunc="sum",
    ).reindex(columns=[2024, 2030]).rename(columns={2024: "AI_2024_TWh", 2030: "AI_2030_TWh"})
    merged = wide_ev.join(wide_ai, how="inner").reset_index()
    merged = merged.dropna(
        subset=["EV_2024_TWh", "EV_2030_TWh", "AI_2024_TWh", "AI_2030_TWh"]
    )
    merged["EV_CAGR_2024_2030"] = (
        (merged["EV_2030_TWh"] / merged["EV_2024_TWh"]) ** (1 / 6) - 1
    ) * 100
    merged["AI_CAGR_2024_2030"] = (
        (merged["AI_2030_TWh"] / merged["AI_2024_TWh"]) ** (1 / 6) - 1
    ) * 100
    merged["EV_to_AI_2030_ratio"] = merged["EV_2030_TWh"] / merged["AI_2030_TWh"]
    merged.to_csv(PROCESSED_DIR / "ev_ai_region_load_comparison.csv", index=False)
    return merged


def save_load_comparison_plot(comp: pd.DataFrame) -> None:
    plot_df = comp[comp["Region"].ne("World")].sort_values("AI_2030_TWh", ascending=False)
    width, height = 980, 560
    left, top, plot_w, plot_h = 86, 70, 820, 360
    max_v = max(plot_df["AI_2030_TWh"].max(), plot_df["EV_2030_TWh"].max())
    ticks = axis_ticks(max_v)
    body = []
    for tick in ticks:
        y = top + plot_h - tick / ticks[-1] * plot_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        body.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{fmt_short(tick)}</text>')
    group_w = plot_w / len(plot_df)
    for i, row in plot_df.reset_index(drop=True).iterrows():
        cx = left + i * group_w + group_w / 2
        for j, (col, color) in enumerate([("AI_2030_TWh", "#5c6b73"), ("EV_2030_TWh", "#d1893b")]):
            bar_w = min(34, group_w / 3)
            x = cx + (j - 0.5) * (bar_w + 4)
            bar_h = row[col] / ticks[-1] * plot_h
            y = top + plot_h - bar_h
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="3" fill="{color}"/>')
        body.append(f'<text x="{cx:.1f}" y="{top + plot_h + 20}" text-anchor="middle" font-family="Arial" font-size="11" fill="#333" transform="rotate(25 {cx:.1f},{top + plot_h + 20})">{escape(row["Region"])}</text>')
    body.extend(
        [
            '<rect x="650" y="70" width="14" height="14" fill="#5c6b73"/>',
            '<text x="670" y="82" font-family="Arial" font-size="12" fill="#333">AI data centers, 2030 Base</text>',
            '<rect x="650" y="92" width="14" height="14" fill="#d1893b"/>',
            '<text x="670" y="104" font-family="Arial" font-size="12" fill="#333">EVs, 2030 IEA STEPS</text>',
            f'<text x="{left - 54}" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333" transform="rotate(-90 {left - 54},{top + plot_h / 2:.0f})">Electricity demand (TWh)</text>',
        ]
    )
    Path(RESULTS_DIR / "starter_1_ev_ai_2030_load_comparison.svg").write_text(
        svg_doc(width, height, "2030 electricity demand: EVs vs AI data centers", "\n".join(body)),
        encoding="utf-8",
    )


def save_growth_quadrant_plot(comp: pd.DataFrame) -> None:
    plot_df = comp[comp["Region"].ne("World")].copy()
    width, height = 900, 560
    left, top, plot_w, plot_h = 90, 70, 680, 360
    x_min, x_max = plot_df["AI_CAGR_2024_2030"].min() - 1, plot_df["AI_CAGR_2024_2030"].max() + 1
    y_min, y_max = plot_df["EV_CAGR_2024_2030"].min() - 1, plot_df["EV_CAGR_2024_2030"].max() + 1
    x_mid, y_mid = plot_df["AI_CAGR_2024_2030"].median(), plot_df["EV_CAGR_2024_2030"].median()

    def sx(v: float) -> float:
        return left + (v - x_min) / (x_max - x_min) * plot_w

    def sy(v: float) -> float:
        return top + plot_h - (v - y_min) / (y_max - y_min) * plot_h

    body = [
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fbfbfb" stroke="#dddddd"/>',
        f'<line x1="{sx(x_mid):.1f}" y1="{top}" x2="{sx(x_mid):.1f}" y2="{top + plot_h}" stroke="#999" stroke-dasharray="5 5"/>',
        f'<line x1="{left}" y1="{sy(y_mid):.1f}" x2="{left + plot_w}" y2="{sy(y_mid):.1f}" stroke="#999" stroke-dasharray="5 5"/>',
    ]
    max_ev = plot_df["EV_2030_TWh"].max()
    max_ratio = plot_df["EV_to_AI_2030_ratio"].max()
    for _, row in plot_df.iterrows():
        r = 9 + 22 * np.sqrt(row["EV_2030_TWh"] / max_ev)
        color_idx = min(len(PALETTE) - 1, int(row["EV_to_AI_2030_ratio"] / max_ratio * (len(PALETTE) - 1)))
        body.append(f'<circle cx="{sx(row["AI_CAGR_2024_2030"]):.1f}" cy="{sy(row["EV_CAGR_2024_2030"]):.1f}" r="{r:.1f}" fill="{PALETTE[color_idx]}" opacity="0.78" stroke="#fff" stroke-width="1.5"/>')
        body.append(f'<text x="{sx(row["AI_CAGR_2024_2030"]) + r + 3:.1f}" y="{sy(row["EV_CAGR_2024_2030"]) + 4:.1f}" font-family="Arial" font-size="11" fill="#333">{escape(row["Region"])}</text>')
    body.extend(
        [
            f'<text x="{left + plot_w / 2:.0f}" y="{top + plot_h + 52}" text-anchor="middle" font-family="Arial" font-size="13" fill="#333">AI data center electricity CAGR, 2024-2030 (%)</text>',
            f'<text x="{left - 58}" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-family="Arial" font-size="13" fill="#333" transform="rotate(-90 {left - 58},{top + plot_h / 2:.0f})">EV electricity demand CAGR, 2024-2030 (%)</text>',
            f'<text x="{left}" y="{top + plot_h + 20}" font-family="Arial" font-size="11" fill="#555">{x_min:.1f}%</text>',
            f'<text x="{left + plot_w}" y="{top + plot_h + 20}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{x_max:.1f}%</text>',
            f'<text x="{left - 8}" y="{top + 4}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{y_max:.1f}%</text>',
            f'<text x="{left - 8}" y="{top + plot_h}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{y_min:.1f}%</text>',
        ]
    )
    Path(RESULTS_DIR / "starter_2_ev_ai_growth_quadrants.svg").write_text(
        svg_doc(width, height, "Where EV load and AI data center load grow fastest", "\n".join(body)),
        encoding="utf-8",
    )


def save_ai_world_scenario_plot(world: pd.DataFrame) -> None:
    width, height = 880, 500
    left, top, plot_w, plot_h = 80, 70, 650, 330
    years = [2020, 2023, 2024, 2030, 2035]
    max_v = world["Value"].max() * 1.08

    def sx(year: float) -> float:
        return left + (year - 2020) / (2035 - 2020) * plot_w

    def sy(value: float) -> float:
        return top + plot_h - value / max_v * plot_h

    body = [f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fbfbfb" stroke="#dddddd"/>']
    for tick in axis_ticks(max_v):
        y = sy(tick)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{fmt_short(tick)}</text>')
    scenarios = ["Historical", "Base", "Lift-Off", "High Efficiency", "Headwinds"]
    hist_2024 = world[(world["Scenario"] == "Historical") & (world["Year"] == 2024)]
    for idx, scenario in enumerate(scenarios):
        if scenario == "Historical":
            line = world[world["Scenario"] == scenario].sort_values("Year")
        else:
            line = pd.concat([hist_2024, world[world["Scenario"] == scenario]], ignore_index=True).sort_values("Year")
        points = " ".join(f'{sx(row.Year):.1f},{sy(row.Value):.1f}' for row in line.itertuples())
        body.append(f'<polyline points="{points}" fill="none" stroke="{PALETTE[idx]}" stroke-width="2.5"/>')
        for row in line.itertuples():
            body.append(f'<circle cx="{sx(row.Year):.1f}" cy="{sy(row.Value):.1f}" r="4" fill="{PALETTE[idx]}"/>')
        body.append(f'<rect x="748" y="{78 + idx * 24}" width="13" height="13" fill="{PALETTE[idx]}"/>')
        body.append(f'<text x="768" y="{89 + idx * 24}" font-family="Arial" font-size="12" fill="#333">{escape(scenario)}</text>')
    for year in years:
        body.append(f'<text x="{sx(year):.1f}" y="{top + plot_h + 20}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{year}</text>')
    body.append(f'<text x="{left - 50}" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333" transform="rotate(-90 {left - 50},{top + plot_h / 2:.0f})">Electricity consumption (TWh)</text>')
    Path(RESULTS_DIR / "starter_3_ai_world_scenarios.svg").write_text(
        svg_doc(width, height, "Global AI data center electricity scenarios", "\n".join(body)),
        encoding="utf-8",
    )


def build_design(df: pd.DataFrame, region_levels=None, powertrain_levels=None) -> tuple[np.ndarray, list[str], list[str]]:
    if region_levels is None:
        region_levels = sorted(df["Region"].unique())
    if powertrain_levels is None:
        powertrain_levels = sorted(df["Powertrain"].unique())
    year_scaled = (df["Year"].to_numpy(dtype=float) - 2017.0) / 10.0
    cols = [np.ones(len(df)), year_scaled, year_scaled**2]
    for level in region_levels:
        cols.append((df["Region"].to_numpy() == level).astype(float))
    for level in powertrain_levels:
        cols.append((df["Powertrain"].to_numpy() == level).astype(float))
    return np.column_stack(cols), region_levels, powertrain_levels


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    penalty = np.eye(x.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + penalty, x.T @ y)


def predict_ridge(df: pd.DataFrame, beta: np.ndarray, region_levels: list[str], powertrain_levels: list[str]) -> np.ndarray:
    x, _, _ = build_design(df, region_levels, powertrain_levels)
    return np.clip(np.expm1(x @ beta), 0, None)


def ml_ev_sales_forecast(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = ev[
        (ev["Version"] == "2025")
        & (ev["Parameter"] == "EV sales")
        & (ev["Mode"] == "Cars")
        & (ev["Category"] == "Historical")
        & (ev["Powertrain"].isin(["BEV", "PHEV", "FCEV"]))
    ].copy()
    sales = sales.groupby(["Region", "Powertrain", "Year"], as_index=False)["Value"].sum()
    sales = sales[sales["Value"] > 0].copy()

    train = sales[sales["Year"] <= 2022].copy()
    test = sales[sales["Year"].isin([2023, 2024])].copy()
    x_train, region_levels, powertrain_levels = build_design(train)
    beta = fit_ridge(x_train, np.log1p(train["Value"].to_numpy()), alpha=2.0)
    pred = predict_ridge(test, beta, region_levels, powertrain_levels)
    rmsle = np.sqrt(np.mean((np.log1p(pred) - np.log1p(test["Value"].to_numpy())) ** 2))
    mae = float(np.mean(np.abs(pred - test["Value"].to_numpy())))
    metrics = pd.DataFrame(
        [{"holdout_years": "2023-2024", "rows": len(test), "MAE_vehicles": mae, "RMSLE": rmsle}]
    )
    metrics.to_csv(PROCESSED_DIR / "ev_ml_holdout_metrics.csv", index=False)

    x_all, region_levels, powertrain_levels = build_design(sales)
    beta = fit_ridge(x_all, np.log1p(sales["Value"].to_numpy()), alpha=2.0)
    future = sales[sales["Year"] == 2024][["Region", "Powertrain"]].drop_duplicates()
    future["Year"] = 2030
    future["ML_2030_sales"] = predict_ridge(future, beta, region_levels, powertrain_levels)

    iea_2030 = ev[
        (ev["Version"] == "2025")
        & (ev["Parameter"] == "EV sales")
        & (ev["Mode"] == "Cars")
        & (ev["Category"] == "Projection-STEPS")
        & (ev["Year"] == 2030)
        & (ev["Powertrain"].isin(["BEV", "PHEV", "FCEV"]))
    ]
    iea_2030 = (
        iea_2030.groupby(["Region", "Powertrain"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "IEA_STEPS_2030_sales"})
    )
    comparison = future.merge(iea_2030, on=["Region", "Powertrain"], how="inner")
    comparison["ML_to_IEA_ratio"] = comparison["ML_2030_sales"] / comparison["IEA_STEPS_2030_sales"]
    comparison.to_csv(PROCESSED_DIR / "ev_ml_forecast_vs_iea_2030.csv", index=False)
    return metrics, comparison


def save_ml_forecast_plot(ev: pd.DataFrame, comparison: pd.DataFrame, metrics: pd.DataFrame) -> None:
    historical_world = ev[
        (ev["Version"] == "2025")
        & (ev["Region"] == "World")
        & (ev["Parameter"] == "EV sales")
        & (ev["Mode"] == "Cars")
        & (ev["Category"] == "Historical")
        & (ev["Powertrain"].isin(["BEV", "PHEV", "FCEV"]))
    ].groupby("Year", as_index=False)["Value"].sum()
    world_comparison = comparison[comparison["Region"] == "World"]
    ml_2030 = world_comparison["ML_2030_sales"].sum()
    iea_2030 = world_comparison["IEA_STEPS_2030_sales"].sum()
    width, height = 880, 500
    left, top, plot_w, plot_h = 80, 70, 650, 330
    max_v = max(historical_world["Value"].max(), ml_2030, iea_2030) / 1_000_000 * 1.12

    def sx(year: float) -> float:
        return left + (year - 2010) / (2030 - 2010) * plot_w

    def sy(million: float) -> float:
        return top + plot_h - million / max_v * plot_h

    body = [f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fbfbfb" stroke="#dddddd"/>']
    for tick in axis_ticks(max_v):
        y = sy(tick)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        body.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{tick:.0f}</text>')
    points = " ".join(f'{sx(row.Year):.1f},{sy(row.Value / 1_000_000):.1f}' for row in historical_world.itertuples())
    body.append(f'<polyline points="{points}" fill="none" stroke="#2f6f73" stroke-width="2.6"/>')
    for row in historical_world.itertuples():
        body.append(f'<circle cx="{sx(row.Year):.1f}" cy="{sy(row.Value / 1_000_000):.1f}" r="3.5" fill="#2f6f73"/>')
    last = historical_world.iloc[-1]
    for value, color, label, dy in [
        (ml_2030 / 1_000_000, "#d1893b", "ML baseline 2030", -12),
        (iea_2030 / 1_000_000, "#6f5a9c", "IEA STEPS 2030", 18),
    ]:
        body.append(f'<line x1="{sx(last.Year):.1f}" y1="{sy(last.Value / 1_000_000):.1f}" x2="{sx(2030):.1f}" y2="{sy(value):.1f}" stroke="{color}" stroke-dasharray="6 5" stroke-width="2"/>')
        body.append(f'<circle cx="{sx(2030):.1f}" cy="{sy(value):.1f}" r="7" fill="{color}"/>')
        body.append(f'<text x="{sx(2030) + 10:.1f}" y="{sy(value) + dy:.1f}" font-family="Arial" font-size="12" fill="#333">{label}: {value:.1f}M</text>')
    for year in [2010, 2015, 2020, 2025, 2030]:
        body.append(f'<text x="{sx(year):.1f}" y="{top + plot_h + 20}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{year}</text>')
    body.append(f'<text x="{left - 50}" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333" transform="rotate(-90 {left - 50},{top + plot_h / 2:.0f})">Global EV car sales (million)</text>')
    body.append(f'<text x="{left + 12}" y="{top + 22}" font-family="Arial" font-size="12" fill="#333">Holdout RMSLE: {metrics.iloc[0]["RMSLE"]:.2f}</text>')
    Path(RESULTS_DIR / "starter_4_ml_ev_sales_forecast.svg").write_text(
        svg_doc(width, height, "EV sales forecast baseline vs IEA 2030 STEPS", "\n".join(body)),
        encoding="utf-8",
    )


def save_dashboard_html(profile: pd.DataFrame, comparison: pd.DataFrame, metrics: pd.DataFrame) -> None:
    cards = [
        ("IEA releases loaded", f"{len(profile)}"),
        ("2025 EV rows", f"{int(profile.loc[profile['Version'].eq('2025'), 'rows'].iloc[0]):,}"),
        ("Common EV/AI regions", f"{len(comparison)}"),
        ("ML holdout RMSLE", f"{metrics.iloc[0]['RMSLE']:.2f}"),
    ]
    card_html = "\n".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>'
        for label, value in cards
    )
    region_rows = "\n".join(
        "<tr>"
        f"<td>{escape(row.Region)}</td>"
        f"<td>{row.EV_2030_TWh:,.1f}</td>"
        f"<td>{row.AI_2030_TWh:,.1f}</td>"
        f"<td>{row.EV_to_AI_2030_ratio:.2f}</td>"
        "</tr>"
        for row in comparison.sort_values("EV_2030_TWh", ascending=False).itertuples()
    )
    figures = [
        "starter_0_iea_version_coverage.svg",
        "starter_1_ev_ai_2030_load_comparison.svg",
        "starter_2_ev_ai_growth_quadrants.svg",
        "starter_3_ai_world_scenarios.svg",
        "starter_4_ml_ev_sales_forecast.svg",
    ]
    figure_html = "\n".join(
        f'<section><img src="{name}" alt="{name}"/></section>' for name in figures
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>EV and AI Energy Starter Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #222; background: #f6f7f5; }}
    header {{ padding: 28px 34px 12px; background: #ffffff; border-bottom: 1px solid #e5e5e5; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    p {{ margin: 0; color: #555; line-height: 1.5; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }}
    .card {{ background: #fff; border: 1px solid #e2e2e2; border-radius: 8px; padding: 14px; }}
    .label {{ font-size: 12px; color: #666; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
    section {{ background: #fff; border: 1px solid #e2e2e2; border-radius: 8px; margin: 16px 0; padding: 10px; overflow-x: auto; }}
    img {{ width: 100%; height: auto; display: block; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; margin-top: 10px; }}
    th, td {{ text-align: right; border-bottom: 1px solid #e8e8e8; padding: 9px 10px; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ color: #555; font-size: 12px; }}
    @media (max-width: 800px) {{ .cards {{ grid-template-columns: repeat(2, 1fr); }} }}
  </style>
</head>
<body>
  <header>
    <h1>EV and AI Energy Starter Dashboard</h1>
    <p>Initial project scaffold using IEA EV 2023/2024/2025 data and the AI energy workbook.</p>
  </header>
  <main>
    <div class="cards">{card_html}</div>
    <section>
      <table>
        <thead><tr><th>Region</th><th>EV 2030 TWh</th><th>AI 2030 TWh</th><th>EV / AI ratio</th></tr></thead>
        <tbody>{region_rows}</tbody>
      </table>
    </section>
    {figure_html}
  </main>
</body>
</html>
"""
    (RESULTS_DIR / "starter_dashboard.html").write_text(html, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    ev = load_all_ev()
    ai = parse_ai_regional(AI_ENERGY)
    ai_world = parse_ai_world_scenarios(AI_ENERGY)

    profile = profile_ev_versions(ev)
    save_version_coverage_plot(profile)

    comparison = compare_ev_ai_loads(ev, ai)
    save_load_comparison_plot(comparison)
    save_growth_quadrant_plot(comparison)
    save_ai_world_scenario_plot(ai_world)

    metrics, ml_comparison = ml_ev_sales_forecast(ev)
    save_ml_forecast_plot(ev, ml_comparison, metrics)
    save_dashboard_html(profile, comparison, metrics)

    print("Created starter analysis outputs:")
    for path in [
        RESULTS_DIR / "starter_dashboard.html",
        RESULTS_DIR / "starter_0_iea_version_coverage.svg",
        RESULTS_DIR / "starter_1_ev_ai_2030_load_comparison.svg",
        RESULTS_DIR / "starter_2_ev_ai_growth_quadrants.svg",
        RESULTS_DIR / "starter_3_ai_world_scenarios.svg",
        RESULTS_DIR / "starter_4_ml_ev_sales_forecast.svg",
        PROCESSED_DIR / "ev_dataset_profile.csv",
        PROCESSED_DIR / "ai_energy_regional_long.csv",
        PROCESSED_DIR / "ai_world_scenarios.csv",
        PROCESSED_DIR / "ev_ai_region_load_comparison.csv",
        PROCESSED_DIR / "ev_ml_holdout_metrics.csv",
        PROCESSED_DIR / "ev_ml_forecast_vs_iea_2030.csv",
    ]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
