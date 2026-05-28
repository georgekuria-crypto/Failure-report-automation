"""Utility functions for data processing, formatting, and styling."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional


def format_number(value: float, decimals: int = 2) -> str:
    """Format number with thousands separator and specified decimals."""
    if pd.isna(value):
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.{decimals}f}K"
    return f"{value:,.{decimals}f}"


def format_duration(hours: float) -> str:
    """Convert hours to readable duration format (Xd Yh Zm)."""
    if pd.isna(hours):
        return "N/A"
    
    hours = float(hours)
    days = int(hours // 24)
    remaining_hours = int(hours % 24)
    minutes = int((hours % 1) * 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if remaining_hours > 0:
        parts.append(f"{remaining_hours}h")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "< 1m"


def calculate_percentile(data: pd.Series, percentile: float) -> float:
    """Calculate percentile safely, handling empty data."""
    if data.empty:
        return 0.0
    return float(np.percentile(data.dropna(), percentile))


def get_color_by_severity(value: float, threshold_low: float, threshold_high: float) -> str:
    """Get color based on severity thresholds."""
    if value < threshold_low:
        return "#10b981"  # Green - Good
    elif value < threshold_high:
        return "#f59e0b"  # Amber - Warning
    else:
        return "#ef4444"  # Red - Critical


def detect_outliers_iqr(data: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """Detect outliers using Interquartile Range method."""
    Q1 = data.quantile(0.25)
    Q3 = data.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - (multiplier * IQR)
    upper_bound = Q3 + (multiplier * IQR)
    return (data < lower_bound) | (data > upper_bound)


def group_small_categories(
    df: pd.DataFrame,
    column: str,
    threshold: int = 0.05,
    other_label: str = "Other"
) -> pd.DataFrame:
    """Group small categories into 'Other' for cleaner visualizations."""
    df = df.copy()
    value_counts = df[column].value_counts()
    total = len(df)
    
    small_categories = value_counts[value_counts / total < threshold].index
    df.loc[df[column].isin(small_categories), column] = other_label
    
    return df


def add_time_features(df: pd.DataFrame, date_column: str = "Date") -> pd.DataFrame:
    """Add time-based features for time-series analysis."""
    df = df.copy()
    df["Hour"] = pd.to_datetime(df[date_column]).dt.hour
    df["DayOfWeek"] = pd.to_datetime(df[date_column]).dt.day_name()
    df["WeekOfYear"] = pd.to_datetime(df[date_column]).dt.isocalendar().week
    df["Month"] = pd.to_datetime(df[date_column]).dt.month
    
    return df


def calculate_moving_average(data: pd.Series, window: int = 7) -> pd.Series:
    """Calculate moving average for trend analysis."""
    return data.rolling(window=window, center=True).mean()


def normalize_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Normalize numeric columns to 0-1 range."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[f"{col}_norm"] = (df[col] - min_val) / (max_val - min_val)
            else:
                df[f"{col}_norm"] = 0.5
    return df


def get_hour_of_day_label(hour: int) -> str:
    """Convert hour to readable label."""
    if 0 <= hour < 6:
        return "Night (00-06)"
    elif 6 <= hour < 12:
        return "Morning (06-12)"
    elif 12 <= hour < 18:
        return "Afternoon (12-18)"
    else:
        return "Evening (18-24)"


def get_region_coordinates() -> Dict[str, Tuple[float, float]]:
    """Get approximate center coordinates for Kenya regions."""
    return {
        "Nairobi": (-1.2865, 36.8172),
        "Coast": (-3.3869, 40.3519),
        "Rift Valley": (-0.5, 35.5),
        "Central": (-0.5500, 36.8333),
        "Western": (0.5, 34.5),
        "Eastern": (-2.0, 38.5),
        "North Eastern": (2.0, 39.5),
        "South Eastern": (-4.0, 39.0),
    }


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
    """Validate dataframe has required columns and valid data."""
    errors = []
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        errors.append(f"Missing columns: {', '.join(missing)}")
    
    if df.empty:
        errors.append("DataFrame is empty")
    
    return len(errors) == 0, errors


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers."""
    try:
        if denominator == 0:
            return default
        return float(numerator / denominator)
    except (TypeError, ValueError):
        return default
