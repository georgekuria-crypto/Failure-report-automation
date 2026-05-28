"""
Production Network Failure and MTTR Dashboard
Enterprise NOC Edition — Premium UI / Executive Presentation Layer

NOTE:
    - Backend analytics, filtering logic, caching, and chart
      computations are preserved from the original implementation.
    - This revision focuses on visual hierarchy, layout, theming,
      KPI presentation, sidebar UX, tab styling, and chart polish.
    - Continues to depend on `visualizations.py` and `constants.py`.
"""

from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from visualizations import (
    DISCRETE_COLORS,
    SEQUENTIAL_SCALE,
    format_bar_text,
    render_chart,
    style_figure,
)

from constants import OPTIONAL_COLUMNS, REQUIRED_COLUMNS  # noqa: F401


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Network Failure & MTTR — NOC Analytics",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DESIGN TOKENS (Telecom NOC palette)
# =========================================================

THEME = {
    "bg":           "#0B1020",
    "bg_soft":      "#111733",
    "surface":      "rgba(255,255,255,0.04)",
    "surface_2":    "rgba(255,255,255,0.06)",
    "border":       "rgba(148,163,184,0.18)",
    "text":         "#E6EDF7",
    "text_muted":   "#94A3B8",
    "navy":         "#0B1F4D",
    "electric":     "#3B82F6",
    "cyan":         "#22D3EE",
    "violet":       "#8B5CF6",
    "success":      "#22C55E",
    "amber":        "#F59E0B",
    "critical":     "#EF4444",
}

CHART_PALETTE = [
    THEME["electric"], THEME["cyan"], THEME["violet"],
    THEME["amber"], THEME["success"], THEME["critical"],
    "#F472B6", "#14B8A6", "#A78BFA", "#FB923C",
]


# =========================================================
# GLOBAL STYLING
# =========================================================

def inject_global_css() -> None:

    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

            html, body, [class*="css"] {{
                font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
                color: {THEME["text"]};
            }}

            .stApp {{
                background:
                    radial-gradient(1200px 600px at 10% -10%, rgba(59,130,246,0.18), transparent 60%),
                    radial-gradient(900px 500px at 110% 10%, rgba(139,92,246,0.15), transparent 55%),
                    linear-gradient(180deg, {THEME["bg"]} 0%, #070B1A 100%);
            }}

            .block-container {{
                padding-top: 1.2rem;
                padding-bottom: 3rem;
                max-width: 1500px;
            }}

            /* ---------- HERO HEADER ---------- */
            .noc-hero {{
                position: relative;
                padding: 28px 32px;
                border-radius: 20px;
                background: linear-gradient(135deg,
                    rgba(59,130,246,0.18) 0%,
                    rgba(34,211,238,0.10) 40%,
                    rgba(139,92,246,0.16) 100%);
                border: 1px solid {THEME["border"]};
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5);
                overflow: hidden;
                margin-bottom: 20px;
            }}
            .noc-hero::after {{
                content: "";
                position: absolute;
                inset: 0;
                background:
                    radial-gradient(400px 200px at 90% 0%, rgba(34,211,238,0.25), transparent 70%);
                pointer-events: none;
            }}
            .noc-hero-row {{
                display: flex; align-items: center; justify-content: space-between;
                gap: 24px; flex-wrap: wrap;
            }}
            .noc-title {{
                font-size: 1.85rem; font-weight: 800; letter-spacing: -0.02em;
                margin: 0; color: {THEME["text"]};
                display: flex; align-items: center; gap: 14px;
            }}
            .noc-subtitle {{
                color: {THEME["text_muted"]}; font-size: 0.98rem;
                margin-top: 6px;
            }}
            .noc-pulse {{
                width: 12px; height: 12px; border-radius: 50%;
                background: {THEME["success"]};
                box-shadow: 0 0 0 0 rgba(34,197,94,0.7);
                animation: pulse 2s infinite;
                display: inline-block;
            }}
            @keyframes pulse {{
                0%   {{ box-shadow: 0 0 0 0 rgba(34,197,94,0.6); }}
                70%  {{ box-shadow: 0 0 0 14px rgba(34,197,94,0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(34,197,94,0); }}
            }}
            .noc-status {{
                display: inline-flex; align-items: center; gap: 10px;
                padding: 8px 14px; border-radius: 999px;
                background: rgba(34,197,94,0.12);
                border: 1px solid rgba(34,197,94,0.35);
                color: {THEME["success"]};
                font-weight: 600; font-size: 0.85rem; letter-spacing: 0.02em;
                text-transform: uppercase;
            }}
            .noc-meta {{
                display: flex; gap: 18px; flex-wrap: wrap;
                color: {THEME["text_muted"]}; font-size: 0.85rem;
                margin-top: 14px;
            }}
            .noc-meta span b {{ color: {THEME["text"]}; font-weight: 600; }}

            /* ---------- KPI CARDS ---------- */
            div[data-testid="stMetric"] {{
                background: {THEME["surface"]};
                border: 1px solid {THEME["border"]};
                border-radius: 16px;
                padding: 18px 20px;
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                transition: transform .15s ease, border-color .15s ease, box-shadow .2s ease;
                box-shadow: 0 4px 18px -8px rgba(0,0,0,0.5);
            }}
            div[data-testid="stMetric"]:hover {{
                transform: translateY(-2px);
                border-color: rgba(59,130,246,0.45);
                box-shadow: 0 10px 30px -12px rgba(59,130,246,0.45);
            }}
            div[data-testid="stMetricLabel"] p {{
                color: {THEME["text_muted"]} !important;
                font-size: 0.78rem !important;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-weight: 600 !important;
            }}
            div[data-testid="stMetricValue"] {{
                font-family: 'JetBrains Mono', monospace !important;
                font-weight: 700 !important;
                font-size: 1.7rem !important;
                color: {THEME["text"]} !important;
            }}

            /* ---------- EXECUTIVE SUMMARY ---------- */
            .exec-summary {{
                margin: 18px 0 8px;
                padding: 18px 22px;
                border-radius: 16px;
                background: linear-gradient(135deg,
                    rgba(139,92,246,0.10), rgba(59,130,246,0.10));
                border: 1px solid {THEME["border"]};
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px,1fr));
                gap: 16px;
            }}
            .exec-item {{ display: flex; flex-direction: column; gap: 4px; }}
            .exec-label {{
                font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase;
                color: {THEME["text_muted"]}; font-weight: 600;
            }}
            .exec-value {{
                font-size: 1.05rem; font-weight: 700; color: {THEME["text"]};
                font-family: 'JetBrains Mono', monospace;
            }}

            /* ---------- SECTION CARDS / CHART CONTAINERS ---------- */
            .section-title {{
                font-size: 1.05rem; font-weight: 700; color: {THEME["text"]};
                margin: 14px 0 10px;
                display: flex; align-items: center; gap: 10px;
            }}
            .section-title .dot {{
                width: 6px; height: 6px; border-radius: 50%;
                background: {THEME["cyan"]};
                box-shadow: 0 0 12px {THEME["cyan"]};
            }}

            /* ---------- TABS ---------- */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 6px;
                background: {THEME["surface"]};
                padding: 6px;
                border-radius: 14px;
                border: 1px solid {THEME["border"]};
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 42px;
                background: transparent;
                border-radius: 10px;
                color: {THEME["text_muted"]};
                font-weight: 600;
                padding: 0 18px;
                transition: all .15s ease;
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                color: {THEME["text"]};
                background: rgba(255,255,255,0.04);
            }}
            .stTabs [aria-selected="true"] {{
                background: linear-gradient(135deg, {THEME["electric"]}, {THEME["violet"]}) !important;
                color: #fff !important;
                box-shadow: 0 6px 20px -8px {THEME["electric"]};
            }}

            /* ---------- SIDEBAR ---------- */
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #0A1230 0%, #070B1F 100%);
                border-right: 1px solid {THEME["border"]};
            }}
            [data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
            .sb-brand {{
                display: flex; align-items: center; gap: 12px;
                padding: 14px 8px 10px;
                border-bottom: 1px solid {THEME["border"]};
                margin-bottom: 14px;
            }}
            .sb-brand-icon {{
                width: 38px; height: 38px; border-radius: 10px;
                background: linear-gradient(135deg, {THEME["electric"]}, {THEME["violet"]});
                display: flex; align-items: center; justify-content: center;
                font-size: 20px;
                box-shadow: 0 6px 20px -6px {THEME["electric"]};
            }}
            .sb-brand-text b {{ color: {THEME["text"]}; font-size: 0.95rem; }}
            .sb-brand-text span {{ color: {THEME["text_muted"]}; font-size: 0.75rem; display:block; }}
            .sb-section {{
                font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase;
                color: {THEME["text_muted"]}; font-weight: 700;
                margin: 14px 4px 6px;
            }}
            .sb-chips {{
                display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 10px;
            }}
            .sb-chip {{
                font-size: 0.72rem; padding: 4px 10px; border-radius: 999px;
                background: rgba(59,130,246,0.14);
                color: {THEME["cyan"]};
                border: 1px solid rgba(59,130,246,0.3);
                font-weight: 600;
            }}

            /* ---------- DATAFRAME ---------- */
            [data-testid="stDataFrame"] {{
                border-radius: 14px; overflow: hidden;
                border: 1px solid {THEME["border"]};
            }}

            /* ---------- BUTTONS / DOWNLOAD ---------- */
            .stDownloadButton button, .stButton button {{
                background: linear-gradient(135deg, {THEME["electric"]}, {THEME["violet"]}) !important;
                color: #fff !important;
                border: none !important;
                border-radius: 10px !important;
                font-weight: 600 !important;
                padding: 10px 18px !important;
                box-shadow: 0 8px 22px -10px {THEME["electric"]};
                transition: transform .12s ease, box-shadow .2s ease;
            }}
            .stDownloadButton button:hover, .stButton button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 12px 26px -10px {THEME["violet"]};
            }}

            /* ---------- DIVIDERS / MISC ---------- */
            hr {{ border-color: {THEME["border"]} !important; }}
            .section-note {{
                font-size: 0.9rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PLOTLY THEME OVERRIDES (layered on top of style_figure)
# =========================================================

def polish_figure(fig: go.Figure, *, height: int | None = None) -> go.Figure:

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, system-ui, sans-serif",
            color=THEME["text"],
            size=13,
        ),
        title=dict(
            font=dict(size=16, color=THEME["text"], family="Inter"),
            x=0.01, xanchor="left", y=0.97,
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            bgcolor="rgba(255,255,255,0.03)",
            bordercolor=THEME["border"],
            borderwidth=1,
            font=dict(color=THEME["text"], size=12),
        ),
        hoverlabel=dict(
            bgcolor=THEME["bg_soft"],
            bordercolor=THEME["electric"],
            font=dict(color=THEME["text"], family="Inter", size=12),
        ),
    )

    fig.update_xaxes(
        gridcolor="rgba(148,163,184,0.10)",
        zerolinecolor="rgba(148,163,184,0.15)",
        tickfont=dict(color=THEME["text_muted"]),
        title_font=dict(color=THEME["text_muted"], size=12),
    )
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.10)",
        zerolinecolor="rgba(148,163,184,0.15)",
        tickfont=dict(color=THEME["text_muted"]),
        title_font=dict(color=THEME["text_muted"], size=12),
    )

    # Smooth lines + nicer markers
    for trace in fig.data:
        if trace.type == "scatter" and getattr(trace, "mode", "") and "lines" in trace.mode:
            trace.line.shape = "spline"
            trace.line.smoothing = 0.8
            trace.line.width = 3
            if trace.marker:
                trace.marker.size = 7
                trace.marker.line = dict(width=1.5, color="rgba(255,255,255,0.85)")

        # Rounded bars (Plotly approximation via corner radius where supported)
        if trace.type == "bar":
            trace.marker.line = dict(width=0)
            try:
                trace.marker.cornerradius = 6
            except Exception:
                pass

    if height:
        fig.update_layout(height=height)

    return fig


# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data(show_spinner=False)
def load_data(file):

    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = df.columns.astype(str).str.strip()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

    numeric_columns = ["MTTR (Hours)", "Total Monthly Hrs"]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in df.select_dtypes(include="object").columns:
        df[col] = (
            df[col].astype(str).str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})
        )

    return df


# =========================================================
# VALIDATION
# =========================================================

def validate_columns(df):

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        st.stop()


# =========================================================
# FILTERS
# =========================================================

def multiselect_filter(label, column, data, key=None):

    options = sorted(data[column].dropna().unique())

    return st.sidebar.multiselect(
        label,
        options=options,
        default=options,
        key=key,
    )


def apply_filters(df):

    # Branded sidebar header
    st.sidebar.markdown(
        """
        <div class="sb-brand">
            <div class="sb-brand-icon">📡</div>
            <div class="sb-brand-text">
                <b>NOC Analytics</b>
                <span>Network Operations Control</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Reset filters
    if st.sidebar.button("↻  Reset All Filters", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith("flt_"):
                del st.session_state[k]
        st.rerun()

    # --- Time Window ---
    st.sidebar.markdown('<div class="sb-section">🕒 Time Window</div>', unsafe_allow_html=True)

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="flt_date",
    )

    if len(date_range) != 2:
        st.warning("Please select a valid start and end date.")
        st.stop()

    start_date, end_date = date_range

    # --- Network Scope ---
    st.sidebar.markdown('<div class="sb-section">🌐 Network Scope</div>', unsafe_allow_html=True)

    with st.sidebar.expander("Region & Site", expanded=True):
        selected_regions      = multiselect_filter("Region", "REGION", df, key="flt_region")
        selected_site_types   = multiselect_filter("Site Type", "SITE TYPE", df, key="flt_stype")
        selected_classes      = multiselect_filter("Site Classification", "Site Classification", df, key="flt_class")
        selected_visibility   = multiselect_filter("Visibility", "Visibility", df, key="flt_vis")

    # --- Failure Profile ---
    st.sidebar.markdown('<div class="sb-section">⚠️ Failure Profile</div>', unsafe_allow_html=True)

    with st.sidebar.expander("Bucket & MTTR", expanded=True):
        selected_buckets = multiselect_filter("Failure Bucket", "Bucket", df, key="flt_bucket")

        mttr_min = float(df["MTTR (Hours)"].min())
        mttr_max = float(df["MTTR (Hours)"].max())

        mttr_range = st.slider(
            "MTTR Range (Hours)",
            min_value=mttr_min,
            max_value=mttr_max,
            value=(mttr_min, mttr_max),
            key="flt_mttr",
        )

    # Apply
    filtered_df = df[
        (df["Date"].dt.date >= start_date)
        & (df["Date"].dt.date <= end_date)
        & (df["REGION"].isin(selected_regions))
        & (df["SITE TYPE"].isin(selected_site_types))
        & (df["Site Classification"].isin(selected_classes))
        & (df["Visibility"].isin(selected_visibility))
        & (df["Bucket"].isin(selected_buckets))
        & (df["MTTR (Hours)"] >= mttr_range[0])
        & (df["MTTR (Hours)"] <= mttr_range[1])
    ].copy()

    # Active filter chips
    chips = []
    if len(selected_regions) < df["REGION"].nunique():
        chips.append(f"{len(selected_regions)} regions")
    if len(selected_buckets) < df["Bucket"].nunique():
        chips.append(f"{len(selected_buckets)} buckets")
    if mttr_range != (mttr_min, mttr_max):
        chips.append(f"MTTR {mttr_range[0]:.1f}–{mttr_range[1]:.1f}h")
    if chips:
        st.sidebar.markdown('<div class="sb-section">Active Filters</div>', unsafe_allow_html=True)
        st.sidebar.markdown(
            '<div class="sb-chips">' +
            "".join(f'<span class="sb-chip">{c}</span>' for c in chips) +
            '</div>',
            unsafe_allow_html=True,
        )

    return filtered_df


# =========================================================
# HEADER
# =========================================================

def render_hero(filtered_df: pd.DataFrame | None = None) -> None:

    now = datetime.now().strftime("%b %d, %Y · %H:%M")

    records = f"{len(filtered_df):,}" if filtered_df is not None else "—"
    regions = filtered_df["REGION"].nunique() if filtered_df is not None else "—"
    sites   = filtered_df["Site Name"].nunique() if filtered_df is not None else "—"

    st.markdown(
        f"""
        <div class="noc-hero">
            <div class="noc-hero-row">
                <div>
                    <h1 class="noc-title">📡 Network Failure & MTTR Intelligence</h1>
                    <div class="noc-subtitle">
                        Executive operations intelligence for telecom NOC teams,
                        regional managers, and leadership.
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="noc-status">
                        <span class="noc-pulse"></span> All Systems Operational
                    </div>
                    <div style="color:{THEME['text_muted']}; font-size:0.8rem; margin-top:8px;">
                        Last refreshed · <b style="color:{THEME['text']};">{now}</b>
                    </div>
                </div>
            </div>
            <div class="noc-meta">
                <span>📊 Records: <b>{records}</b></span>
                <span>🌍 Regions: <b>{regions}</b></span>
                <span>🗼 Sites: <b>{sites}</b></span>
                <span>🟢 Data Source: <b>Live Upload</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# KPI SECTION
# =========================================================

def render_kpis(df):

    total_failures   = len(df)
    total_mttr       = df["MTTR (Hours)"].sum()
    avg_mttr         = df["MTTR (Hours)"].mean()
    affected_sites   = df["Site Name"].nunique()
    critical_count   = int((df["MTTR (Hours)"] > avg_mttr).sum())

    # MTTR risk classification
    if avg_mttr < 4:
        risk_label, risk_delta = "Healthy", "▲ Stable"
    elif avg_mttr < 12:
        risk_label, risk_delta = "Elevated", "▲ Watch"
    else:
        risk_label, risk_delta = "Critical", "▼ Action"

    critical_share = (critical_count / total_failures * 100) if total_failures else 0

    cols = st.columns(5)

    cols[0].metric("⚡ Total Failures",  f"{total_failures:,}",     delta=f"{affected_sites} sites impacted")
    cols[1].metric("⏱ Total MTTR",      f"{total_mttr:,.1f} hrs",  delta=f"avg {avg_mttr:,.2f} h/incident")
    cols[2].metric("📈 Average MTTR",   f"{avg_mttr:,.2f} hrs",    delta=risk_delta, delta_color="inverse")
    cols[3].metric("🗼 Affected Sites", f"{affected_sites:,}",     delta=f"of total network")
    cols[4].metric("🚨 Critical Cases", f"{critical_count:,}",     delta=f"{critical_share:.1f}% of total", delta_color="inverse")


# =========================================================
# EXECUTIVE SUMMARY
# =========================================================

def render_executive_summary(df):

    worst_region = df.groupby("REGION")["MTTR (Hours)"].sum().idxmax()
    worst_bucket = df.groupby("Bucket")["MTTR (Hours)"].sum().idxmax()
    worst_site   = df.groupby("Site Name")["MTTR (Hours)"].sum().idxmax()
    peak_day     = df.groupby(df["Date"].dt.date)["MTTR (Hours)"].sum().idxmax()

    st.markdown(
        f"""
        <div class="exec-summary">
            <div class="exec-item">
                <div class="exec-label">🌍 Highest-MTTR Region</div>
                <div class="exec-value">{worst_region}</div>
            </div>
            <div class="exec-item">
                <div class="exec-label">📦 Largest Failure Bucket</div>
                <div class="exec-value">{worst_bucket}</div>
            </div>
            <div class="exec-item">
                <div class="exec-label">🗼 Worst-Performing Site</div>
                <div class="exec-value">{worst_site}</div>
            </div>
            <div class="exec-item">
                <div class="exec-label">📅 Peak Outage Day</div>
                <div class="exec-value">{peak_day}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# AGGREGATION
# =========================================================

def aggregate_sum(df, group_column, value_column="MTTR (Hours)", top_n=None):

    data = (
        df.groupby(group_column)[value_column]
        .sum().reset_index()
        .sort_values(value_column, ascending=False)
    )

    if top_n:
        data = data.head(top_n)

    return data


# =========================================================
# CHARTS  (logic preserved; visuals upgraded)
# =========================================================

def chart_mttr_by_bucket(df):
    data = aggregate_sum(df, "Bucket")
    fig = px.bar(
        data, x="Bucket", y="MTTR (Hours)", color="Bucket",
        text="MTTR (Hours)",
        color_discrete_sequence=CHART_PALETTE,
        title="Total MTTR by Failure Bucket",
    )
    fig.update_layout(showlegend=False)
    return polish_figure(format_bar_text(style_figure(fig)))


def chart_daily_failures(df):
    data = df.groupby(df["Date"].dt.date).size().reset_index(name="Failure Count")
    data["Date"] = pd.to_datetime(data["Date"])
    fig = px.area(
        data, x="Date", y="Failure Count",
        title="Daily Failure Count",
        color_discrete_sequence=[THEME["cyan"]],
    )
    fig.update_traces(
        fill="tozeroy", line=dict(width=3, color=THEME["cyan"]),
        fillcolor="rgba(34,211,238,0.18)",
    )
    return polish_figure(style_figure(fig))


def chart_daily_mttr(df):
    data = df.groupby(df["Date"].dt.date)["MTTR (Hours)"].sum().reset_index()
    data["Date"] = pd.to_datetime(data["Date"])
    fig = px.line(
        data, x="Date", y="MTTR (Hours)", markers=True,
        title="Daily MTTR Trend",
        color_discrete_sequence=[THEME["electric"]],
    )
    return polish_figure(style_figure(fig))


def chart_daily_activity(df):
    data = (
        df.groupby(df["Date"].dt.date)
        .agg({"MTTR (Hours)": "sum", "Site Name": "count"})
        .reset_index().rename(columns={"Site Name": "Failure Count"})
    )
    data["Date"] = pd.to_datetime(data["Date"])

    fig = go.Figure()
    fig.add_bar(
        x=data["Date"], y=data["Failure Count"], name="Failures",
        marker=dict(color=THEME["violet"], opacity=0.85),
    )
    fig.add_scatter(
        x=data["Date"], y=data["MTTR (Hours)"], name="MTTR (hrs)",
        yaxis="y2", mode="lines+markers",
        line=dict(color=THEME["cyan"], width=3, shape="spline"),
        marker=dict(size=7, color=THEME["cyan"]),
    )
    fig.update_layout(
        title="Daily Failures vs MTTR",
        yaxis=dict(title="Failures"),
        yaxis2=dict(title="MTTR (Hours)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return polish_figure(style_figure(fig))


def chart_region_mttr(df):
    data = aggregate_sum(df, "REGION")
    fig = px.bar(
        data, x="REGION", y="MTTR (Hours)", color="REGION",
        text="MTTR (Hours)",
        color_discrete_sequence=CHART_PALETTE,
        title="Regional MTTR Distribution",
    )
    fig.update_layout(showlegend=False)
    return polish_figure(format_bar_text(style_figure(fig)))


def chart_region_heatmap(df):
    data = df.pivot_table(
        index="REGION", columns="Bucket", values="MTTR (Hours)",
        aggfunc="sum", fill_value=0,
    )
    fig = px.imshow(
        data, color_continuous_scale=SEQUENTIAL_SCALE,
        text_auto=".1f", aspect="auto",
        title="Regional × Failure-Bucket Heatmap",
    )
    fig.update_layout(coloraxis_colorbar=dict(title="MTTR", thickness=12))
    return polish_figure(style_figure(fig))


def chart_site_mttr(df, top_n=15):
    data = aggregate_sum(df, "Site Name", top_n=top_n)
    fig = px.bar(
        data, x="MTTR (Hours)", y="Site Name", orientation="h",
        color="MTTR (Hours)", text="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=f"Top {top_n} Sites — Total MTTR",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    return polish_figure(format_bar_text(style_figure(fig, height=600)))


def chart_site_failures(df, top_n=15):
    data = (
        df.groupby("Site Name").size().reset_index(name="Failure Count")
        .sort_values("Failure Count", ascending=False).head(top_n)
    )
    fig = px.bar(
        data, x="Failure Count", y="Site Name", orientation="h",
        color="Failure Count", text="Failure Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=f"Top {top_n} Sites — Failure Frequency",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    return polish_figure(style_figure(fig, height=600))


# =========================================================
# EXCEL EXPORT
# =========================================================

def generate_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Filtered Data")
    return output.getvalue()


def section_title(label: str) -> None:
    st.markdown(
        f'<div class="section-title"><span class="dot"></span>{label}</div>',
        unsafe_allow_html=True,
    )


# =========================================================
# MAIN APP
# =========================================================

def main():

    inject_global_css()

    # Sidebar uploader (kept here for consistent layout)
    st.sidebar.markdown(
        """
        <div class="sb-brand">
            <div class="sb-brand-icon">📡</div>
            <div class="sb-brand-text">
                <b>NOC Analytics</b>
                <span>Network Operations Control</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="sb-section">📤 Data Source</div>', unsafe_allow_html=True)

    uploaded_file = st.sidebar.file_uploader(
        "Upload Failure Report",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is None:
        render_hero(None)
        st.info(
            "📥  Upload a failure report (CSV / Excel) from the sidebar to "
            "begin executive analysis."
        )
        return

    with st.spinner("Loading and validating telecom dataset…"):
        df = load_data(uploaded_file)
        validate_columns(df)

    if df.empty:
        render_hero(None)
        st.warning("No valid data found in the uploaded file.")
        return

    # The branded sidebar header was already rendered above; re-using the
    # branded block inside apply_filters would duplicate it, so we re-inject
    # only the filter controls below by skipping the brand block there.
    filtered_df = _apply_filters_no_brand(df)

    if filtered_df.empty:
        render_hero(None)
        st.warning("No data matches the current filters. Try expanding selections.")
        return

    # Hero + KPIs + Exec Summary
    render_hero(filtered_df)
    render_kpis(filtered_df)
    render_executive_summary(filtered_df)

    # Tabs
    overview_tab, regional_tab, site_tab, export_tab = st.tabs(
        ["📊  Overview", "🌍  Regional Analysis", "🗼  Site Performance", "📁  Data Export"]
    )

    with overview_tab:
        section_title("Failure Composition & Daily Volume")
        col1, col2 = st.columns(2)
        with col1: render_chart(chart_mttr_by_bucket(filtered_df))
        with col2: render_chart(chart_daily_failures(filtered_df))

        section_title("Operational Timeline")
        render_chart(chart_daily_activity(filtered_df))
        render_chart(chart_daily_mttr(filtered_df))

    with regional_tab:
        section_title("Regional Health Overview")
        col1, col2 = st.columns(2)
        with col1: render_chart(chart_region_mttr(filtered_df))
        with col2: render_chart(chart_region_heatmap(filtered_df))

    with site_tab:
        section_title("Site Performance Drilldown")
        top_n = st.slider("Sites to Display", min_value=5, max_value=50, value=15)
        col1, col2 = st.columns(2)
        with col1: render_chart(chart_site_mttr(filtered_df, top_n))
        with col2: render_chart(chart_site_failures(filtered_df, top_n))

    with export_tab:
        section_title("Filtered Dataset Preview")
        st.caption(f"Showing first 1,000 of {len(filtered_df):,} filtered records.")
        st.dataframe(filtered_df.head(1000), use_container_width=True, hide_index=True)

        st.markdown("####  ")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            excel_data = generate_excel(filtered_df)
            st.download_button(
                label="⬇  Download Excel Report",
                data=excel_data,
                file_name="network_failure_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c2:
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇  Download CSV",
                data=csv_data,
                file_name="network_failure_analysis.csv",
                mime="text/csv",
                use_container_width=True,
            )


# Internal wrapper: same as apply_filters but skips the duplicate brand header
def _apply_filters_no_brand(df):
    # Re-uses the original sidebar controls; brand block was already rendered.
    if st.sidebar.button("↻  Reset All Filters", use_container_width=True, key="reset_btn"):
        for k in list(st.session_state.keys()):
            if k.startswith("flt_"):
                del st.session_state[k]
        st.rerun()

    st.sidebar.markdown('<div class="sb-section">🕒 Time Window</div>', unsafe_allow_html=True)

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date, max_value=max_date,
        key="flt_date",
    )
    if len(date_range) != 2:
        st.warning("Please select a valid start and end date.")
        st.stop()
    start_date, end_date = date_range

    st.sidebar.markdown('<div class="sb-section">🌐 Network Scope</div>', unsafe_allow_html=True)
    with st.sidebar.expander("Region & Site", expanded=True):
        selected_regions    = multiselect_filter("Region", "REGION", df, key="flt_region")
        selected_site_types = multiselect_filter("Site Type", "SITE TYPE", df, key="flt_stype")
        selected_classes    = multiselect_filter("Site Classification", "Site Classification", df, key="flt_class")
        selected_visibility = multiselect_filter("Visibility", "Visibility", df, key="flt_vis")

    st.sidebar.markdown('<div class="sb-section">⚠️ Failure Profile</div>', unsafe_allow_html=True)
    with st.sidebar.expander("Bucket & MTTR", expanded=True):
        selected_buckets = multiselect_filter("Failure Bucket", "Bucket", df, key="flt_bucket")
        mttr_min = float(df["MTTR (Hours)"].min())
        mttr_max = float(df["MTTR (Hours)"].max())
        mttr_range = st.slider(
            "MTTR Range (Hours)",
            min_value=mttr_min, max_value=mttr_max,
            value=(mttr_min, mttr_max), key="flt_mttr",
        )

    filtered_df = df[
        (df["Date"].dt.date >= start_date)
        & (df["Date"].dt.date <= end_date)
        & (df["REGION"].isin(selected_regions))
        & (df["SITE TYPE"].isin(selected_site_types))
        & (df["Site Classification"].isin(selected_classes))
        & (df["Visibility"].isin(selected_visibility))
        & (df["Bucket"].isin(selected_buckets))
        & (df["MTTR (Hours)"] >= mttr_range[0])
        & (df["MTTR (Hours)"] <= mttr_range[1])
    ].copy()

    chips = []
    if len(selected_regions) < df["REGION"].nunique():
        chips.append(f"{len(selected_regions)} regions")
    if len(selected_buckets) < df["Bucket"].nunique():
        chips.append(f"{len(selected_buckets)} buckets")
    if mttr_range != (mttr_min, mttr_max):
        chips.append(f"MTTR {mttr_range[0]:.1f}–{mttr_range[1]:.1f}h")
    if chips:
        st.sidebar.markdown('<div class="sb-section">Active Filters</div>', unsafe_allow_html=True)
        st.sidebar.markdown(
            '<div class="sb-chips">' +
            "".join(f'<span class="sb-chip">{c}</span>' for c in chips) +
            '</div>',
            unsafe_allow_html=True,
        )

    st.sidebar.divider()
    st.sidebar.metric("Filtered Records", f"{len(filtered_df):,}")
    st.sidebar.metric("Regions",          filtered_df["REGION"].nunique())
    st.sidebar.metric("Sites",            filtered_df["Site Name"].nunique())

    return filtered_df


if __name__ == "__main__":
    main()
