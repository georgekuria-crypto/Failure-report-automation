"""Advanced visualization functions for enhanced charts."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, Dict, List, Tuple

# Optional imports for mapping features
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from utils import get_region_coordinates, format_duration


SEQUENTIAL_SCALE = ["#312e81", "#4f46e5", "#06b6d4", "#22d3ee"]
DISCRETE_COLORS = [
    "#6366f1",  # Indigo
    "#0ea5e9",  # Sky Blue
    "#10b981",  # Emerald Green
    "#f59e0b",  # Amber/Yellow
    "#ef4444",  # Coral Red
    "#8b5cf6",  # Purple
    "#ec4899",  # Pink
]


def is_dark_theme() -> bool:
    """Check if dark theme is active."""
    return st.get_option("theme.base") == "dark"


def chart_template() -> str:
    """Get appropriate chart template for current theme."""
    return "plotly_dark" if is_dark_theme() else "plotly_white"


def chart_text_color() -> str:
    """Get text color for current theme."""
    return "#f8fafc" if is_dark_theme() else "#0f172a"


def chart_grid_color() -> str:
    """Get grid color for current theme."""
    return "rgba(226, 232, 240, 0.20)" if is_dark_theme() else "#e5e7eb"


CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def style_figure(
    fig: go.Figure,
    height: int = 430,
    margin: Optional[Dict] = None,
    showgrid: bool = True,
    legend: Optional[Dict] = None,
    title: Optional[str] = None,
) -> go.Figure:
    """Apply consistent visual style to every chart."""
    template = chart_template()
    
    if margin is None:
        margin = dict(l=65, r=35, t=85, b=65)
    
    if legend is None:
        legend = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    
    fig.update_layout(
        template=template,
        height=height,
        margin=margin,
        font=dict(
            family="Inter, system-ui, -apple-system, sans-serif",
            size=12,
            color=chart_text_color()
        ),
        title=dict(
            text=title if title else fig.layout.title.text if hasattr(fig.layout.title, 'text') else "",
            font=dict(size=15, color=chart_text_color()),
            x=0.01,
            xanchor="left"
        ),
        legend=legend,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="#1f2937" if is_dark_theme() else "#ffffff",
            font=dict(
                family="Inter, system-ui, -apple-system, sans-serif",
                color="#f9fafb" if is_dark_theme() else "#111827",
                size=12
            ),
            bordercolor=chart_grid_color(),
        ),
        coloraxis_colorbar=dict(
            title_font=dict(
                family="Inter, system-ui, -apple-system, sans-serif",
                color=chart_text_color()
            ),
            tickfont=dict(
                family="Inter, system-ui, -apple-system, sans-serif",
                color=chart_text_color()
            )
        ),
    )
    
    grid_color = chart_grid_color()
    fig.update_xaxes(showgrid=showgrid, gridcolor=grid_color, zeroline=False)
    fig.update_yaxes(showgrid=showgrid, gridcolor=grid_color, zeroline=False)
    
    return fig


def format_bar_text(fig: go.Figure, decimals: int = 2) -> go.Figure:
    """Format bar text with proper formatting."""
    fig.update_traces(
        texttemplate=f"%{{text:,.{decimals}f}}",
        textposition="auto",
        cliponaxis=False,
    )
    return fig


def render_chart(fig: go.Figure, **kwargs):
    """Render chart with consistent configuration."""
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=CHART_CONFIG,
        **kwargs,
    )


def create_kpi_gauge(
    value: float,
    title: str,
    min_val: float = 0,
    max_val: float = 100,
    unit: str = "",
    threshold_warning: Optional[float] = None,
    threshold_critical: Optional[float] = None,
) -> go.Figure:
    """Create a telecom-style KPI gauge."""
    
    # Determine color based on thresholds
    if threshold_critical and value >= threshold_critical:
        gauge_color = "#ef4444"  # Red
    elif threshold_warning and value >= threshold_warning:
        gauge_color = "#f59e0b"  # Amber
    else:
        gauge_color = "#10b981"  # Green
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title=dict(text=title, font=dict(size=14, color=chart_text_color())),
        number=dict(
            suffix=unit,
            font=dict(size=20, color=chart_text_color()),
            valueformat=".1f"
        ),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickcolor=chart_text_color()),
            bar=dict(color=gauge_color, thickness=0.25),
            steps=[
                dict(range=[min_val, max_val * 0.33], color="rgba(16, 185, 129, 0.1)"),
                dict(range=[max_val * 0.33, max_val * 0.67], color="rgba(245, 158, 11, 0.1)"),
                dict(range=[max_val * 0.67, max_val], color="rgba(239, 68, 68, 0.1)"),
            ],
            threshold=dict(
                line=dict(color="red", width=4),
                thickness=0.75,
                value=max_val * 0.9
            )
        )
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(family="Inter, system-ui, -apple-system, sans-serif", color=chart_text_color()),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    
    return fig


def create_anomaly_chart(
    df: pd.DataFrame,
    anomalies: pd.Series,
    date_col: str = "Date",
    value_col: str = "MTTR (Hours)",
) -> go.Figure:
    """Create chart highlighting anomalies."""
    daily_data = df.groupby(df[date_col].dt.date).agg({value_col: "mean"}).reset_index()
    daily_data.columns = ["Date", "Value"]
    daily_data["Date"] = pd.to_datetime(daily_data["Date"])
    daily_data = daily_data.sort_values("Date")
    
    fig = go.Figure()
    
    # Normal points
    normal_mask = ~anomalies.reindex(range(len(daily_data)), fill_value=False).values
    fig.add_scatter(
        x=daily_data.loc[normal_mask, "Date"],
        y=daily_data.loc[normal_mask, "Value"],
        mode="markers+lines",
        name="Normal",
        marker=dict(color="#6366f1", size=8),
        line=dict(color="#6366f1", width=2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>"
    )
    
    # Anomalies
    anomaly_mask = anomalies.reindex(range(len(daily_data)), fill_value=False).values
    fig.add_scatter(
        x=daily_data.loc[anomaly_mask, "Date"],
        y=daily_data.loc[anomaly_mask, "Value"],
        mode="markers",
        name="Anomaly detected",
        marker=dict(color="#ef4444", size=12, symbol="diamond"),
        hovertemplate="<b>⚠️ ANOMALY</b><br>%{x|%d %b %Y}<br>MTTR: %{y:,.2f} hrs<extra></extra>"
    )
    
    fig.update_layout(
        title="MTTR Anomaly Detection",
        xaxis_title="Date",
        yaxis_title="Average MTTR (Hours)",
        hovermode="x unified",
        height=450,
        margin=dict(l=65, r=35, t=85, b=65),
    )
    
    return style_figure(fig)


def create_outage_hour_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create heatmap of outages by hour and day of week."""
    df_copy = df.copy()
    df_copy["hour"] = pd.to_datetime(df_copy["Date"]).dt.hour
    df_copy["day_of_week"] = pd.to_datetime(df_copy["Date"]).dt.day_name()
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    heatmap_data = df_copy.pivot_table(
        index="day_of_week",
        columns="hour",
        values="MTTR (Hours)",
        aggfunc="sum",
        fill_value=0
    )
    
    heatmap_data = heatmap_data.reindex([day for day in day_order if day in heatmap_data.index])
    
    fig = px.imshow(
        heatmap_data,
        color_continuous_scale=SEQUENTIAL_SCALE,
        aspect="auto",
        title="Outage Hours Heatmap: Day of Week vs Hour of Day",
        labels=dict(x="Hour of Day", y="Day of Week", color="MTTR Hours"),
        text_auto=".0f",
    )
    
    fig.update_layout(
        height=450,
        margin=dict(l=100, r=80, t=85, b=65),
    )
    
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Hour: %{x}:00<br>MTTR: %{z:,.2f} hrs<extra></extra>"
    )
    
    return style_figure(fig, showgrid=False)


def create_kenya_map(df: pd.DataFrame, metric: str = "failure_count") -> Optional[folium.Map]:
    """Create interactive Kenya regional outage map."""
    
    if not FOLIUM_AVAILABLE:
        return None
    
    # Region aggregations
    if metric == "failure_count":
        region_data = df.groupby("REGION").size().reset_index(name="value")
    elif metric == "total_mttr":
        region_data = df.groupby("REGION").agg({"MTTR (Hours)": "sum"}).reset_index()
        region_data.columns = ["REGION", "value"]
    else:
        region_data = df.groupby("REGION").agg({"MTTR (Hours)": "mean"}).reset_index()
        region_data.columns = ["REGION", "value"]
    
    # Normalize for color intensity
    max_val = region_data["value"].max()
    region_data["color_intensity"] = region_data["value"] / max_val
    
    # Get coordinates
    coordinates = get_region_coordinates()
    
    # Create map centered on Kenya
    m = folium.Map(
        location=[-0.0236, 37.9062],
        zoom_start=6,
        tiles="CartoDB positron"
    )
    
    # Add markers for each region
    for _, row in region_data.iterrows():
        region = row["REGION"]
        value = row["value"]
        intensity = row["color_intensity"]
        
        if region in coordinates:
            lat, lon = coordinates[region]
            
            # Color intensity based on value
            color = f"hsl(0, 100%, {100 - intensity * 60}%)"  # Red shades
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=10 + intensity * 20,
                popup=f"<b>{region}</b><br>{metric}: {value:.1f}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2,
                tooltip=f"{region}: {value:.1f}"
            ).add_to(m)
    
    return m


def create_sla_breach_chart(
    breaches_df: pd.DataFrame,
    total_records: int,
    sla_threshold: float = 24.0
) -> go.Figure:
    """Create visualization of SLA breaches."""
    
    if breaches_df.empty:
        # Create empty state chart
        fig = go.Figure()
        fig.add_annotation(
            text="No SLA breaches detected! ✓",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="#10b981")
        )
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
        return fig
    
    fig = px.bar(
        breaches_df.head(10),
        x="MTTR (Hours)",
        y="Site Name",
        color="breach_amount",
        color_continuous_scale=["#f59e0b", "#ef4444"],
        orientation="h",
        title="Top SLA Breaches (>24h target)",
        labels={"breach_amount": "Breach Amount (hours)"},
        hover_data={"MTTR (Hours)": ":.2f", "breach_amount": ":.2f"}
    )
    
    fig.update_layout(
        height=400,
        margin=dict(l=120, r=35, t=85, b=55),
        yaxis={"categoryorder": "total ascending"}
    )
    
    fig.update_xaxes(title_text="MTTR (Hours)")
    
    return style_figure(fig)


def create_mttr_trend_forecast(
    forecast_df: pd.DataFrame,
) -> go.Figure:
    """Create MTTR trend with forecast."""
    
    actual_df = forecast_df[forecast_df["type"] == "actual"]
    forecast_df_subset = forecast_df[forecast_df["type"] == "forecast"]
    
    fig = go.Figure()
    
    # Actual data
    fig.add_scatter(
        x=actual_df["Date"],
        y=actual_df["mttr"],
        name="Actual MTTR",
        mode="lines+markers",
        line=dict(color="#6366f1", width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>MTTR: %{y:,.2f} hrs<extra></extra>"
    )
    
    # Forecast data
    if not forecast_df_subset.empty:
        fig.add_scatter(
            x=forecast_df_subset["Date"],
            y=forecast_df_subset["mttr"],
            name="Forecast",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=2, dash="dash"),
            marker=dict(size=6),
            hovertemplate="<b>📊 Forecast</b><br>%{x|%d %b %Y}<br>Predicted: %{y:,.2f} hrs<extra></extra>"
        )
    
    fig.update_layout(
        title="MTTR Trend and Forecast",
        xaxis_title="Date",
        yaxis_title="Average MTTR (Hours)",
        hovermode="x unified",
        height=450,
        margin=dict(l=65, r=35, t=85, b=65),
    )
    
    return style_figure(fig)


def create_team_performance_chart(
    team_metrics: pd.DataFrame,
    team_col: str = "Team"
) -> go.Figure:
    """Create team performance comparison chart."""
    
    if team_metrics.empty:
        fig = go.Figure()
        fig.add_annotation(text="No team data available")
        return fig
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Average MTTR", "Efficiency Score"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Average MTTR
    fig.add_trace(
        go.Bar(
            x=team_metrics[team_col],
            y=team_metrics["avg_mttr"],
            name="Avg MTTR",
            marker_color="#6366f1",
            text=team_metrics["avg_mttr"].round(1),
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Avg MTTR: %{y:,.2f} hrs<extra></extra>"
        ),
        row=1, col=1
    )
    
    # Efficiency Score
    fig.add_trace(
        go.Bar(
            x=team_metrics[team_col],
            y=team_metrics["efficiency_score"],
            name="Efficiency",
            marker_color="#10b981",
            text=team_metrics["efficiency_score"].round(1),
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>"
        ),
        row=1, col=2
    )
    
    fig.update_xaxes(title_text=team_col, row=1, col=1)
    fig.update_xaxes(title_text=team_col, row=1, col=2)
    fig.update_yaxes(title_text="Hours", row=1, col=1)
    fig.update_yaxes(title_text="Score (0-100)", row=1, col=2)
    
    fig.update_layout(
        title_text="Team Performance Metrics",
        height=450,
        margin=dict(l=65, r=35, t=85, b=65),
        showlegend=False
    )
    
    return style_figure(fig)
