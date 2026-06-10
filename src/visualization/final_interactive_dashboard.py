import json
import math
import shutil
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
PROCESSED_DIR = ROOT / "data" / "processed"
HTML_PATH = ROOT / "EV_AI_CCUS_Interactive_Dashboard.html"

PNG_FILES = {
    "pressure_ranking_2030.png",
    "combined_demand_by_region.png",
    "ev_ai_mix_2030.png",
    "ccus_buffer_ratio_2030.png",
    "scenario_pressure_comparison_2030.png",
    "feature_importance.png",
    "cluster_scatter.png",
}


def read_csv(name):
    path = PROCESSED_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def clean_results():
    RESULTS_DIR.mkdir(exist_ok=True)
    resolved = RESULTS_DIR.resolve()
    if resolved != (ROOT / "results").resolve():
        raise RuntimeError(f"Refusing to clean unexpected results path: {resolved}")
    for item in RESULTS_DIR.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def font(size=18, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def safe_number(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def draw_bar_png(df, label_col, value_col, title, path, color=(47, 111, 115), limit=12):
    width, height = 1400, 860
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font, label_font, small_font = font(30, True), font(18), font(16)
    draw.text((width // 2, 38), title, fill=(30, 30, 30), font=title_font, anchor="mm")
    if df.empty or value_col not in df:
        draw.text((width // 2, height // 2), "No data", fill=(80, 80, 80), font=title_font, anchor="mm")
        img.save(path)
        return
    plot = df[[label_col, value_col]].dropna().sort_values(value_col, ascending=False).head(limit)
    max_value = max(plot[value_col].map(safe_number).max(), 1)
    left, top, bar_h, gap, plot_w = 330, 110, 42, 18, 900
    for i, row in enumerate(plot.itertuples(index=False)):
        label, value = str(row[0]), safe_number(row[1])
        y = top + i * (bar_h + gap)
        bar_w = int(value / max_value * plot_w)
        draw.text((left - 16, y + bar_h // 2), label[:28], fill=(35, 35, 35), font=label_font, anchor="rm")
        draw.rounded_rectangle((left, y, left + bar_w, y + bar_h), radius=8, fill=color)
        draw.text((left + bar_w + 12, y + bar_h // 2), f"{value:,.1f}", fill=(35, 35, 35), font=small_font, anchor="lm")
    img.save(path)


def draw_stacked_png(df, title, path, limit=12):
    width, height = 1400, 860
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font, label_font, small_font = font(30, True), font(18), font(16)
    draw.text((width // 2, 38), title, fill=(30, 30, 30), font=title_font, anchor="mm")
    plot = df.dropna(subset=["common_region"]).sort_values("combined_electricity_demand_twh", ascending=False).head(limit)
    max_value = max(plot["combined_electricity_demand_twh"].map(safe_number).max(), 1)
    left, top, bar_h, gap, plot_w = 330, 110, 42, 18, 900
    ev_color, ai_color = (47, 111, 115), (217, 143, 69)
    for i, row in enumerate(plot.itertuples()):
        ev = safe_number(row.ev_electricity_twh)
        ai = safe_number(row.ai_electricity_twh)
        total = max(ev + ai, 1)
        y = top + i * (bar_h + gap)
        ev_w = int(ev / max_value * plot_w)
        ai_w = int(ai / max_value * plot_w)
        draw.text((left - 16, y + bar_h // 2), str(row.common_region)[:28], fill=(35, 35, 35), font=label_font, anchor="rm")
        draw.rounded_rectangle((left, y, left + ev_w, y + bar_h), radius=8, fill=ev_color)
        draw.rectangle((left + ev_w, y, left + ev_w + ai_w, y + bar_h), fill=ai_color)
        draw.text((left + ev_w + ai_w + 12, y + bar_h // 2), f"{total:,.1f}", fill=(35, 35, 35), font=small_font, anchor="lm")
    draw.rectangle((1020, 70, 1040, 90), fill=ev_color)
    draw.text((1048, 80), "EV TWh", fill=(35, 35, 35), font=small_font, anchor="lm")
    draw.rectangle((1140, 70, 1160, 90), fill=ai_color)
    draw.text((1168, 80), "AI TWh", fill=(35, 35, 35), font=small_font, anchor="lm")
    img.save(path)


def draw_scatter_png(df, title, path, x_col, y_col, label_col="common_region"):
    width, height = 1400, 860
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font, label_font, small_font = font(30, True), font(18), font(15)
    draw.text((width // 2, 38), title, fill=(30, 30, 30), font=title_font, anchor="mm")
    if df.empty or x_col not in df or y_col not in df:
        draw.text((width // 2, height // 2), "No data", fill=(80, 80, 80), font=title_font, anchor="mm")
        img.save(path)
        return
    left, top, plot_w, plot_h = 150, 100, 1080, 620
    draw.rectangle((left, top, left + plot_w, top + plot_h), outline=(210, 210, 210), fill=(250, 250, 250))
    x_values = df[x_col].map(safe_number)
    y_values = df[y_col].map(safe_number)
    x_min, x_max = min(x_values.min(), 0), max(x_values.max(), 1)
    y_min, y_max = min(y_values.min(), 0), max(y_values.max(), 1)
    palette = [(47, 111, 115), (217, 143, 69), (111, 90, 156), (185, 78, 72)]
    used_positions = []
    for i, row in enumerate(df.itertuples()):
        x_val, y_val = safe_number(getattr(row, x_col)), safe_number(getattr(row, y_col))
        x = left + int((x_val - x_min) / (x_max - x_min) * plot_w)
        y = top + plot_h - int((y_val - y_min) / (y_max - y_min) * plot_h)
        color = palette[i % len(palette)]
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=color, outline="white", width=2)
        label = str(getattr(row, label_col))[:18]
        # Draw only sparse labels when there is room; hover labels in HTML carry the full detail.
        if all(abs(x - px) > 110 or abs(y - py) > 28 for px, py in used_positions):
            draw.text((x + 14, y), label, fill=(45, 45, 45), font=small_font, anchor="lm")
            used_positions.append((x, y))
    draw.text((left + plot_w // 2, top + plot_h + 48), x_col.replace("_", " "), fill=(35, 35, 35), font=label_font, anchor="mm")
    draw.text((left - 70, top + plot_h // 2), y_col.replace("_", " "), fill=(35, 35, 35), font=label_font, anchor="mm")
    img.save(path)


def to_records(df):
    if df.empty:
        return []
    clean = df.copy()
    clean = clean.where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def build_pngs(ml, scenario, importance, clusters):
    focus_2030 = ml[ml["year"].eq(2030)].copy()
    scenario_2030 = scenario[scenario["year"].eq(2030)].copy()
    if focus_2030.empty:
        focus_2030 = ml.copy()
    if scenario_2030.empty:
        scenario_2030 = scenario.copy()
    draw_bar_png(focus_2030, "common_region", "regional_pressure_score", "2030 Regional Pressure Ranking", RESULTS_DIR / "pressure_ranking_2030.png", (185, 78, 72))
    draw_bar_png(focus_2030, "common_region", "combined_electricity_demand_twh", "2030 Combined EV + AI Demand (TWh)", RESULTS_DIR / "combined_demand_by_region.png", (92, 107, 115))
    draw_stacked_png(focus_2030, "2030 EV vs AI Electricity Mix (TWh)", RESULTS_DIR / "ev_ai_mix_2030.png")
    buffer_col = "ccus_capacity_per_twh_demand" if "ccus_capacity_per_twh_demand" in focus_2030 else "ccus_buffer_ratio"
    draw_bar_png(focus_2030, "common_region", buffer_col, "2030 CCUS Buffer Ratio", RESULTS_DIR / "ccus_buffer_ratio_2030.png", (111, 90, 156))
    draw_bar_png(scenario_2030, "common_region", "regional_pressure_score", "2030 Scenario Pressure Comparison", RESULTS_DIR / "scenario_pressure_comparison_2030.png", (217, 143, 69))
    imp = importance.sort_values("importance", ascending=False).head(12) if not importance.empty else importance
    if not imp.empty:
        imp["feature_label"] = imp["model"].astype(str) + ": " + imp["feature"].astype(str)
    draw_bar_png(imp, "feature_label", "importance", "Model Feature Importance", RESULTS_DIR / "feature_importance.png", (47, 111, 115))
    x_col = "pca_x" if "pca_x" in clusters else "combined_electricity_demand_twh"
    y_col = "pca_y" if "pca_y" in clusters else "regional_pressure_score"
    draw_scatter_png(clusters, "Regional Cluster Scatter", RESULTS_DIR / "cluster_scatter.png", x_col, y_col)


def build_html(ml, scenario, importance, clusters, quality):
    option_source = scenario if not scenario.empty else ml
    years = sorted({int(x) for x in option_source.get("year", pd.Series(dtype=int)).dropna().unique()})
    regions = sorted(str(x) for x in option_source.get("common_region", pd.Series(dtype=str)).dropna().unique())
    ev_scenarios = sorted(str(x) for x in option_source.get("ev_scenario", pd.Series(dtype=str)).dropna().unique())
    ai_scenarios = sorted(str(x) for x in option_source.get("ai_scenario", pd.Series(dtype=str)).dropna().unique())
    ccus_scenarios = sorted(str(x) for x in scenario.get("ccus_scenario", pd.Series(dtype=str)).dropna().unique())
    if not years:
        years = [2030]
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>EV-AI-CCUS Interactive Energy Dashboard</title>
  <style>
    :root {{ --ink:#20242a; --muted:#65717c; --line:#dfe3e6; --bg:#f5f7f6; --panel:#fff; --teal:#2f6f73; --gold:#d98f45; --red:#b94e48; --violet:#6f5a9c; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial, sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ padding:22px 28px; background:#fff; border-bottom:1px solid var(--line); position:sticky; top:0; z-index:5; }}
    h1 {{ margin:0 0 8px; font-size:26px; }}
    .sub {{ color:var(--muted); }}
    main {{ max-width:1320px; margin:0 auto; padding:18px; }}
    .controls {{ display:grid; grid-template-columns: repeat(5, minmax(150px,1fr)); gap:12px; margin:16px 0; }}
    label {{ display:grid; gap:5px; font-size:12px; color:var(--muted); }}
    select {{ padding:9px 10px; border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--ink); }}
    .cards {{ display:grid; grid-template-columns: repeat(4,1fr); gap:12px; }}
    .card, section {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .card span {{ color:var(--muted); font-size:12px; }}
    .card strong {{ display:block; margin-top:4px; font-size:24px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }}
    section.wide {{ grid-column:1 / -1; }}
    .chart {{ min-height:390px; overflow:hidden; }}
    svg {{ width:100%; height:auto; display:block; }}
    .bar:hover, .point:hover {{ filter:brightness(1.1); stroke:#111; stroke-width:2; }}
    select option:disabled {{ color:#9aa3aa; }}
    .empty-banner {{ display:none; margin:10px 0 14px; padding:10px 12px; border:1px solid #e3b76b; background:#fff8e8; color:#6c4a12; border-radius:8px; }}
    .empty-state {{ min-height:220px; display:flex; align-items:center; justify-content:center; color:#6c4a12; background:#fff8e8; border:1px dashed #e3b76b; border-radius:8px; padding:14px; text-align:center; }}
    .empty-card {{ grid-column:1 / -1; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ padding:7px 9px; border-bottom:1px solid #edf0f1; text-align:right; white-space:nowrap; }}
    th:first-child,td:first-child {{ text-align:left; }}
    .tooltip {{ position:fixed; pointer-events:none; display:none; background:#1f2428; color:#fff; padding:8px 10px; border-radius:6px; font-size:12px; max-width:320px; z-index:10; box-shadow:0 6px 20px rgba(0,0,0,.22); }}
    .pngs {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .pngs a {{ color:var(--teal); text-decoration:none; border:1px solid var(--line); background:#fff; padding:7px 9px; border-radius:6px; }}
    @media(max-width:900px) {{ .controls,.cards,.grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>EV-AI-CCUS Interactive Energy Dashboard</h1>
  <div class="sub">Hover charts for exact values. Use filters to switch year, region, and scenarios. Scatter charts avoid static labels to prevent annotation overlap.</div>
</header>
<main>
  <div class="controls">
    <label>Year<select id="year"></select></label>
    <label>Region<select id="region"></select></label>
    <label>EV scenario<select id="evScenario"></select></label>
    <label>AI scenario<select id="aiScenario"></select></label>
    <label>CCUS scenario<select id="ccusScenario"></select></label>
  </div>
  <div id="emptyNotice" class="empty-banner">该情景组合下数据暂时缺失，请尝试切换年份、地区或情景组合。</div>
  <div class="cards" id="cards"></div>
  <div class="grid">
    <section><h2>Pressure Ranking</h2><div id="ranking" class="chart"></div></section>
    <section><h2>Combined Demand Scatter</h2><div id="scatter" class="chart"></div></section>
    <section><h2>EV vs AI Mix</h2><div id="mix" class="chart"></div></section>
    <section><h2>CCUS Buffer</h2><div id="buffer" class="chart"></div></section>
    <section><h2>Feature Importance</h2><div id="importance" class="chart"></div></section>
    <section><h2>Cluster Scatter</h2><div id="cluster" class="chart"></div></section>
    <section class="wide"><h2>Filtered Data</h2><div id="table"></div></section>
    <section class="wide"><h2>PNG Exports</h2><div class="pngs">{''.join(f'<a href="results/{name}">{name}</a>' for name in sorted(PNG_FILES))}</div></section>
  </div>
</main>
<div class="tooltip" id="tooltip"></div>
<script>
const SCENARIO_DATA = {json.dumps(to_records(scenario), ensure_ascii=False)};
const IMPORTANCE = {json.dumps(to_records(importance), ensure_ascii=False)};
const CLUSTERS = {json.dumps(to_records(clusters), ensure_ascii=False)};
const QUALITY = {json.dumps(to_records(quality), ensure_ascii=False)};
const YEARS = {json.dumps(years)};
const REGIONS = {json.dumps(regions)};
const EV_SCENARIOS = {json.dumps(ev_scenarios)};
const AI_SCENARIOS = {json.dumps(ai_scenarios)};
const CCUS_SCENARIOS = {json.dumps(ccus_scenarios)};
const colors = ['#2f6f73','#d98f45','#6f5a9c','#b94e48','#5c6b73','#3f7cac'];
const $ = id => document.getElementById(id);
const fmt = v => Number.isFinite(+v) ? (+v).toLocaleString(undefined, {{maximumFractionDigits:1}}) : '';
function fillSelect(id, values, all=false) {{
  const sel = $(id); sel.innerHTML = '';
  if (all) sel.add(new Option('All', 'All'));
  values.forEach(v => sel.add(new Option(v, v)));
}}
fillSelect('year', YEARS); $('year').value = YEARS.includes(2030) ? 2030 : YEARS[YEARS.length-1];
fillSelect('region', REGIONS, true);
fillSelect('evScenario', EV_SCENARIOS); if (EV_SCENARIOS.includes('STEPS')) $('evScenario').value = 'STEPS';
fillSelect('aiScenario', AI_SCENARIOS); if (AI_SCENARIOS.includes('Base Case')) $('aiScenario').value = 'Base Case';
fillSelect('ccusScenario', CCUS_SCENARIOS); if (CCUS_SCENARIOS.includes('all_announced')) $('ccusScenario').value = 'all_announced';
function tooltip(html, event) {{ const t=$('tooltip'); t.innerHTML=html; t.style.display='block'; t.style.left=(event.clientX+14)+'px'; t.style.top=(event.clientY+14)+'px'; }}
function hideTip() {{ $('tooltip').style.display='none'; }}
function filteredScenario() {{
  const y=+$('year').value, r=$('region').value, ev=$('evScenario').value, ai=$('aiScenario').value, ccus=$('ccusScenario').value;
  return SCENARIO_DATA.filter(d => +d.year===y && d.ev_scenario===ev && d.ai_scenario===ai && d.ccus_scenario===ccus && (r==='All' || d.common_region===r));
}}
function currentSelection() {{
  return {{year:+$('year').value, region:$('region').value, ev:$('evScenario').value, ai:$('aiScenario').value, ccus:$('ccusScenario').value}};
}}
function scenarioHasRows(sel) {{
  return SCENARIO_DATA.some(d => +d.year===+sel.year && d.ev_scenario===sel.ev && d.ai_scenario===sel.ai && d.ccus_scenario===sel.ccus && (sel.region==='All' || d.common_region===sel.region));
}}
function selectionWith(id, value) {{
  const sel = currentSelection();
  if (id === 'year') sel.year = +value;
  if (id === 'region') sel.region = value;
  if (id === 'evScenario') sel.ev = value;
  if (id === 'aiScenario') sel.ai = value;
  if (id === 'ccusScenario') sel.ccus = value;
  return sel;
}}
function updateOptionAvailability() {{
  ['year','region','evScenario','aiScenario','ccusScenario'].forEach(id => {{
    Array.from($(id).options).forEach(opt => {{
      const ok = scenarioHasRows(selectionWith(id, opt.value));
      opt.disabled = false;
      opt.style.color = ok ? '' : '#888';
      opt.title = ok ? '' : '当前组合下无数据，选择后将显示暂无数据';
    }});
  }});
}}
function noDataHtml() {{
  return '<div class="empty-state">该情景组合下无历史或预测数据（数据暂时缺失）</div>';
}}
function svg(w,h,inner) {{ return `<svg viewBox="0 0 ${{w}} ${{h}}" role="img">${{inner}}</svg>`; }}
function barChart(id, data, label, value, color, limit=12) {{
  data = [...data].filter(d => d[value] != null).sort((a,b)=>+b[value]-+a[value]).slice(0,limit);
  if (!data.length) {{ $(id).innerHTML = noDataHtml(); return; }}
  const w=680,h=390,l=190,t=24,bh=22,g=8,max=Math.max(1,...data.map(d=>+d[value]||0));
  let out = '';
  data.forEach((d,i)=>{{ const y=t+i*(bh+g), bw=(+d[value]||0)/max*(w-l-70);
    out += `<text x="${{l-8}}" y="${{y+15}}" text-anchor="end" font-size="12" fill="#333">${{String(d[label]).slice(0,24)}}</text>`;
    out += `<rect class="bar" x="${{l}}" y="${{y}}" width="${{bw}}" height="${{bh}}" rx="4" fill="${{color}}" onmousemove="tooltip('<b>${{d[label]}}</b><br>${{value}}: ${{fmt(d[value])}}', event)" onmouseleave="hideTip()"></rect>`;
    out += `<text x="${{l+bw+6}}" y="${{y+15}}" font-size="12" fill="#333">${{fmt(d[value])}}</text>`;
  }});
  $(id).innerHTML = svg(w,h,out);
}}
function stackedMix(id, data) {{
  data = [...data].sort((a,b)=>+b.combined_electricity_demand_twh-+a.combined_electricity_demand_twh).slice(0,12);
  if (!data.length) {{ $(id).innerHTML = noDataHtml(); return; }}
  const w=680,h=390,l=190,t=24,bh=22,g=8,max=Math.max(1,...data.map(d=>+d.combined_electricity_demand_twh||0));
  let out = `<rect x="480" y="0" width="12" height="12" fill="#2f6f73"/><text x="498" y="11" font-size="12">EV</text><rect x="540" y="0" width="12" height="12" fill="#d98f45"/><text x="558" y="11" font-size="12">AI</text>`;
  data.forEach((d,i)=>{{ const y=t+i*(bh+g), ev=(+d.ev_electricity_twh||0), ai=(+d.ai_electricity_twh||0), evw=ev/max*(w-l-70), aiw=ai/max*(w-l-70);
    out += `<text x="${{l-8}}" y="${{y+15}}" text-anchor="end" font-size="12" fill="#333">${{String(d.common_region).slice(0,24)}}</text>`;
    out += `<rect class="bar" x="${{l}}" y="${{y}}" width="${{evw}}" height="${{bh}}" rx="4" fill="#2f6f73" onmousemove="tooltip('<b>${{d.common_region}}</b><br>EV: ${{fmt(ev)}} TWh<br>AI: ${{fmt(ai)}} TWh', event)" onmouseleave="hideTip()"></rect>`;
    out += `<rect class="bar" x="${{l+evw}}" y="${{y}}" width="${{aiw}}" height="${{bh}}" fill="#d98f45" onmousemove="tooltip('<b>${{d.common_region}}</b><br>EV: ${{fmt(ev)}} TWh<br>AI: ${{fmt(ai)}} TWh', event)" onmouseleave="hideTip()"></rect>`;
  }});
  $(id).innerHTML = svg(w,h,out);
}}
function scatter(id, data, xKey, yKey) {{
  if (!data.length) {{ $(id).innerHTML = noDataHtml(); return; }}
  const w=680,h=390,l=64,t=24,pw=560,ph=310;
  const xs=data.map(d=>+d[xKey]||0), ys=data.map(d=>+d[yKey]||0);
  const xmax=Math.max(1,...xs)*1.1, ymax=Math.max(1,...ys)*1.1, xmin=Math.min(0,...xs), ymin=Math.min(0,...ys);
  let out = `<rect x="${{l}}" y="${{t}}" width="${{pw}}" height="${{ph}}" fill="#fbfbfb" stroke="#ddd"/>`;
  data.forEach((d,i)=>{{ const x=l+((+d[xKey]||0)-xmin)/(xmax-xmin)*pw, y=t+ph-((+d[yKey]||0)-ymin)/(ymax-ymin)*ph;
    out += `<circle class="point" cx="${{x}}" cy="${{y}}" r="8" fill="${{colors[i%colors.length]}}" opacity=".85" onmousemove="tooltip('<b>${{d.common_region}}</b><br>${{xKey}}: ${{fmt(d[xKey])}}<br>${{yKey}}: ${{fmt(d[yKey])}}', event)" onmouseleave="hideTip()"></circle>`;
  }});
  out += `<text x="${{l+pw/2}}" y="${{t+ph+36}}" text-anchor="middle" font-size="12">${{xKey.replaceAll('_',' ')}}</text><text x="18" y="${{t+ph/2}}" transform="rotate(-90 18 ${{t+ph/2}})" text-anchor="middle" font-size="12">${{yKey.replaceAll('_',' ')}}</text>`;
  $(id).innerHTML = svg(w,h,out);
}}
function table(id, data) {{
  if (!data.length) {{ $(id).innerHTML = noDataHtml(); return; }}
  const cols = ['common_region','year','ev_scenario','ai_scenario','ccus_scenario','combined_electricity_demand_twh','ccus_buffer_ratio','regional_pressure_score','pressure_class'].filter(c => data.some(d => c in d));
  const rows = data.slice().sort((a,b)=>(+b.regional_pressure_score||0)-(+a.regional_pressure_score||0)).map(d => `<tr>${{cols.map(c=>`<td>${{fmt(d[c]) || d[c] || ''}}</td>`).join('')}}</tr>`).join('');
  $(id).innerHTML = `<table><thead><tr>${{cols.map(c=>`<th>${{c}}</th>`).join('')}}</tr></thead><tbody>${{rows}}</tbody></table>`;
}}
function cards(data) {{
  if (!data.length) {{
    $('cards').innerHTML = '<div class="card empty-card"><span>当前筛选</span><strong>数据暂时缺失，请切换其他选项</strong></div>';
    return;
  }}
  const maxP = Math.max(0,...data.map(d=>+d.regional_pressure_score||0));
  const maxD = Math.max(0,...data.map(d=>+d.combined_electricity_demand_twh||0));
  const critical = data.filter(d=>d.pressure_class==='Critical Pressure').length;
  const qPass = QUALITY.filter(d=>d.status==='PASS').length;
  $('cards').innerHTML = [
    ['Rows', data.length],
    ['Max pressure', fmt(maxP)],
    ['Max demand TWh', fmt(maxD)],
    ['Quality PASS', qPass],
  ].map(([k,v])=>`<div class="card"><span>${{k}}</span><strong>${{v}}</strong></div>`).join('');
}}
function render() {{
  updateOptionAvailability();
  const s = filteredScenario();
  $('emptyNotice').style.display = s.length ? 'none' : 'block';
  cards(s);
  barChart('ranking', s, 'common_region', 'regional_pressure_score', '#b94e48');
  scatter('scatter', s, 'combined_electricity_demand_twh', 'regional_pressure_score');
  stackedMix('mix', s);
  barChart('buffer', s, 'common_region', 'ccus_buffer_ratio', '#6f5a9c');
  const imp = [...IMPORTANCE].sort((a,b)=>(+b.importance||0)-(+a.importance||0)).slice(0,12).map(d=>({{feature:(d.model+': '+d.feature).slice(0,36), importance:d.importance}}));
  barChart('importance', imp, 'feature', 'importance', '#2f6f73');
  scatter('cluster', CLUSTERS, CLUSTERS[0]?.pca_x!=null?'pca_x':'combined_electricity_demand_twh', CLUSTERS[0]?.pca_y!=null?'pca_y':'regional_pressure_score');
  table('table', s);
}}
['year','region','evScenario','aiScenario','ccusScenario'].forEach(id => $(id).addEventListener('change', render));
render();
</script>
</body>
</html>"""
    HTML_PATH.write_text(html, encoding="utf-8")


def main():
    ml = read_csv("ml_region_year_features.csv")
    scenario = read_csv("scenario_region_year_features.csv")
    importance = read_csv("model_feature_importance.csv")
    clusters = read_csv("region_clusters.csv")
    quality = read_csv("data_quality_report.csv")
    if ml.empty and scenario.empty:
        raise RuntimeError("No feature data found. Run the pipeline first.")
    clean_results()
    build_pngs(ml, scenario, importance, clusters)
    build_html(ml, scenario, importance, clusters, quality)
    print(f"Wrote {len(PNG_FILES)} PNG files to {RESULTS_DIR}")
    print(f"Wrote dashboard to {HTML_PATH}")


if __name__ == "__main__":
    main()
