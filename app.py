import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


REQUIRED_COLUMNS = [
    "Date",
    "REGION",
    "SITE TYPE",
    "Site Classification",
    "Visibility",
    "Bucket",
    "MTTR (Hours)",
    "Site Name",
]

OPTIONAL_COLUMNS = [
    "Total Monthly Hrs",
    "Source of Power",
    "Status",
]

SEQUENTIAL_SCALE = "Viridis"
DISCRETE_COLORS = px.colors.qualitative.Safe


st.set_page_config(
    page_title="Network Failure Analysis",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded",
)


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
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
        }
        [data-testid="stSidebar"] {
            background: color-mix(in srgb, var(--background-color) 94%, var(--text-color) 6%);
        }
        .section-note {
            color: var(--text-color);
            font-size: 0.95rem;
            margin-top: -0.35rem;
            margin-bottom: 1rem;
            opacity: 0.74;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def is_dark_theme():
    return st.get_option("theme.base") == "dark"


def chart_template():
    return "plotly_dark" if is_dark_theme() else "plotly_white"


def chart_text_color():
    return "#f8fafc" if is_dark_theme() else "#0f172a"


def chart_grid_color():
    return "rgba(226, 232, 240, 0.20)" if is_dark_theme() else "#e5e7eb"


def style_figure(fig, height=430):
    fig.update_layout(
        template=chart_template(),
        height=height,
        margin=dict(l=20, r=20, t=70, b=35),
        font=dict(size=13, color=chart_text_color()),
        title=dict(font=dict(size=17), x=0.02, xanchor="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="#111827" if is_dark_theme() else "#ffffff",
            font=dict(color="#f8fafc" if is_dark_theme() else "#0f172a"),
            bordercolor=chart_grid_color(),
        ),
        coloraxis_colorbar=dict(title_font=dict(color=chart_text_color())),
    )
    fig.update_xaxes(showgrid=True, gridcolor=chart_grid_color(), zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=chart_grid_color(), zeroline=False)
    return fig


def format_bar_text(fig):
    fig.update_traces(
        texttemplate="%{text:,.2f}",
        textposition="auto",
        cliponaxis=False,
    )
    return fig


def render_chart(fig, **kwargs):
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=CHART_CONFIG,
        **kwargs,
    )


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

    for column in ["MTTR (Hours)", "Total Monthly Hrs"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].astype(str).str.strip()
        df[column] = df[column].replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})

    return df


def validate_columns(df):
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        st.error(
            "The uploaded file is missing required columns: "
            + ", ".join(f"`{column}`" for column in missing)
        )
        st.stop()


def multiselect_filter(label, column, data):
    options = sorted(data[column].dropna().unique())
    return st.sidebar.multiselect(label, options=options, default=options)


def apply_filters(df):
    st.sidebar.header("Filters")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) != 2:
        st.warning("Select both a start date and an end date.")
        st.stop()

    start_date, end_date = date_range
    if start_date > end_date:
        st.warning("Start date must be before end date.")
        st.stop()

    selected_regions = multiselect_filter("Region", "REGION", df)
    selected_site_types = multiselect_filter("Site type", "SITE TYPE", df)
    selected_classes = multiselect_filter("Site classification", "Site Classification", df)
    selected_visibility = multiselect_filter("Visibility", "Visibility", df)
    selected_buckets = multiselect_filter("Failure bucket", "Bucket", df)

    mttr_min = float(df["MTTR (Hours)"].min())
    mttr_max = float(df["MTTR (Hours)"].max())
    if mttr_min == mttr_max:
        st.sidebar.caption(f"MTTR range is fixed at {mttr_min:.2f} hours.")
        mttr_range = (mttr_min, mttr_max)
    else:
        mttr_range = st.sidebar.slider(
            "MTTR range (hours)",
            min_value=mttr_min,
            max_value=mttr_max,
            value=(mttr_min, mttr_max),
        )

    mask = (
        (df["Date"].dt.date >= start_date)
        & (df["Date"].dt.date <= end_date)
        & (df["REGION"].isin(selected_regions))
        & (df["SITE TYPE"].isin(selected_site_types))
        & (df["Site Classification"].isin(selected_classes))
        & (df["Visibility"].isin(selected_visibility))
        & (df["Bucket"].isin(selected_buckets))
        & (df["MTTR (Hours)"] >= mttr_range[0])
        & (df["MTTR (Hours)"] <= mttr_range[1])
    )
    return df.loc[mask].copy()


def aggregate_sum(df, group_column, value_column="MTTR (Hours)", top_n=None):
    result = (
        df.groupby(group_column, dropna=False)[value_column]
        .sum()
        .reset_index()
        .sort_values(value_column, ascending=False)
    )
    if top_n:
        result = result.head(top_n)
    return result


def render_kpis(df):
    total_failures = len(df)
    total_mttr = df["MTTR (Hours)"].sum()
    avg_mttr = df["MTTR (Hours)"].mean()
    affected_sites = df["Site Name"].nunique()
    high_mttr = int((df["MTTR (Hours)"] > avg_mttr).sum()) if total_failures else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total failures", f"{total_failures:,}")
    col2.metric("Total MTTR", f"{total_mttr:,.2f} hrs")
    col3.metric("Average MTTR", f"{avg_mttr:,.2f} hrs")
    col4.metric("Affected sites", f"{affected_sites:,}")
    col5.metric("Above avg MTTR", f"{high_mttr:,}")


def chart_mttr_by_bucket(df):
    data = aggregate_sum(df, "Bucket")
    data["Failures"] = data["Bucket"].map(df["Bucket"].value_counts())
    fig = px.bar(
        data,
        x="Bucket",
        y="MTTR (Hours)",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="MTTR (Hours)",
        title="Total MTTR by Failure Bucket",
        hover_data={"Failures": ":,", "MTTR (Hours)": ":,.2f", "Bucket": False},
    )
    fig.update_layout(xaxis_title="Failure bucket", yaxis_title="MTTR hours")
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<br>Failures: %{customdata[0]:,}<extra></extra>"
    )
    return format_bar_text(style_figure(fig))


def chart_daily_failures(df):
    data = df.groupby(df["Date"].dt.date).size().reset_index(name="Failure Count")
    data["Date"] = pd.to_datetime(data["Date"])
    fig = px.line(
        data,
        x="Date",
        y="Failure Count",
        markers=True,
        title="Daily Failure Count",
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Failures: %{y:,}<extra></extra>",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Failures", hovermode="x unified")
    return style_figure(fig)


def chart_daily_mttr(df):
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
        title="Daily MTTR Trend",
        hover_data={"Affected Sites": ":,", "MTTR (Hours)": ":,.2f"},
    )
    avg_daily_mttr = data["MTTR (Hours)"].mean()
    fig.add_hline(
        y=avg_daily_mttr,
        line_dash="dash",
        line_color="#f97316",
        annotation_text=f"Avg {avg_daily_mttr:,.2f} hrs",
        annotation_position="top left",
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate=(
            "<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs"
            "<br>Affected sites: %{customdata[0]:,}<extra></extra>"
        ),
    )
    fig.update_xaxes(rangeslider_visible=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="MTTR hours", hovermode="x unified")
    return style_figure(fig, height=460)


def chart_daily_activity(df):
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
        marker_color="#3b82f6",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Failures: %{y:,}<extra></extra>",
    )
    fig.add_scatter(
        x=data["Date"],
        y=data["MTTR (Hours)"],
        name="MTTR hours",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#f97316", width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>",
    )
    fig.update_layout(
        title="Daily Failures and MTTR Together",
        xaxis_title="Date",
        yaxis=dict(title="Failures"),
        yaxis2=dict(
            title="MTTR hours",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        hovermode="x unified",
        barmode="group",
    )
    return style_figure(fig, height=470)


def chart_region_mttr(df):
    data = aggregate_sum(df, "REGION")
    fig = px.bar(
        data,
        x="REGION",
        y="MTTR (Hours)",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="MTTR (Hours)",
        title="MTTR by Region",
        hover_data={"MTTR (Hours)": ":,.2f", "REGION": False},
    )
    fig.update_layout(xaxis_title="Region", yaxis_title="MTTR hours")
    fig.update_traces(hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>")
    return format_bar_text(style_figure(fig))


def chart_region_bucket_heatmap(df):
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
        title="Regional MTTR Heatmap by Failure Bucket",
        text_auto=".1f",
        labels=dict(x="Failure bucket", y="Region", color="MTTR hours"),
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Bucket: %{x}<br>MTTR: %{z:,.2f} hrs<extra></extra>"
    )
    return style_figure(fig, height=500)


def chart_site_mttr(df, top_n=15):
    data = aggregate_sum(df, "Site Name", top_n=top_n)
    fig = px.bar(
        data,
        x="MTTR (Hours)",
        y="Site Name",
        orientation="h",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="MTTR (Hours)",
        title=f"Top {top_n} Sites by MTTR",
        hover_data={"MTTR (Hours)": ":,.2f", "Site Name": False},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="MTTR hours")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>MTTR: %{x:,.2f} hrs<extra></extra>")
    return format_bar_text(style_figure(fig, height=560))


def chart_site_failures(df, top_n=20):
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
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Failures")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Failures: %{x:,}<extra></extra>")
    return style_figure(fig, height=620)


def chart_site_type_mttr(df):
    data = aggregate_sum(df, "SITE TYPE")
    fig = px.bar(
        data,
        x="SITE TYPE",
        y="MTTR (Hours)",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        text="MTTR (Hours)",
        title="MTTR by Site Type",
        hover_data={"MTTR (Hours)": ":,.2f", "SITE TYPE": False},
    )
    fig.update_layout(xaxis_title="Site type", yaxis_title="MTTR hours")
    fig.update_traces(hovertemplate="<b>%{x}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>")
    return format_bar_text(style_figure(fig))


def chart_site_scatter(df):
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
        title="Site MTTR vs Monthly Hours",
    )
    fig.update_traces(marker=dict(line=dict(width=1, color=chart_text_color())))
    fig.update_layout(
        xaxis_title="Total monthly hours",
        yaxis_title="MTTR hours",
        hovermode="closest",
    )
    return style_figure(fig, height=520)


def chart_outage_breakdown(df):
    data = df.dropna(subset=["REGION", "Bucket", "SITE TYPE"])
    fig = px.sunburst(
        data,
        path=["REGION", "Bucket", "SITE TYPE"],
        values="MTTR (Hours)",
        color="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title="Outage Breakdown: Region, Bucket, and Site Type",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>MTTR: %{value:,.2f} hrs<br>Share: %{percentParent:.1%}<extra></extra>"
    )
    return style_figure(fig, height=560)


def chart_daily_reasons(df):
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
        title="Daily Site Failures and Reasons",
        color="Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Failures: %{value:,}<br>Share: %{percentParent:.1%}<extra></extra>"
    )
    return style_figure(fig, height=620)


def chart_resolution_flow(df):
    required = ["Source of Power", "Bucket", "Status"]
    if any(column not in df.columns for column in required):
        return None

    data = df[required].dropna()
    if data.empty:
        return None

    fig = px.parallel_categories(
        data,
        dimensions=required,
        color=data["Status"].astype("category").cat.codes,
        color_continuous_scale=SEQUENTIAL_SCALE,
        labels={
            "Source of Power": "Power source",
            "Bucket": "Failure bucket",
            "Status": "Ticket status",
        },
        title="Resolution Flow",
    )
    return style_figure(fig, height=500)


def render_missing_optional_notice(df):
    missing_optional = [column for column in OPTIONAL_COLUMNS if column not in df.columns]
    if missing_optional:
        st.sidebar.caption(
            "Optional visuals skipped when these fields are absent: "
            + ", ".join(missing_optional)
        )


def main():
    st.title("Network Failure and MTTR Dashboard")
    st.caption("Daily operations view for filtering, ranking, and explaining network failures.")

    uploaded_file = st.sidebar.file_uploader(
        "Upload failure report",
        type=["xlsx", "xls", "csv"],
        help="Upload an Excel or CSV report with Date, Region, Site, Bucket, and MTTR fields.",
    )

    if uploaded_file is None:
        st.info("Upload a failure report from the sidebar to begin analysis.")
        return

    df = load_data(uploaded_file)
    validate_columns(df)

    if df.empty:
        st.warning("The uploaded file has no valid rows after date cleaning.")
        return

    render_missing_optional_notice(df)
    filtered_df = apply_filters(df)

    if filtered_df.empty:
        st.warning("No data is available for the selected filters.")
        return

    render_kpis(filtered_df)
    st.divider()

    overview_tab, regional_tab, site_tab, patterns_tab, flow_tab, data_tab = st.tabs(
        [
            "Overview",
            "Regional analysis",
            "Site performance",
            "Failure patterns",
            "Resolution and SLA",
            "Data export",
        ]
    )

    with overview_tab:
        st.subheader("Executive overview")
        st.markdown(
            (
                '<p class="section-note">Use this view to understand the overall volume, '
                "MTTR trend, and largest failure drivers.</p>"
            ),
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_mttr_by_bucket(filtered_df))
        with col2:
            render_chart(chart_daily_failures(filtered_df))
        render_chart(chart_daily_activity(filtered_df))
        render_chart(chart_daily_mttr(filtered_df))

    with regional_tab:
        st.subheader("Regional analysis")
        st.markdown(
            (
                '<p class="section-note">Compare total MTTR across regions and identify '
                "which failure buckets drive regional impact.</p>"
            ),
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            render_chart(chart_region_mttr(filtered_df))
        with col2:
            render_chart(chart_site_type_mttr(filtered_df))
        render_chart(chart_region_bucket_heatmap(filtered_df))

    with site_tab:
        st.subheader("Site performance")
        st.markdown(
            (
                '<p class="section-note">Find sites causing the highest MTTR and sites '
                "with repeated failure events.</p>"
            ),
            unsafe_allow_html=True,
        )
        site_count = filtered_df["Site Name"].nunique()
        top_site_count = st.slider(
            "Sites to show",
            min_value=1 if site_count < 5 else 5,
            max_value=max(1, min(50, site_count)),
            value=max(1, min(15, site_count)),
        )
        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_site_mttr(filtered_df, top_n=top_site_count))
        with col2:
            render_chart(chart_site_failures(filtered_df, top_n=top_site_count))

        scatter = chart_site_scatter(filtered_df)
        if scatter is not None:
            render_chart(scatter)
        else:
            st.info("Add `Total Monthly Hrs` to the report to view the site MTTR scatter plot.")

    with patterns_tab:
        st.subheader("Failure patterns")
        st.markdown(
            (
                '<p class="section-note">Explore how failures are distributed by region, '
                "bucket, site type, site, and day.</p>"
            ),
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            render_chart(chart_outage_breakdown(filtered_df))
        with col2:
            render_chart(chart_daily_reasons(filtered_df))

    with flow_tab:
        st.subheader("Resolution and SLA")
        st.markdown(
            (
                '<p class="section-note">Review ticket status flow and spot high-MTTR '
                "records that may need attention.</p>"
            ),
            unsafe_allow_html=True,
        )
        flow = chart_resolution_flow(filtered_df)
        if flow is not None:
            render_chart(flow)
        else:
            st.info("Add `Source of Power` and `Status` to the report to view resolution flow.")

        avg_mttr = filtered_df["MTTR (Hours)"].mean()
        high_mttr_df = filtered_df[filtered_df["MTTR (Hours)"] > avg_mttr].sort_values(
            "MTTR (Hours)",
            ascending=False,
        )
        high_mttr_columns = [
            column
            for column in ["Date", "Site Name", "REGION", "Bucket", "MTTR (Hours)", "Status"]
            if column in high_mttr_df.columns
        ]
        st.dataframe(
            high_mttr_df[high_mttr_columns],
            use_container_width=True,
            hide_index=True,
        )

    with data_tab:
        st.subheader("Filtered data")
        st.markdown(
            (
                '<p class="section-note">Inspect the filtered records and export the '
                "current analysis dataset.</p>"
            ),
            unsafe_allow_html=True,
        )
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download filtered CSV",
            data=csv,
            file_name="filtered_failure_report.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
