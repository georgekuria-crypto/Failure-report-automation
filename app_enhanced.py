"""
EXPERIMENTAL: Enhanced Network Failure and MTTR Dashboard with Advanced Analytics

NOTE: This is an experimental version of the dashboard with additional analytics features
including anomaly detection, SLA tracking, forecasting, and team performance metrics.
It is not currently part of the main production workflow.

The main production app is in app.py. Use this file as a reference for future feature
development, but do NOT use it for deployment.

To use this version:
1. Ensure all dependencies from requirements.txt are installed
2. Run: streamlit run app_enhanced.py

Features in this version not in production app.py:
- Advanced anomaly detection for MTTR outliers
- SLA compliance tracking and breach alerts
- MTTR trend forecasting
- Team/engineer performance metrics
- Kenya regional mapping (requires folium)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Import custom modules
from utils import (
    format_number, format_duration, calculate_percentile,
    detect_outliers_iqr, add_time_features, normalize_columns
)
from analytics import (
    AnomalyDetector, SLATracker, MTTRPredictor, PerformanceMetrics,
    get_outage_heatmap_data, get_failure_distribution_by_time
)
from visualizations import (
    is_dark_theme, chart_template, chart_text_color, chart_grid_color,
    style_figure, format_bar_text, render_chart, create_kpi_gauge,
    create_anomaly_chart, create_outage_hour_heatmap, create_kenya_map,
    create_sla_breach_chart, create_mttr_trend_forecast, create_team_performance_chart,
    CHART_CONFIG, SEQUENTIAL_SCALE, DISCRETE_COLORS
)

# Page configuration
st.set_page_config(
    page_title="Network Failure Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced CSS styling
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        [data-testid="stMetric"] {
            background: color-mix(in srgb, var(--background-color) 88%, var(--text-color) 12%);
            border: 1px solid color-mix(in srgb, var(--background-color) 70%, var(--text-color) 30%);
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 2px 4px rgba(15, 23, 42, 0.08);
            transition: all 0.3s ease;
        }
        [data-testid="stMetric"]:hover {
            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.12);
        }
        [data-testid="stSidebar"] {
            background: color-mix(in srgb, var(--background-color) 94%, var(--text-color) 6%);
        }
        .section-note {
            color: var(--text-color);
            font-size: 0.95rem;
            margin-top: -0.35rem;
            margin-bottom: 1.2rem;
            opacity: 0.74;
            line-height: 1.4;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .status-ok {
            background-color: rgba(16, 185, 129, 0.1);
            color: #10b981;
            border: 1px solid #10b981;
        }
        .status-warning {
            background-color: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
            border: 1px solid #f59e0b;
        }
        .status-critical {
            background-color: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid #ef4444;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants
REQUIRED_COLUMNS = [
    "Date", "REGION", "SITE TYPE", "Site Classification",
    "Visibility", "Bucket", "MTTR (Hours)", "Site Name",
]

OPTIONAL_COLUMNS = [
    "Total Monthly Hrs", "Source of Power", "Status",
]

# SLA Thresholds (hours)
SLA_THRESHOLD_CRITICAL = 4.0
SLA_THRESHOLD_MAJOR = 12.0
SLA_THRESHOLD_MINOR = 48.0


# ============================================================================
# DATA LOADING & VALIDATION
# ============================================================================

@st.cache_data(show_spinner=False)
def load_data(file):
    """Load and clean data from Excel or CSV file."""
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = df.columns.astype(str).str.strip()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

    for column in ["MTTR (Hours)", "Total Monthly Hrs"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].astype(str).str.strip()
        df[column] = df[column].replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})

    return df


def validate_columns(df):
    """Validate required columns exist."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(f'`{col}`' for col in missing)}")
        st.stop()


def multiselect_filter(label: str, column: str, data: pd.DataFrame):
    """Create multiselect filter for sidebar."""
    options = sorted(data[column].dropna().unique())
    return st.sidebar.multiselect(label, options=options, default=options)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all filters from sidebar."""
    st.sidebar.header("Filters & Settings")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    date_range = st.sidebar.date_input(
        "📅 Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) != 2:
        st.warning("Select both start and end dates.")
        st.stop()

    start_date, end_date = date_range
    if start_date > end_date:
        st.warning("Start date must be before end date.")
        st.stop()

    selected_regions = multiselect_filter("🌍 Region", "REGION", df)
    selected_site_types = multiselect_filter("📍 Site type", "SITE TYPE", df)
    selected_classes = multiselect_filter("🏷️ Site classification", "Site Classification", df)
    selected_visibility = multiselect_filter("👁️ Visibility", "Visibility", df)
    selected_buckets = multiselect_filter("⚡ Failure bucket", "Bucket", df)

    mttr_min = float(df["MTTR (Hours)"].min())
    mttr_max = float(df["MTTR (Hours)"].max())
    if mttr_min == mttr_max:
        st.sidebar.caption(f"MTTR range fixed at {mttr_min:.2f} hours.")
        mttr_range = (mttr_min, mttr_max)
    else:
        mttr_range = st.sidebar.slider(
            "⏱️ MTTR range (hours)",
            min_value=mttr_min,
            max_value=mttr_max,
            value=(mttr_min, mttr_max),
        )

    mask = (
        (df["Date"].dt.date >= start_date) &
        (df["Date"].dt.date <= end_date) &
        (df["REGION"].isin(selected_regions)) &
        (df["SITE TYPE"].isin(selected_site_types)) &
        (df["Site Classification"].isin(selected_classes)) &
        (df["Visibility"].isin(selected_visibility)) &
        (df["Bucket"].isin(selected_buckets)) &
        (df["MTTR (Hours)"] >= mttr_range[0]) &
        (df["MTTR (Hours)"] <= mttr_range[1])
    )
    return df.loc[mask].copy()


# ============================================================================
# KPI CALCULATIONS
# ============================================================================

def aggregate_sum(df: pd.DataFrame, group_column: str, value_column: str = "MTTR (Hours)", top_n: int = None):
    """Aggregate sum by group column."""
    result = (
        df.groupby(group_column, dropna=False)[value_column]
        .sum()
        .reset_index()
        .sort_values(value_column, ascending=False)
    )
    if top_n:
        result = result.head(top_n)
    return result


def render_kpis(df: pd.DataFrame):
    """Render main KPI metrics."""
    total_failures = len(df)
    total_mttr = df["MTTR (Hours)"].sum()
    avg_mttr = df["MTTR (Hours)"].mean()
    affected_sites = df["Site Name"].nunique()
    p95_mttr = calculate_percentile(df["MTTR (Hours)"], 95)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "📊 Total Failures",
            f"{total_failures:,}",
            help="Total number of failure records"
        )

    with col2:
        st.metric(
            "⏱️ Total MTTR",
            f"{format_number(total_mttr)}h",
            help="Combined MTTR across all failures"
        )

    with col3:
        st.metric(
            "📈 Average MTTR",
            f"{format_number(avg_mttr)}h",
            help="Mean time to recovery"
        )

    with col4:
        st.metric(
            "🌐 Affected Sites",
            f"{affected_sites:,}",
            help="Unique sites with failures"
        )

    with col5:
        st.metric(
            "📊 P95 MTTR",
            f"{format_number(p95_mttr)}h",
            help="95th percentile MTTR"
        )


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def chart_mttr_by_bucket(df: pd.DataFrame):
    """MTTR by failure bucket with enhanced styling."""
    data = aggregate_sum(df, "Bucket")
    data["Failures"] = data["Bucket"].map(df["Bucket"].value_counts())

    fig = px.bar(
        data,
        x="Bucket",
        y="MTTR (Hours)",
        color="Bucket",
        color_discrete_sequence=DISCRETE_COLORS,
        text="MTTR (Hours)",
        title="Total MTTR by Failure Bucket",
        hover_data={"Failures": ":,", "MTTR (Hours)": ":,.2f", "Bucket": False},
    )

    fig.update_layout(
        xaxis_title="Failure Bucket",
        yaxis_title="MTTR (Hours)",
        showlegend=False,
        height=480,
        margin=dict(l=75, r=35, t=100, b=80)
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<br>Failures: %{customdata[0]:,}<extra></extra>"
    )

    return format_bar_text(style_figure(fig, height=480))


def chart_daily_failures(df: pd.DataFrame):
    """Daily failure count trend."""
    data = df.groupby(df["Date"].dt.date).size().reset_index(name="Failure Count")
    data["Date"] = pd.to_datetime(data["Date"])

    fig = px.line(
        data,
        x="Date",
        y="Failure Count",
        markers=True,
        title="Daily Failure Count Trend",
    )

    fig.update_traces(
        line=dict(width=3, color="#6366f1"),
        marker=dict(size=8, color="#4f46e5"),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Failures: %{y:,}<extra></extra>",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Failures",
        hovermode="x unified",
        height=480,
        margin=dict(l=75, r=35, t=100, b=80)
    )

    return style_figure(fig, height=480)


def chart_daily_mttr(df: pd.DataFrame):
    """Daily MTTR trend with range slider."""
    data = (
        df.groupby(df["Date"].dt.date)
        .agg({"MTTR (Hours)": "sum", "Site Name": "nunique"})
        .reset_index()
        .rename(columns={"Site Name": "Affected Sites"})
    )
    data["Date"] = pd.to_datetime(data["Date"])

    fig = px.line(
        data,
        x="Date",
        y="MTTR (Hours)",
        markers=True,
        title="Daily MTTR Trend with Range Selector",
        hover_data={"Affected Sites": ":,", "MTTR (Hours)": ":,.2f"},
    )

    avg_daily_mttr = data["MTTR (Hours)"].mean()
    fig.add_hline(
        y=avg_daily_mttr,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"Average: {avg_daily_mttr:,.1f}h",
        annotation_position="top left",
        annotation_font=dict(family="Inter, system-ui, sans-serif", size=11, color="#ef4444")
    )

    fig.update_traces(
        line=dict(width=3, color="#0ea5e9"),
        marker=dict(size=8, color="#0284c7"),
        hovertemplate=(
            "<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs"
            "<br>Affected sites: %{customdata[0]:,}<extra></extra>"
        ),
    )

    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day"),
                dict(count=14, label="2w", step="day"),
                dict(count=1, label="1m", step="month"),
                dict(step="all")
            ])
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="MTTR (Hours)",
        hovermode="x unified",
        height=520,
        margin=dict(l=75, r=35, t=100, b=100)
    )

    return style_figure(fig, height=520)


def chart_daily_activity(df: pd.DataFrame):
    """Dual-axis chart: failures and MTTR."""
    data = (
        df.groupby(df["Date"].dt.date)
        .agg({"MTTR (Hours)": "sum", "Site Name": "count"})
        .reset_index()
        .rename(columns={"Site Name": "Failure Count"})
    )
    data["Date"] = pd.to_datetime(data["Date"])

    fig = go.Figure()

    fig.add_bar(
        x=data["Date"],
        y=data["Failure Count"],
        name="Failures",
        marker_color="#8b5cf6",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Failures: %{y:,}<extra></extra>",
    )

    fig.add_scatter(
        x=data["Date"],
        y=data["MTTR (Hours)"],
        name="MTTR hours",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#10b981", width=3),
        marker=dict(size=8, color="#059669"),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>",
    )

    fig.update_layout(
        title="Daily Failures and MTTR Combined View",
        xaxis_title="Date",
        yaxis=dict(title="Number of Failures"),
        yaxis2=dict(
            title="MTTR (Hours)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        hovermode="x unified",
        barmode="group",
        height=500,
        margin=dict(l=75, r=75, t=100, b=80)
    )

    return style_figure(fig, height=500)


def chart_region_mttr(df: pd.DataFrame):
    """MTTR by region with comparison."""
    data = aggregate_sum(df, "REGION")

    fig = px.bar(
        data,
        x="REGION",
        y="MTTR (Hours)",
        color="REGION",
        color_discrete_sequence=DISCRETE_COLORS,
        text="MTTR (Hours)",
        title="MTTR by Region",
        hover_data={"MTTR (Hours)": ":,.2f", "REGION": False},
    )

    fig.update_layout(
        xaxis_title="Region",
        yaxis_title="MTTR (Hours)",
        showlegend=False,
        height=480,
        margin=dict(l=75, r=35, t=100, b=80)
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>"
    )

    return format_bar_text(style_figure(fig, height=480))


def chart_region_bucket_heatmap(df: pd.DataFrame):
    """Region vs bucket heatmap with enhanced styling."""
    data = df.pivot_table(
        index="REGION",
        columns="Bucket",
        values="MTTR (Hours)",
        aggfunc="sum",
        fill_value=0,
    )

    fig = px.imshow(
        data,
        color_continuous_scale=SEQUENTIAL_SCALE,
        aspect="auto",
        title="Regional MTTR Distribution by Failure Type",
        text_auto=".1f",
        labels=dict(x="Failure Type", y="Region", color="MTTR (hrs)"),
    )

    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Type: %{x}<br>MTTR: %{z:,.2f} hrs<extra></extra>"
    )

    fig.update_layout(
        height=520,
        margin=dict(l=100, r=100, t=100, b=80)
    )

    return style_figure(fig, height=520, showgrid=False)


def chart_site_mttr(df: pd.DataFrame, top_n: int = 15):
    """Top sites by MTTR with enhanced layout."""
    data = aggregate_sum(df, "Site Name", top_n=top_n)

    fig = px.bar(
        data,
        x="MTTR (Hours)",
        y="Site Name",
        orientation="h",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="MTTR (Hours)",
        title=f"Top {top_n} Sites by MTTR (Cumulative Hours)",
        hover_data={"MTTR (Hours)": ":,.2f", "Site Name": False},
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="MTTR (Hours)",
        coloraxis_showscale=False,
        height=600,
        margin=dict(l=160, r=35, t=100, b=80)
    )

    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>MTTR: %{x:,.2f} hrs<extra></extra>"
    )

    return format_bar_text(style_figure(fig, height=600))


def chart_site_failures(df: pd.DataFrame, top_n: int = 20):
    """Top sites by failure frequency."""
    data = (
        df.groupby("Site Name")
        .size()
        .reset_index(name="Failure Count")
        .sort_values("Failure Count", ascending=False)
        .head(top_n)
    )

    fig = px.bar(
        data,
        x="Failure Count",
        y="Site Name",
        orientation="h",
        color="Failure Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="Failure Count",
        title=f"Top {top_n} Sites by Failure Frequency",
        hover_data={"Failure Count": ":,", "Site Name": False},
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Number of Failures",
        coloraxis_showscale=False,
        height=650,
        margin=dict(l=160, r=35, t=100, b=80)
    )

    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Failures: %{x:,}<extra></extra>"
    )

    return style_figure(fig, height=650)


def chart_site_type_mttr(df: pd.DataFrame):
    """MTTR by site type."""
    data = aggregate_sum(df, "SITE TYPE")

    fig = px.bar(
        data,
        x="SITE TYPE",
        y="MTTR (Hours)",
        color="SITE TYPE",
        color_discrete_sequence=DISCRETE_COLORS,
        text="MTTR (Hours)",
        title="MTTR by Site Type",
        hover_data={"MTTR (Hours)": ":,.2f", "SITE TYPE": False},
    )

    fig.update_layout(
        xaxis_title="Site Type",
        yaxis_title="MTTR (Hours)",
        showlegend=False,
        height=480,
        margin=dict(l=75, r=35, t=100, b=80)
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>"
    )

    return format_bar_text(style_figure(fig, height=480))


def chart_site_scatter(df: pd.DataFrame):
    """Site MTTR vs monthly hours scatter plot."""
    if "Total Monthly Hrs" not in df.columns:
        return None

    data = (
        df.groupby(["Site Name", "Visibility", "REGION"], dropna=False)
        .agg({"MTTR (Hours)": "sum", "Total Monthly Hrs": "max"})
        .reset_index()
    )

    fig = px.scatter(
        data,
        x="Total Monthly Hrs",
        y="MTTR (Hours)",
        color="Visibility",
        size="MTTR (Hours)",
        hover_name="Site Name",
        color_discrete_sequence=DISCRETE_COLORS,
        hover_data={"REGION": True, "Total Monthly Hrs": ":,.2f", "MTTR (Hours)": ":,.2f"},
        title="Site MTTR vs Operating Hours (Size = MTTR Impact)",
    )

    fig.update_traces(marker=dict(line=dict(width=1, color=chart_text_color())))
    fig.update_layout(
        xaxis_title="Total Monthly Operating Hours",
        yaxis_title="Total MTTR (Hours)",
        hovermode="closest",
        height=520,
        margin=dict(l=75, r=35, t=100, b=80)
    )

    return style_figure(fig, height=520)


def chart_outage_breakdown(df: pd.DataFrame):
    """Sunburst chart for outage breakdown."""
    data = df.dropna(subset=["REGION", "Bucket", "SITE TYPE"])

    fig = px.sunburst(
        data,
        path=["REGION", "Bucket", "SITE TYPE"],
        values="MTTR (Hours)",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title="Outage Hierarchy: Region → Bucket → Site Type",
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>MTTR: %{value:,.2f} hrs<br>Share: %{percentParent:.1%}<extra></extra>"
    )

    fig.update_layout(
        height=580,
        margin=dict(l=35, r=35, t=100, b=35)
    )

    return style_figure(fig, height=580, showgrid=False)


def chart_daily_reasons(df: pd.DataFrame):
    """Sunburst chart for daily failures by site and bucket."""
    data = (
        df.groupby([df["Date"].dt.date, "Site Name", "Bucket"])
        .size()
        .reset_index(name="Count")
    )
    data["Date"] = data["Date"].astype(str)

    fig = px.sunburst(
        data,
        path=["Date", "Site Name", "Bucket"],
        values="Count",
        title="Daily Failures by Site and Reason",
        color="Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Failures: %{value:,}<br>Share: %{percentParent:.1%}<extra></extra>"
    )

    fig.update_layout(
        height=620,
        margin=dict(l=35, r=35, t=100, b=35)
    )

    return style_figure(fig, height=620, showgrid=False)


def chart_resolution_flow(df: pd.DataFrame):
    """Resolution flow sankey-like diagram."""
    required = ["Source of Power", "Bucket", "Status"]
    if any(column not in df.columns for column in required):
        return None

    data = df[required].dropna()
    if data.empty:
        return None

    dimensions = []
    labels = {
        "Source of Power": "Power Source",
        "Bucket": "Failure Type",
        "Status": "Resolution Status",
    }

    for col in required:
        categories = data[col].astype("category")
        dimensions.append(
            go.parcats.Dimension(
                values=categories,
                label=labels.get(col, col),
            )
        )

    status_colors = {
        "Resolved": "#10b981",
        "In Progress": "#0ea5e9",
        "Pending Vendor": "#f59e0b",
        "Investigating": "#8b5cf6",
        "Open": "#3b82f6",
        "Escalated": "#ef4444",
    }
    colors = [status_colors.get(s, "#64748b") for s in data["Status"]]

    fig = go.Figure(
        go.Parcats(
            dimensions=dimensions,
            line=dict(color=colors, showscale=False),
            hoveron="color",
            hoverinfo="count+probability",
            arrangement="freeform",
        )
    )

    fig.update_layout(
        title_text="Resolution Flow: Power Source → Failure Type → Status",
        height=520,
        margin=dict(l=80, r=80, t=100, b=55)
    )

    return style_figure(fig, height=520, showgrid=False)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application flow."""
    
    # Header
    st.markdown("# 📊 Network Failure & MTTR Dashboard")
    st.markdown("*Advanced analytics for failure analysis, SLA tracking, and predictive insights*")

    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "📁 Upload failure report",
        type=["xlsx", "xls", "csv"],
        help="Excel or CSV with Date, Region, Site, Bucket, MTTR columns"
    )

    if uploaded_file is None:
        st.info(
            "👉 **Getting started:** Upload a failure report from the sidebar to begin analysis. "
            "Reports should include Date, Region, Site Type, Site Name, Classification, Visibility, Bucket, and MTTR (Hours) columns."
        )
        return

    # Load and validate data
    df = load_data(uploaded_file)
    validate_columns(df)

    if df.empty:
        st.warning("The uploaded file has no valid rows after date processing.")
        return

    # Display optional columns notice
    missing_optional = [col for col in OPTIONAL_COLUMNS if col not in df.columns]
    if missing_optional:
        st.sidebar.info(
            f"⚠️ Optional fields missing: {', '.join(missing_optional)}. "
            "Some advanced visualizations will be unavailable."
        )

    # Apply filters
    filtered_df = apply_filters(df)

    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
        return

    # Render KPIs
    st.divider()
    render_kpis(filtered_df)
    st.divider()

    # Create tabs for different sections
    tab_overview, tab_regional, tab_sites, tab_patterns, tab_advanced, tab_data = st.tabs([
        "📊 Overview",
        "🌍 Regional Analysis",
        "📍 Site Performance",
        "📈 Patterns & Trends",
        "🔬 Advanced Analytics",
        "📋 Data Export"
    ])

    # ========================================================================
    # OVERVIEW TAB
    # ========================================================================
    with tab_overview:
        st.subheader("Executive Overview")
        st.markdown(
            '<p class="section-note">High-level summary of failures, trends, and key metrics</p>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_mttr_by_bucket(filtered_df))
        with col2:
            render_chart(chart_daily_failures(filtered_df))

        st.divider()
        render_chart(chart_daily_activity(filtered_df))
        render_chart(chart_daily_mttr(filtered_df))

    # ========================================================================
    # REGIONAL TAB
    # ========================================================================
    with tab_regional:
        st.subheader("Regional Impact Analysis")
        st.markdown(
            '<p class="section-note">Compare MTTR across regions and identify regional patterns</p>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            render_chart(chart_region_mttr(filtered_df))
        with col2:
            render_chart(chart_site_type_mttr(filtered_df))

        st.divider()
        render_chart(chart_region_bucket_heatmap(filtered_df))

        # Kenya Regional Map
        st.subheader("Kenya Regional Outage Map")
        map_metric = st.selectbox(
            "Select metric for map visualization",
            ["failure_count", "total_mttr", "avg_mttr"],
            format_func=lambda x: {
                "failure_count": "Failure Count",
                "total_mttr": "Total MTTR",
                "avg_mttr": "Average MTTR"
            }[x]
        )
        
        try:
            map_obj = create_kenya_map(filtered_df, metric=map_metric)
            if map_obj is not None:
                st.markdown("*Interactive map - use scroll to zoom, drag to pan*")
                st.write(map_obj)
            else:
                st.info("ℹ️ Map visualization requires folium library. Install with: pip install folium")
        except Exception as e:
            st.error(f"Could not create map: {str(e)}")

    # ========================================================================
    # SITE PERFORMANCE TAB
    # ========================================================================
    with tab_sites:
        st.subheader("Site Performance Analysis")
        st.markdown(
            '<p class="section-note">Identify problematic sites and understand their impact</p>',
            unsafe_allow_html=True
        )

        site_count = filtered_df["Site Name"].nunique()
        top_site_count = st.slider(
            "Sites to display",
            min_value=1 if site_count < 5 else 5,
            max_value=max(1, min(50, site_count)),
            value=max(1, min(15, site_count)),
        )

        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_site_mttr(filtered_df, top_n=top_site_count))
        with col2:
            render_chart(chart_site_failures(filtered_df, top_n=top_site_count))

        st.divider()
        scatter = chart_site_scatter(filtered_df)
        if scatter is not None:
            render_chart(scatter)
        else:
            st.info("ℹ️ Add 'Total Monthly Hrs' column to view scatter plot analysis")

    # ========================================================================
    # PATTERNS & TRENDS TAB
    # ========================================================================
    with tab_patterns:
        st.subheader("Failure Patterns and Hierarchies")
        st.markdown(
            '<p class="section-note">Explore hierarchical breakdown and time-based patterns</p>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_outage_breakdown(filtered_df))
        with col2:
            render_chart(chart_daily_reasons(filtered_df))

        st.divider()
        flow = chart_resolution_flow(filtered_df)
        if flow is not None:
            st.subheader("Resolution Flow Analysis")
            render_chart(flow)
        else:
            st.info("ℹ️ Add 'Source of Power' and 'Status' columns to view resolution flow")

        # Outage heatmap
        st.subheader("Outage Hour Heatmap")
        st.markdown("*Identifies which hours and days experience most outages*")
        try:
            render_chart(create_outage_hour_heatmap(filtered_df))
        except Exception as e:
            st.error(f"Could not create heatmap: {str(e)}")

    # ========================================================================
    # ADVANCED ANALYTICS TAB
    # ========================================================================
    with tab_advanced:
        st.subheader("Advanced Analytics & Predictions")
        st.markdown(
            '<p class="section-note">Anomaly detection, SLA compliance, forecasting, and team metrics</p>',
            unsafe_allow_html=True
        )

        # ANOMALY DETECTION
        st.subheader("🚨 Anomaly Detection")
        try:
            detector = AnomalyDetector()
            anomalies = detector.detect_by_iqr(filtered_df["MTTR (Hours)"])
            render_chart(create_anomaly_chart(filtered_df, anomalies))
            
            anomaly_count = anomalies.sum()
            st.metric("Detected Anomalies", f"{anomaly_count} ({anomaly_count/len(filtered_df)*100:.1f}%)")
        except Exception as e:
            st.error(f"Anomaly detection error: {str(e)}")

        st.divider()

        # SLA TRACKING
        st.subheader("📋 SLA Compliance & Breaches")
        col1, col2, col3 = st.columns(3)
        
        try:
            tracker = SLATracker()
            sla_metrics = tracker.calculate_sla_compliance(filtered_df, sla_threshold=SLA_THRESHOLD_MAJOR)
            
            with col1:
                compliance_pct = sla_metrics["compliance_rate"]
                status = "✅ Good" if compliance_pct >= 95 else "⚠️ Warning" if compliance_pct >= 80 else "❌ Critical"
                st.metric("SLA Compliance", f"{compliance_pct}%", status)
            
            with col2:
                st.metric("SLA Breaches", sla_metrics["breaches"])
            
            with col3:
                st.metric("Total Records", sla_metrics["total"])
            
            breaches = tracker.get_sla_breaches(filtered_df, sla_threshold=SLA_THRESHOLD_MAJOR, top_n=10)
            render_chart(create_sla_breach_chart(breaches, sla_metrics["total"]))
            
            st.markdown("**SLA Threshold:** 24 hours (Major incidents)")
        except Exception as e:
            st.error(f"SLA tracking error: {str(e)}")

        st.divider()

        # MTTR FORECASTING
        st.subheader("📊 MTTR Trend & Forecast")
        try:
            predictor = MTTRPredictor()
            forecast_df = predictor.forecast_mttr(filtered_df, periods=7)
            render_chart(create_mttr_trend_forecast(forecast_df))
            st.markdown("*Forecast uses exponential smoothing on daily average MTTR*")
        except Exception as e:
            st.error(f"Forecasting error: {str(e)}")

        st.divider()

        # TEAM PERFORMANCE (if data available)
        if "Engineer" in filtered_df.columns or "Team" in filtered_df.columns:
            st.subheader("👥 Team Performance Metrics")
            team_col = "Team" if "Team" in filtered_df.columns else "Engineer"
            try:
                perf = PerformanceMetrics()
                team_metrics = perf.calculate_team_metrics(filtered_df, team_col=team_col)
                if not team_metrics.empty:
                    render_chart(create_team_performance_chart(team_metrics, team_col=team_col))
            except Exception as e:
                st.error(f"Team metrics error: {str(e)}")

    # ========================================================================
    # DATA EXPORT TAB
    # ========================================================================
    with tab_data:
        st.subheader("Filtered Dataset & Export")
        st.markdown(
            '<p class="section-note">Review and export the filtered analysis dataset</p>',
            unsafe_allow_html=True
        )

        st.dataframe(filtered_df, use_container_width=True, height=600)

        col1, col2 = st.columns(2)

        with col1:
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"failure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        with col2:
            st.info("💡 Tip: Use the filters in the sidebar to refine the dataset before exporting")


if __name__ == "__main__":
    main()
