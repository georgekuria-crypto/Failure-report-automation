
"""
Production Network Failure and MTTR Dashboard
Cleaned and Optimized Version
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from io import BytesIO

from visualizations import (
    style_figure,
    format_bar_text,
    render_chart,
    SEQUENTIAL_SCALE,
    DISCRETE_COLORS,
)

from constants import REQUIRED_COLUMNS, OPTIONAL_COLUMNS


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Network Failure Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown(
    """
    <style>

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        [data-testid="stMetric"] {
            background: color-mix(in srgb, var(--background-color) 88%, var(--text-color) 12%);
            border: 1px solid color-mix(in srgb, var(--background-color) 70%, var(--text-color) 30%);
            border-radius: 12px;
            padding: 14px 16px;
        }

        [data-testid="stSidebar"] {
            background: color-mix(in srgb, var(--background-color) 94%, var(--text-color) 6%);
        }

        .section-note {
            font-size: 0.95rem;
            opacity: 0.75;
            margin-bottom: 1rem;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


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

    # Date Parsing
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

    # Numeric Conversion
    numeric_columns = [
        "MTTR (Hours)",
        "Total Monthly Hrs",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Clean Object Columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})
        )

    return df


# =========================================================
# VALIDATION
# =========================================================

def validate_columns(df):

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        st.error(
            "Missing required columns: "
            + ", ".join(missing)
        )
        st.stop()


# =========================================================
# FILTERS
# =========================================================

def multiselect_filter(label, column, data):

    options = sorted(data[column].dropna().unique())

    return st.sidebar.multiselect(
        label,
        options=options,
        default=options,
    )


def apply_filters(df):

    st.sidebar.header("Dashboard Filters")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) != 2:
        st.warning("Please select a valid start and end date.")
        st.stop()

    start_date, end_date = date_range

    selected_regions = multiselect_filter(
        "Region",
        "REGION",
        df,
    )

    selected_site_types = multiselect_filter(
        "Site Type",
        "SITE TYPE",
        df,
    )

    selected_classes = multiselect_filter(
        "Site Classification",
        "Site Classification",
        df,
    )

    selected_visibility = multiselect_filter(
        "Visibility",
        "Visibility",
        df,
    )

    selected_buckets = multiselect_filter(
        "Failure Bucket",
        "Bucket",
        df,
    )

    mttr_min = float(df["MTTR (Hours)"].min())
    mttr_max = float(df["MTTR (Hours)"].max())

    mttr_range = st.sidebar.slider(
        "MTTR Range (Hours)",
        min_value=mttr_min,
        max_value=mttr_max,
        value=(mttr_min, mttr_max),
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

    return filtered_df


# =========================================================
# KPI SECTION
# =========================================================

def render_kpis(df):

    total_failures = len(df)

    total_mttr = df["MTTR (Hours)"].sum()

    avg_mttr = df["MTTR (Hours)"].mean()

    affected_sites = df["Site Name"].nunique()

    critical_failures = int(
        (df["MTTR (Hours)"] > avg_mttr).sum()
    )

    cols = st.columns(5)

    cols[0].metric("Total Failures", f"{total_failures:,}")

    cols[1].metric("Total MTTR", f"{total_mttr:,.2f} hrs")

    cols[2].metric("Average MTTR", f"{avg_mttr:,.2f} hrs")

    cols[3].metric("Affected Sites", f"{affected_sites:,}")

    cols[4].metric("Critical Failures", f"{critical_failures:,}")


# =========================================================
# EXECUTIVE SUMMARY
# =========================================================

def render_executive_summary(df):

    worst_region = (
        df.groupby("REGION")["MTTR (Hours)"]
        .sum()
        .idxmax()
    )

    worst_bucket = (
        df.groupby("Bucket")["MTTR (Hours)"]
        .sum()
        .idxmax()
    )

    worst_site = (
        df.groupby("Site Name")["MTTR (Hours)"]
        .sum()
        .idxmax()
    )

    peak_day = (
        df.groupby(df["Date"].dt.date)["MTTR (Hours)"]
        .sum()
        .idxmax()
    )

    st.info(
        f"""
        Highest MTTR Region: {worst_region} |
        Largest Failure Bucket: {worst_bucket} |
        Worst Performing Site: {worst_site} |
        Peak Outage Day: {peak_day}
        """
    )


# =========================================================
# AGGREGATION
# =========================================================

def aggregate_sum(
    df,
    group_column,
    value_column="MTTR (Hours)",
    top_n=None,
):

    data = (
        df.groupby(group_column)[value_column]
        .sum()
        .reset_index()
        .sort_values(value_column, ascending=False)
    )

    if top_n:
        data = data.head(top_n)

    return data


# =========================================================
# CHARTS
# =========================================================

def chart_mttr_by_bucket(df):

    data = aggregate_sum(df, "Bucket")

    fig = px.bar(
        data,
        x="Bucket",
        y="MTTR (Hours)",
        color="Bucket",
        text="MTTR (Hours)",
        color_discrete_sequence=DISCRETE_COLORS,
        title="Total MTTR by Failure Bucket",
    )

    fig.update_layout(showlegend=False)

    return format_bar_text(style_figure(fig))


def chart_daily_failures(df):

    data = (
        df.groupby(df["Date"].dt.date)
        .size()
        .reset_index(name="Failure Count")
    )

    data["Date"] = pd.to_datetime(data["Date"])

    fig = px.line(
        data,
        x="Date",
        y="Failure Count",
        markers=True,
        title="Daily Failure Count",
    )

    return style_figure(fig)


def chart_daily_mttr(df):

    data = (
        df.groupby(df["Date"].dt.date)
        ["MTTR (Hours)"]
        .sum()
        .reset_index()
    )

    data["Date"] = pd.to_datetime(data["Date"])

    fig = px.line(
        data,
        x="Date",
        y="MTTR (Hours)",
        markers=True,
        title="Daily MTTR Trend",
    )

    return style_figure(fig)


def chart_daily_activity(df):

    data = (
        df.groupby(df["Date"].dt.date)
        .agg({
            "MTTR (Hours)": "sum",
            "Site Name": "count"
        })
        .reset_index()
        .rename(columns={"Site Name": "Failure Count"})
    )

    data["Date"] = pd.to_datetime(data["Date"])

    fig = go.Figure()

    fig.add_bar(
        x=data["Date"],
        y=data["Failure Count"],
        name="Failures",
    )

    fig.add_scatter(
        x=data["Date"],
        y=data["MTTR (Hours)"],
        name="MTTR",
        yaxis="y2",
        mode="lines+markers",
    )

    fig.update_layout(
        title="Daily Failures vs MTTR",
        yaxis=dict(title="Failures"),
        yaxis2=dict(
            title="MTTR",
            overlaying="y",
            side="right",
        ),
    )

    return style_figure(fig)


def chart_region_mttr(df):

    data = aggregate_sum(df, "REGION")

    fig = px.bar(
        data,
        x="REGION",
        y="MTTR (Hours)",
        color="REGION",
        text="MTTR (Hours)",
        color_discrete_sequence=DISCRETE_COLORS,
        title="Regional MTTR",
    )

    fig.update_layout(showlegend=False)

    return format_bar_text(style_figure(fig))


def chart_region_heatmap(df):

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
        text_auto=".1f",
        aspect="auto",
        title="Regional MTTR Heatmap",
    )

    return style_figure(fig)


def chart_site_mttr(df, top_n=15):

    data = aggregate_sum(
        df,
        "Site Name",
        top_n=top_n,
    )

    fig = px.bar(
        data,
        x="MTTR (Hours)",
        y="Site Name",
        orientation="h",
        color="MTTR (Hours)",
        text="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=f"Top {top_n} Sites by MTTR",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    return format_bar_text(style_figure(fig, height=600))


def chart_site_failures(df, top_n=15):

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
        text="Failure Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=f"Top {top_n} Sites by Failure Frequency",
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    return style_figure(fig, height=600)


# =========================================================
# EXCEL EXPORT
# =========================================================

def generate_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Filtered Data"
        )

    return output.getvalue()


# =========================================================
# MAIN APP
# =========================================================

def main():

    st.title("Network Failure and MTTR Dashboard")

    st.caption(
        "Operational analytics dashboard for telecom network failure monitoring."
    )

    uploaded_file = st.sidebar.file_uploader(
        "Upload Failure Report",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is None:
        st.info("Upload a report to begin analysis.")
        return

    df = load_data(uploaded_file)

    validate_columns(df)

    if df.empty:
        st.warning("No valid data found.")
        return

    filtered_df = apply_filters(df)

    if filtered_df.empty:
        st.warning(
            "No data matches the current filters. "
            "Try expanding the filter selections."
        )
        return

    # Sidebar Summary
    st.sidebar.divider()

    st.sidebar.metric(
        "Filtered Records",
        f"{len(filtered_df):,}"
    )

    st.sidebar.metric(
        "Regions",
        filtered_df["REGION"].nunique()
    )

    st.sidebar.metric(
        "Sites",
        filtered_df["Site Name"].nunique()
    )

    # KPIs
    render_kpis(filtered_df)

    st.divider()

    render_executive_summary(filtered_df)

    # Tabs
    overview_tab, regional_tab, site_tab, export_tab = st.tabs(
        [
            "Overview",
            "Regional Analysis",
            "Site Performance",
            "Data Export",
        ]
    )

    # =====================================================
    # OVERVIEW TAB
    # =====================================================

    with overview_tab:

        col1, col2 = st.columns(2)

        with col1:
            render_chart(chart_mttr_by_bucket(filtered_df))

        with col2:
            render_chart(chart_daily_failures(filtered_df))

        render_chart(chart_daily_activity(filtered_df))

        render_chart(chart_daily_mttr(filtered_df))

    # =====================================================
    # REGIONAL TAB
    # =====================================================

    with regional_tab:

        col1, col2 = st.columns(2)

        with col1:
            render_chart(chart_region_mttr(filtered_df))

        with col2:
            render_chart(chart_region_heatmap(filtered_df))

    # =====================================================
    # SITE TAB
    # =====================================================

    with site_tab:

        top_n = st.slider(
            "Sites to Display",
            min_value=5,
            max_value=50,
            value=15,
        )

        col1, col2 = st.columns(2)

        with col1:
            render_chart(
                chart_site_mttr(
                    filtered_df,
                    top_n,
                )
            )

        with col2:
            render_chart(
                chart_site_failures(
                    filtered_df,
                    top_n,
                )
            )

    # =====================================================
    # EXPORT TAB
    # =====================================================

    with export_tab:

        st.dataframe(
            filtered_df.head(1000),
            use_container_width=True,
            hide_index=True,
        )

        excel_data = generate_excel(filtered_df)

        st.download_button(
            label="Download Excel Report",
            data=excel_data,
            file_name="network_failure_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()

