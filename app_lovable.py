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
import os
import tempfile
from fpdf import FPDF

from visualizations import (
    DISCRETE_COLORS,
    SEQUENTIAL_SCALE,
    format_bar_text,
    render_chart,
    style_figure,
    CHART_CONFIG,
)

from constants import OPTIONAL_COLUMNS, REQUIRED_COLUMNS  # noqa: F401

# Attempt importing plotly_events safely
try:
    from streamlit_plotly_events import plotly_events
    PLOTLY_EVENTS_AVAILABLE = True
except ImportError:
    PLOTLY_EVENTS_AVAILABLE = False


class NavigationState:
    """Class representing a node in the interactive drilldown path."""
    def __init__(self, view_type: str, filter_col: str | None = None, filter_val: str | None = None):
        self.view_type = view_type  # 'dashboard', 'category_details', 'site_details'
        self.filter_col = filter_col  # The column name to filter
        self.filter_val = filter_val  # The value of the category


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
    "bg":           "var(--background-color)",
    "bg_soft":      "var(--secondary-background-color)",
    "surface":      "var(--secondary-background-color)",
    "surface_2":    "rgba(148,163,184,0.15)",
    "border":       "rgba(148,163,184,0.25)",
    "text":         "var(--text-color)",
    "text_muted":   "rgba(148,163,184,0.85)",  # Slate-like neutral gray with alpha
    "navy":         "var(--primary-color)",
    "electric":     "#3B82F6",
    "cyan":         "#06B6D4",
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
                background: {THEME["surface_2"]};
            }}
            .stTabs [aria-selected="true"] {{
                background: linear-gradient(135deg, {THEME["electric"]}, {THEME["violet"]}) !important;
                color: #fff !important;
                box-shadow: 0 6px 20px -8px {THEME["electric"]};
            }}

            /* ---------- SIDEBAR ---------- */
            [data-testid="stSidebar"] {{
                background: {THEME["bg_soft"]};
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
            bgcolor=THEME["surface_2"],
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
    
    # Rotate x-axis labels vertically downwards for date charts
    is_date_axis = False
    if hasattr(fig.layout, "xaxis") and hasattr(fig.layout.xaxis, "title") and hasattr(fig.layout.xaxis.title, "text"):
        if fig.layout.xaxis.title.text and "date" in str(fig.layout.xaxis.title.text).lower():
            is_date_axis = True
            
    if not is_date_axis:
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None and len(trace.x) > 0:
                first_x = trace.x[0]
                if type(first_x).__name__ == "datetime64" or isinstance(first_x, (pd.Timestamp, __import__('datetime').date, __import__('datetime').datetime)):
                    is_date_axis = True
                    break
                    
    if is_date_axis:
        fig.update_xaxes(
            tickangle=-90,
            dtick="86400000.0",
            tickformat="%d %b %Y",
            tickfont=dict(size=10, color=THEME["text_muted"]),
            automargin=True
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
                trace.marker.line = dict(width=1.5, color=THEME["bg"])

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

    # Column normalization for cross-vendor support (e.g. Safaricom vs Airtel)
    column_mapping = {
        "DATE": "Date",
        "Region": "REGION",
        "Site Type": "SITE TYPE",
        "TOTAL DOWN TIME (HOURS)": "MTTR (Hours)",
        "TOTAL DOWNTIME(HOURS)": "MTTR (Hours)",
        "TOTAL DOWTIME(HOURS)": "MTTR (Hours)",
        "total downtime(hours)": "MTTR (Hours)",
        "total downtime (hours)": "MTTR (Hours)",
        "BHT (HOURS)": "MTTR (Hours)",
        "BHT ( HOURS)": "MTTR (Hours)",
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
            
    # Inject defaults for structural columns that might be missing in some vendor sheets
    if "Date" in df.columns:
        # Multi-pass parser to strictly enforce m/d/y priority for strings while preserving native datetimes
        date_col = df["Date"]
        
        # Strict d/m/y parsing first
        s_dmy = pd.to_datetime(date_col, format="%d/%m/%Y", errors="coerce")
        s_dmy2 = pd.to_datetime(date_col, format="%d-%m-%Y", errors="coerce")
        s_dmy3 = pd.to_datetime(date_col, format="%d/%m/%y", errors="coerce")
        
        s_mdy = pd.to_datetime(date_col, format="%m/%d/%Y", errors="coerce")
        s_mdy2 = pd.to_datetime(date_col, format="%m-%d-%Y", errors="coerce")
        s_mdy3 = pd.to_datetime(date_col, format="%m/%d/%y", errors="coerce")
        
        s_gen = pd.to_datetime(date_col, errors="coerce", format="mixed", dayfirst=True)
        
        df["Date"] = s_dmy.combine_first(s_dmy2).combine_first(s_dmy3).combine_first(s_mdy).combine_first(s_mdy2).combine_first(s_mdy3).combine_first(s_gen)
        
        df = df.dropna(subset=["Date"])
        # Filter out 1970 Unix epoch or 1900 Excel epoch artifacts caused by empty/zero cells
        df = df[df["Date"].dt.year > 2000]

    numeric_columns = ["MTTR (Hours)", "Total Monthly Hrs"]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in df.select_dtypes(include="object").columns:
        df[col] = (
            df[col].astype(str).str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})
        )

    if "Site Classification" not in df.columns:
        df["Site Classification"] = "Unknown"
    
    df["Site Classification"] = df["Site Classification"].fillna("Unknown")


    return df


# =========================================================
# VALIDATION
# =========================================================

def validate_columns(df):

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        st.info("Columns found in uploaded file: " + ", ".join(df.columns))
        st.stop()


def extract_clicked_value(pt, df, column_name):
    """Extract and validate clicked value from Plotly click event."""
    unique_vals = set(df[column_name].dropna().astype(str).unique())
    val_x = str(pt.get('x', ''))
    val_y = str(pt.get('y', ''))
    if val_x in unique_vals:
        return pt.get('x')
    if val_y in unique_vals:
        return pt.get('y')
    # Search for matching string representations
    for val in unique_vals:
        if val.lower() == val_x.lower() or val.lower() == val_y.lower():
            return val
    return pt.get('x') or pt.get('y')


def render_drillable_chart(fig, df, column_name, view_type, key):
    """Render a Plotly chart that supports interactive click-to-drill-down, with manual fallback."""
    clicked_val = None
    
    # 1. Render the chart itself (either interactive or static fallback)
    if PLOTLY_EVENTS_AVAILABLE:
        try:
            # We enforce override_height and configure the interactive key
            selected_points = plotly_events(
                fig,
                click_event=True,
                select_event=False,
                hover_event=False,
                key=f"evt_{key}"
            )
            if selected_points:
                pt = selected_points[0]
                clicked_val = extract_clicked_value(pt, df, column_name)
        except Exception:
            # Fall back to standard st.plotly_chart if click tracking fails
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    else:
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    # 2. Render a clean manual selection fallback
    unique_vals = sorted(df[column_name].dropna().unique())
    with st.expander(f"🔍 Manual {column_name} Drill Down"):
        selected_val = st.selectbox(
            f"Select {column_name} to inspect:",
            options=["-- Select --"] + unique_vals,
            key=f"sb_manual_{key}"
        )
        if selected_val != "-- Select --":
            clicked_val = selected_val

    if clicked_val is not None:
        # Prevent appending duplicates if already on stack
        stack = st.session_state.drilldown_stack
        if not stack or stack[-1].filter_val != clicked_val or stack[-1].filter_col != column_name:
            st.session_state.drilldown_stack.append(NavigationState(view_type, column_name, clicked_val))
            st.rerun()


def render_breadcrumbs() -> None:
    """Render a breadcrumb trail as a styled HTML bar — no nested columns."""
    stack = st.session_state.drilldown_stack
    if not stack:
        return

    # Build the breadcrumb HTML segments
    crumb_html = f'<span style="color:{THEME["text_muted"]}; font-size:0.9rem; font-weight:600;">🏠 Dashboard</span>'
    for state in stack:
        label = f"{state.filter_col}: {state.filter_val}"
        crumb_html += (
            f' <span style="color:{THEME["electric"]}; margin:0 6px;">➔</span> '
            f'<span style="'
            f'color:var(--text-color); font-size:0.9rem; font-weight:600; '
            f'background:rgba(59,130,246,0.15); padding:3px 10px; border-radius:6px;'
            f'">{label}</span>'
        )

    st.markdown(
        f'<div style="'
        f'padding:8px 14px; border-radius:10px; '
        f'background:{THEME["surface"]}; '
        f'border:1px solid {THEME["border"]}; '
        f'margin-bottom:4px; line-height:2;'
        f'">{crumb_html}</div>',
        unsafe_allow_html=True,
    )


def render_navigation_controls() -> None:
    """Render Back / Home buttons above the breadcrumb bar."""
    if not st.session_state.drilldown_stack:
        return

    btn_col1, btn_col2, _ = st.columns([1, 1, 7])
    with btn_col1:
        if st.button("🔙 Back", use_container_width=True, key="nav_back_btn"):
            st.session_state.drilldown_stack.pop()
            st.rerun()
    with btn_col2:
        if st.button("🏠 Home", use_container_width=True, key="nav_home_btn"):
            st.session_state.drilldown_stack = []
            st.rerun()

    render_breadcrumbs()
    st.markdown("---")


def render_category_drilldown(df, state):
    """Render the detail view for a specific category (Bucket, Region, County, etc.)."""
    val = state.filter_val
    col = state.filter_col
    
    # The dataset has already been filtered by the stack items
    st.markdown(f"## 📊 Category Analysis: `{val}` ({col})")
    
    # Calculations
    total_incidents = len(df)
    total_downtime = df["MTTR (Hours)"].sum()
    avg_mttr = df["MTTR (Hours)"].mean()
    total_sites = df["Site Name"].nunique()
    
    # KPIs cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚡ Total Incidents", f"{total_incidents:,}")
    c2.metric("🗼 Unique Sites Impacted", f"{total_sites:,}")
    c3.metric("⏱ Total Downtime", f"{total_downtime:,.1f} hrs")
    c4.metric("📈 Average MTTR", f"{avg_mttr:,.2f} hrs")
    
    # Top affected sites under this category (Plotly chart)
    section_title(f"Top Impacted Sites under {col}: {val}")
    site_data = df.groupby("Site Name")["MTTR (Hours)"].sum().reset_index()
    site_data = site_data.sort_values("MTTR (Hours)", ascending=False).head(15)
    
    fig = px.bar(
        site_data, x="MTTR (Hours)", y="Site Name", orientation="h",
        color="MTTR (Hours)", text="MTTR (Hours)",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=f"Top Sites by Total MTTR under {col}: {val}"
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    fig = polish_figure(format_bar_text(style_figure(fig, height=400)))
    
    render_drillable_chart(fig, df, "Site Name", "site_details", key=f"cat_site_{col}_{val}")
    
    # Site Table breakdown
    section_title("Detailed Site Performance Grid")
    site_groups = df.groupby("Site Name")
    
    site_table_data = []
    for site_name, group in site_groups:
        region_val = group["REGION"].iloc[0] if "REGION" in group.columns else "N/A"
        county_val = group["County"].iloc[0] if "County" in group.columns else "N/A"
        cat_val = group["Failure Category"].iloc[0] if "Failure Category" in group.columns else "N/A"
        bucket_val = group["Bucket"].iloc[0] if "Bucket" in group.columns else "N/A"
        incidents = len(group)
        downtime = group["MTTR (Hours)"].sum()
        avg_m = group["MTTR (Hours)"].mean()
        max_m = group["MTTR (Hours)"].max()
        min_m = group["MTTR (Hours)"].min()
        last_fail = group["Date"].max().strftime("%Y-%m-%d %H:%M") if "Date" in group.columns else "N/A"
        
        site_table_data.append({
            "Site Name": site_name,
            "Region": region_val,
            "County": county_val,
            "Failure Category": cat_val,
            "Failure Bucket": bucket_val,
            "Number of Incidents": incidents,
            "Total Downtime (Hrs)": round(downtime, 2),
            "Average MTTR (Hrs)": round(avg_m, 2),
            "Maximum MTTR (Hrs)": round(max_m, 2),
            "Minimum MTTR (Hrs)": round(min_m, 2),
            "Last Failure Date": last_fail
        })
    
    site_table_df = pd.DataFrame(site_table_data)
    
    if not site_table_df.empty:
        site_table_df = site_table_df.sort_values("Total Downtime (Hrs)", ascending=False)
        st.dataframe(site_table_df, use_container_width=True, hide_index=True)
    else:
        st.info("No sites found under this classification.")
        
    # Export Section
    st.markdown("#### 📁 Export Category Dataset")
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        excel_data = generate_excel(df)
        st.download_button(
            label="⬇ Download Excel Report",
            data=excel_data,
            file_name=f"category_{col}_{val}_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_excel_{col}_{val}"
        )
    with c2:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download CSV",
            data=csv_data,
            file_name=f"category_{col}_{val}_report.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"dl_csv_{col}_{val}"
        )


def render_site_drilldown(df, state):
    """Render the outage timeline and failure history for a single site."""
    site_name = state.filter_val
    
    st.markdown(f"## 🗼 Site Outage Profile: `{site_name}`")
    
    # Calculations
    total_incidents = len(df)
    total_downtime = df["MTTR (Hours)"].sum()
    avg_mttr = df["MTTR (Hours)"].mean()
    
    # SLA calculations
    from analytics import SLATracker
    sla_stats = SLATracker.calculate_sla_compliance(df, mttr_col="MTTR (Hours)", sla_threshold=24.0)
    compliance_rate = sla_stats["compliance_rate"]
    
    # Display KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚡ Total Incidents", f"{total_incidents:,}")
    c2.metric("⏱ Total Downtime", f"{total_downtime:,.1f} hrs")
    c3.metric("📈 Average MTTR", f"{avg_mttr:,.2f} hrs")
    c4.metric("🚨 SLA Compliance (<24h)", f"{compliance_rate:.1f}%", delta=f"{sla_stats['breaches']} breaches", delta_color="inverse")
    
    # Chronological timeline scatter plot
    section_title("Chronological Outage History")
    hover_cols = ["Status"]
    if "Source of Power" in df.columns:
        hover_cols.append("Source of Power")
    if "Alarm Type" in df.columns:
        hover_cols.append("Alarm Type")
        
    fig = px.scatter(
        df, x="Date", y="MTTR (Hours)", color="Bucket",
        size="MTTR (Hours)", hover_data=hover_cols,
        color_discrete_sequence=CHART_PALETTE,
        title=f"Outage Timelines for Site {site_name}"
    )
    fig = polish_figure(style_figure(fig, height=400))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    
    # Historical record grid
    section_title("Full Outage History Records")
    show_cols = ["Date", "REGION", "Bucket", "MTTR (Hours)", "Status"]
    for extra_col in ["County", "Vendor", "Alarm Type", "Source of Power", "Failure Category"]:
        if extra_col in df.columns:
            show_cols.append(extra_col)
            
    site_history_df = df[show_cols].sort_values("Date", ascending=False)
    st.dataframe(site_history_df, use_container_width=True, hide_index=True)
    
    # Export Section
    st.markdown("#### 📁 Export Site History")
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        excel_data = generate_excel(df)
        st.download_button(
            label="⬇ Download Excel Report",
            data=excel_data,
            file_name=f"site_{site_name}_history.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_excel_site_{site_name}"
        )
    with c2:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download CSV",
            data=csv_data,
            file_name=f"site_{site_name}_history.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"dl_csv_site_{site_name}"
        )


def render_data_audit(df, filtered_df) -> None:
    """Mathematical reconciler and schema validator."""
    with st.expander("🔍 System Audit & Mathematical Reconciler", expanded=False):
        st.markdown("### 📊 Database & Calculation Reconciler")
        
        # 1. Row counts
        total_rows = len(df)
        filtered_rows = len(filtered_df)
        pct_filtered = (filtered_rows / total_rows * 100) if total_rows > 0 else 0
        
        # 2. Missing data audit
        missing_counts = df.isnull().sum()
        required_missing = {col: missing_counts[col] for col in REQUIRED_COLUMNS if col in missing_counts}
        
        # 3. Duplicate checks
        duplicate_rows = df.duplicated().sum()
        
        # 4. Reconciler
        raw_total_mttr = filtered_df["MTTR (Hours)"].sum()
        bucket_sums = filtered_df.groupby("Bucket")["MTTR (Hours)"].sum()
        aggregated_total_mttr = bucket_sums.sum()
        
        discrepancy = abs(raw_total_mttr - aggregated_total_mttr)
        reconciled = discrepancy < 0.001
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Data Coverage**")
            st.write(f"Total Database Rows: {total_rows:,}")
            st.write(f"Active Filtered Rows: {filtered_rows:,} ({pct_filtered:.1f}%)")
            st.write(f"Duplicate Records: {duplicate_rows:,}")
        with c2:
            st.markdown(f"**Required Column Gaps (Nulls)**")
            has_missing = False
            for col, count in required_missing.items():
                if count > 0:
                    st.write(f"❌ {col}: {count:,} missing")
                    has_missing = True
            if not has_missing:
                st.write("✅ All required fields have 100% data presence.")
        with c3:
            st.markdown(f"**MTTR Calculation Reconciler**")
            st.write(f"Raw MTTR Sum: `{raw_total_mttr:,.4f}` hrs")
            st.write(f"Bucket Group Sum: `{aggregated_total_mttr:,.4f}` hrs")
            if reconciled:
                st.markdown("### ✅ **Reconciled**")
                st.caption(f"Zero mathematical discrepancy (diff: {discrepancy:,.6f} hrs)")
            else:
                st.markdown("### ⚠️ **Discrepancy Detected!**")
                st.write(f"Difference: `{discrepancy:,.6f}` hrs")


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


def apply_filters(df, show_brand=True):

    if show_brand:
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
    if st.sidebar.button("↻  Reset All Filters", use_container_width=True, key="reset_btn"):
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
        selected_sites        = multiselect_filter("Site Name", "Site Name", df, key="flt_site")
        
        has_site_class = not (df["Site Classification"].nunique() == 1 and df["Site Classification"].iloc[0] == "Unknown")
        if has_site_class:
            selected_classes = multiselect_filter("Site Classification", "Site Classification", df, key="flt_class")
        else:
            selected_classes = df["Site Classification"].unique().tolist()
            
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

    # --- Dynamic Custom Fields ---
    selected_dynamic = {}
    present_dynamic = [c for c in ["County", "Vendor", "Alarm Type", "Failure Category"] if c in df.columns]
    if present_dynamic:
        st.sidebar.markdown('<div class="sb-section">📦 Custom Fields</div>', unsafe_allow_html=True)
        with st.sidebar.expander("Attributes", expanded=False):
            for col in present_dynamic:
                selected_dynamic[col] = multiselect_filter(col, col, df, key=f"flt_{col.lower().replace(' ', '_')}")

    # Apply base mask
    mask = (
        (df["Date"].dt.date >= start_date)
        & (df["Date"].dt.date <= end_date)
        & (df["REGION"].isin(selected_regions))
        & (df["SITE TYPE"].isin(selected_site_types))
        & (df["Site Name"].isin(selected_sites))
        & (df["Site Classification"].isin(selected_classes))
        & (df["Visibility"].isin(selected_visibility))
        & (df["Bucket"].isin(selected_buckets))
        & (df["MTTR (Hours)"] >= mttr_range[0])
        & (df["MTTR (Hours)"] <= mttr_range[1])
    )

    # Apply dynamic masks
    for col, vals in selected_dynamic.items():
        mask = mask & (df[col].isin(vals))

    filtered_df = df[mask].copy()

    # Active filter chips
    chips = []
    if len(selected_regions) < df["REGION"].nunique():
        chips.append(f"{len(selected_regions)} regions")
    if len(selected_buckets) < df["Bucket"].nunique():
        chips.append(f"{len(selected_buckets)} buckets")
    if mttr_range != (mttr_min, mttr_max):
        chips.append(f"MTTR {mttr_range[0]:.1f}–{mttr_range[1]:.1f}h")
    for col, vals in selected_dynamic.items():
        if len(vals) < df[col].nunique():
            chips.append(f"{len(vals)} {col.lower()}s")

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

    return filtered_df, start_date, end_date


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
        markers=True,
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
    fig.add_hline(
        y=2.5, 
        line_dash="dash", 
        line_color="red", 
        annotation_text="Threshold (2.5 hrs)", 
        annotation_position="bottom right"
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


def chart_failures_by_bucket(df):
    data = df.groupby("Bucket").size().reset_index(name="Failure Count").sort_values("Failure Count", ascending=True)
    fig = px.bar(
        data, x="Failure Count", y="Bucket", orientation="h",
        color="Failure Count", text="Failure Count",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title="Total Failures by Bucket",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    return polish_figure(style_figure(fig))


def chart_failures_by_region(df):
    data = df.groupby("REGION").size().reset_index(name="Failure Count")
    fig = px.pie(
        data, names="REGION", values="Failure Count",
        color_discrete_sequence=CHART_PALETTE,
        title="Failures per Region (Percentage)",
        hole=0.4
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return polish_figure(style_figure(fig))


def chart_mttr_visibility_sitetype(df):
    if "Visibility" not in df.columns or "SITE TYPE" not in df.columns:
        return go.Figure()
    data = df.groupby(["SITE TYPE", "Visibility"])["MTTR (Hours)"].mean().reset_index()
    fig = px.bar(
        data, x="SITE TYPE", y="MTTR (Hours)", color="Visibility", barmode="group",
        color_discrete_sequence=CHART_PALETTE,
        title="Average MTTR by Site Type & Visibility",
        text="MTTR (Hours)",
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    return polish_figure(style_figure(fig))


def chart_site_failures_per_day(df, top_n=15):
    top_sites = df.groupby("Site Name").size().nlargest(top_n).index
    filtered = df[df["Site Name"].isin(top_sites)]
    
    data = filtered.groupby([filtered["Date"].dt.date, "Site Name"]).size().reset_index(name="Failure Count")
    data["Date"] = pd.to_datetime(data["Date"])
    
    fig = px.bar(
        data, x="Date", y="Failure Count", color="Site Name",
        title=f"Daily Failures for Top {top_n} Sites",
        color_discrete_sequence=CHART_PALETTE,
        barmode="stack",
    )
    return polish_figure(style_figure(fig))


def chart_sla_breaches(df, start_date=None, end_date=None):
    if df.empty:
        return polish_figure(style_figure(px.line(title="No data available for SLA tracking")))

    if "SITE TYPE" in df.columns:
        # Group by Date and SITE TYPE
        data = df.groupby([df["Date"].dt.date, "SITE TYPE"])["MTTR (Hours)"].sum().reset_index()
        data["Date"] = pd.to_datetime(data["Date"])
        
        sdate = pd.to_datetime(start_date) if start_date else data["Date"].min()
        edate = pd.to_datetime(end_date) if end_date else data["Date"].max()
        all_dates = pd.date_range(start=sdate, end=edate, freq="D")
        all_types = df["SITE TYPE"].dropna().unique()
        
        idx = pd.MultiIndex.from_product([all_dates, all_types], names=["Date", "SITE TYPE"])
        full_grid = pd.DataFrame(index=idx).reset_index()
        
        data = pd.merge(full_grid, data, on=["Date", "SITE TYPE"], how="left").fillna({"MTTR (Hours)": 0})
        
        def calculate_uptime(row):
            stype = str(row["SITE TYPE"]).strip().upper()
            if stype == "DG":
                total_hours = 306 * 24
            elif stype == "NON-DG":
                total_hours = 243 * 24
            else:
                # Fallback for unexpected site types
                total_hours = 243 * 24 
            
            return 100 - (row["MTTR (Hours)"] / total_hours) * 100
            
        data["Uptime (%)"] = data.apply(calculate_uptime, axis=1)
        
        fig = px.line(
            data, x="Date", y="Uptime (%)", color="SITE TYPE", markers=True,
            title="Daily Uptime by Site Type vs 99.97% SLA Target",
            color_discrete_sequence=CHART_PALETTE,
        )
    else:
        data = df.groupby(df["Date"].dt.date)["MTTR (Hours)"].sum().reset_index()
        data["Date"] = pd.to_datetime(data["Date"])
        
        sdate = pd.to_datetime(start_date) if start_date else data["Date"].min()
        edate = pd.to_datetime(end_date) if end_date else data["Date"].max()
        all_dates = pd.DataFrame({"Date": pd.date_range(start=sdate, end=edate, freq="D")})
        
        data = pd.merge(all_dates, data, on="Date", how="left").fillna({"MTTR (Hours)": 0})
        
        # 549 sites * 24 hours = 13176 total hours per day
        data["Uptime (%)"] = 100 - (data["MTTR (Hours)"] / 13176) * 100
        
        fig = px.line(
            data, x="Date", y="Uptime (%)", markers=True,
            title="Daily Uptime vs 99.97% SLA Target",
            color_discrete_sequence=[THEME.get("electric", "#0ea5e9")],
        )
        
    fig.add_hline(
        y=99.97,
        line_dash="dash",
        line_color="red",
        annotation_text="SLA Target (99.97%)",
        annotation_position="bottom right",
    )
    return polish_figure(style_figure(fig))


# =========================================================
# EXCEL EXPORT
# =========================================================

def generate_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Filtered Data")
    return output.getvalue()


# =========================================================
# PDF EXPORT
# =========================================================

def generate_pdf_report(df, start_date, end_date):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def add_chart(pdf_obj, fig, title):
        # Prevent overlapping by placing legend on the right with generous margins
        fig.update_layout(
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=60, r=200, t=60, b=140)
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.write_image(tmp.name, format="png", engine="kaleido", width=1400, height=550, scale=2)
            with pdf_obj.unbreakable():
                pdf_obj.set_font("helvetica", style="B", size=12)
                pdf_obj.cell(0, 10, title, align="C", new_x="LMARGIN", new_y="NEXT")
                pdf_obj.image(tmp.name, x=10, w=190)
                pdf_obj.ln(5)
        os.unlink(tmp.name)
        
    def add_section(pdf_obj, section_title):
        pdf_obj.add_page()
        pdf_obj.set_font("helvetica", style="B", size=18)
        pdf_obj.set_text_color(14, 165, 233)
        pdf_obj.cell(0, 15, section_title, align="L", new_x="LMARGIN", new_y="NEXT")
        pdf_obj.set_text_color(0, 0, 0)
        pdf_obj.ln(5)
        
    # Build charts
    add_section(pdf, "1. Executive Overview")
    add_chart(pdf, chart_daily_failures(df), "Daily Failures Trend")
    add_chart(pdf, chart_daily_activity(df), "Daily Failure Activity")
    add_chart(pdf, chart_daily_mttr(df), "Daily MTTR Trend")
    add_chart(pdf, chart_failures_by_bucket(df), "Failures by Bucket")
    add_chart(pdf, chart_mttr_by_bucket(df), "MTTR by Bucket")
    add_chart(pdf, chart_mttr_visibility_sitetype(df), "MTTR by Visibility & Site Type")
    
    add_section(pdf, "2. Regional Analysis")
    add_chart(pdf, chart_failures_by_region(df), "Failures by Region")
    add_chart(pdf, chart_region_mttr(df), "MTTR by Region")
    add_chart(pdf, chart_region_heatmap(df), "Regional Heatmap")
    
    add_section(pdf, "3. Site Performance")
    add_chart(pdf, chart_site_failures_per_day(df, 15), "Top 15 Sites Daily Failures")
    add_chart(pdf, chart_site_mttr(df, 15), "Top 15 Sites by MTTR")
    add_chart(pdf, chart_site_failures(df, 15), "Top 15 Sites by Failure Count")
    
    add_section(pdf, "4. SLA Compliance Tracking")
    add_chart(pdf, chart_sla_breaches(df, start_date, end_date), "Daily Uptime vs 99.97% SLA Target")
    
    present_dynamic = [c for c in ["County", "Vendor", "Alarm Type", "Failure Category"] if c in df.columns]
    if present_dynamic:
        add_section(pdf, "5. Custom Attributes Analysis")
        for col in present_dynamic:
            data = aggregate_sum(df, col)
            fig = px.bar(
                data, x=col, y="MTTR (Hours)", color=col,
                text="MTTR (Hours)",
                color_discrete_sequence=CHART_PALETTE,
                title=f"Total MTTR by {col}"
            )
            fig.update_layout(showlegend=False)
            fig = polish_figure(format_bar_text(style_figure(fig)))
            add_chart(pdf, fig, f"Total MTTR by {col}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.unlink(tmp.name)
    
    return pdf_bytes


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

    # Initialize navigation stack
    if "drilldown_stack" not in st.session_state:
        st.session_state.drilldown_stack = []

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

    # Check and reset stack if new file is uploaded
    if st.session_state.get("last_uploaded_file") != uploaded_file.name:
        st.session_state.last_uploaded_file = uploaded_file.name
        st.session_state.drilldown_stack = []

    with st.spinner("Loading and validating telecom dataset…"):
        df = load_data(uploaded_file)
        validate_columns(df)

    if df.empty:
        render_hero(None)
        st.warning("No valid data found in the uploaded file.")
        return

    # Apply filters dynamically (using unified function, no brand header duplicate)
    filtered_df, start_date, end_date = apply_filters(df, show_brand=False)

    if filtered_df.empty:
        render_hero(None)
        st.warning("No data matches the current filters. Try expanding selections.")
        return

    # Navigation Routing Logic
    if st.session_state.drilldown_stack:
        # Render back and breadcrumb controls
        render_navigation_controls()
        
        # Calculate active dataframe sequentially
        active_df = filtered_df.copy()
        for state in st.session_state.drilldown_stack[:-1]:
            active_df = active_df[active_df[state.filter_col].astype(str) == str(state.filter_val)]
            
        current_state = st.session_state.drilldown_stack[-1]
        subset_df = active_df[active_df[current_state.filter_col].astype(str) == str(current_state.filter_val)]
        
        # Switch to detailed views
        if current_state.view_type == "category_details":
            render_category_drilldown(subset_df, current_state)
        elif current_state.view_type == "site_details":
            render_site_drilldown(subset_df, current_state)
            
        # Global audit at the bottom of detailed views too
        render_data_audit(df, filtered_df)
        return

    # Hero + KPIs + Exec Summary (Dashboard View)
    render_hero(filtered_df)
    render_kpis(filtered_df)
    render_executive_summary(filtered_df)

    # Dynamic Tabs Setup
    tab_list = ["📊  Overview", "🌍  Regional Analysis", "🗼  Site Performance", "📈  SLA Breaches"]
    has_dynamic_charts = any(col in filtered_df.columns for col in ["County", "Vendor", "Alarm Type", "Failure Category"])
    if has_dynamic_charts:
        tab_list.append("📦  Attribute Analysis")
    tab_list.append("📁  Data Export")

    tabs = st.tabs(tab_list)

    with tabs[0]:
        section_title("Failure Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            fig = chart_failures_by_bucket(filtered_df)
            render_drillable_chart(fig, filtered_df, "Bucket", "category_details", key="overview_failures_bucket")
        with col2:
            fig = chart_mttr_by_bucket(filtered_df)
            render_drillable_chart(fig, filtered_df, "Bucket", "category_details", key="overview_mttr_bucket")

        section_title("MTTR by Attributes")
        if "Visibility" in filtered_df.columns and "SITE TYPE" in filtered_df.columns:
            render_chart(chart_mttr_visibility_sitetype(filtered_df))

        section_title("Operational Timeline")
        col3, col4 = st.columns(2)
        with col3:
            render_chart(chart_daily_failures(filtered_df))
        with col4:
            render_chart(chart_daily_activity(filtered_df))
        render_chart(chart_daily_mttr(filtered_df))

    with tabs[1]:
        section_title("Regional Health Overview")
        col1, col2 = st.columns(2)
        with col1:
            fig = chart_failures_by_region(filtered_df)
            render_drillable_chart(fig, filtered_df, "REGION", "category_details", key="regional_failures_region")
        with col2:
            fig = chart_region_mttr(filtered_df)
            render_drillable_chart(fig, filtered_df, "REGION", "category_details", key="regional_mttr_region")
            
        st.markdown("---")
        render_chart(chart_region_heatmap(filtered_df))

    with tabs[2]:
        section_title("Site Performance Drilldown")
        top_n = st.slider("Sites to Display", min_value=5, max_value=50, value=15)
        
        render_chart(chart_site_failures_per_day(filtered_df, top_n))
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            fig = chart_site_mttr(filtered_df, top_n)
            render_drillable_chart(fig, filtered_df, "Site Name", "site_details", key="site_mttr")
        with col2:
            fig = chart_site_failures(filtered_df, top_n)
            render_drillable_chart(fig, filtered_df, "Site Name", "site_details", key="site_failures")

    with tabs[3]:
        section_title("SLA Compliance Tracking")
        st.info("Tracking daily network uptime against the 99.97% SLA target. Assumes 13,176 total possible hours per day (549 sites × 24 hours).")
        render_chart(chart_sla_breaches(filtered_df, start_date, end_date))

    if has_dynamic_charts:
        with tabs[tab_list.index("📦  Attribute Analysis")]:
            section_title("Custom Attributes Performance")
            cols_to_render = [col for col in ["County", "Vendor", "Alarm Type", "Failure Category"] if col in filtered_df.columns]
            
            for col in cols_to_render:
                st.markdown(f"### {col} Analysis")
                data = aggregate_sum(filtered_df, col)
                fig = px.bar(
                    data, x=col, y="MTTR (Hours)", color=col,
                    text="MTTR (Hours)",
                    color_discrete_sequence=CHART_PALETTE,
                    title=f"Total MTTR by {col}"
                )
                fig.update_layout(showlegend=False)
                fig = polish_figure(format_bar_text(style_figure(fig)))
                
                render_drillable_chart(fig, filtered_df, col, "category_details", key=f"dynamic_chart_{col.lower().replace(' ', '_')}")

    with tabs[tab_list.index("📁  Data Export")]:
        section_title("Filtered Dataset Preview")
        st.caption(f"Showing first 1,000 of {len(filtered_df):,} filtered records.")
        st.dataframe(filtered_df.head(1000), use_container_width=True, hide_index=True)

        st.markdown("####  ")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            excel_data = generate_excel(filtered_df)
            st.download_button(
                label="⬇  Download Excel Report",
                data=excel_data,
                file_name="network_failure_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_main_excel"
            )
        with c2:
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇  Download CSV",
                data=csv_data,
                file_name="network_failure_analysis.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_main_csv"
            )
        with c3:
            df_hash = pd.util.hash_pandas_object(filtered_df).sum()
            
            if st.button("📄 Prepare PDF Report", use_container_width=True):
                with st.spinner("Rendering high-res charts to PDF... (Approx. 5-10s)"):
                    st.session_state.pdf_bytes = generate_pdf_report(filtered_df, start_date, end_date)
                    st.session_state.pdf_df_hash = df_hash
                    
            if st.session_state.get("pdf_bytes") and st.session_state.get("pdf_df_hash") == df_hash:
                st.download_button(
                    label="⬇  Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name="NOC_Executive_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_main_pdf"
                )

    # Render system audit reconciler block globally at the bottom
    render_data_audit(df, filtered_df)


if __name__ == "__main__":
    main()
