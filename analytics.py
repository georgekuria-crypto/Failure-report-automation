"""Advanced analytics functions for anomaly detection, SLA tracking, and forecasting."""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
from scipy import stats


class AnomalyDetector:
    """Detect anomalies in failure data using multiple methods."""
    
    @staticmethod
    def detect_by_zscore(data: pd.Series, threshold: float = 2.5) -> pd.Series:
        """Detect anomalies using Z-score method."""
        z_scores = np.abs(stats.zscore(data.dropna()))
        return pd.Series(
            z_scores > threshold,
            index=data.dropna().index
        )
    
    @staticmethod
    def detect_by_iqr(data: pd.Series, multiplier: float = 1.5) -> pd.Series:
        """Detect anomalies using IQR method."""
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
        return (data < lower) | (data > upper)
    
    @staticmethod
    def detect_temporal_anomalies(
        df: pd.DataFrame,
        date_col: str = "Date",
        value_col: str = "MTTR (Hours)",
        window: int = 7
    ) -> pd.DataFrame:
        """Detect anomalies by comparing to rolling average."""
        df = df.copy()
        df_sorted = df.sort_values(date_col)
        
        rolling_mean = df_sorted[value_col].rolling(window=window, center=True).mean()
        rolling_std = df_sorted[value_col].rolling(window=window, center=True).std()
        
        df_sorted["rolling_mean"] = rolling_mean
        df_sorted["rolling_std"] = rolling_std
        
        df_sorted["is_anomaly"] = (
            (df_sorted[value_col] > rolling_mean + 2 * rolling_std) |
            (df_sorted[value_col] < rolling_mean - 2 * rolling_std)
        ).fillna(False)
        
        return df_sorted


class SLATracker:
    """Track and calculate SLA metrics."""
    
    @staticmethod
    def calculate_sla_compliance(
        df: pd.DataFrame,
        mttr_col: str = "MTTR (Hours)",
        sla_threshold: float = 24.0,
        severity_col: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate SLA compliance rate."""
        if df.empty:
            return {"compliance_rate": 0.0, "breaches": 0, "total": 0}
        
        total_records = len(df)
        
        if severity_col and severity_col in df.columns:
            # Different SLA thresholds by severity
            sla_thresholds = {
                "Critical": 4,
                "Major": 12,
                "Minor": 48
            }
            breaches = sum(
                df[df[severity_col] == severity][mttr_col] > sla_thresholds.get(severity, sla_threshold)
                for severity in df[severity_col].unique()
            )
        else:
            breaches = (df[mttr_col] > sla_threshold).sum()
        
        compliance_rate = ((total_records - breaches) / total_records * 100) if total_records > 0 else 0
        
        return {
            "compliance_rate": round(compliance_rate, 2),
            "breaches": int(breaches),
            "total": int(total_records),
            "breach_percentage": round((breaches / total_records * 100) if total_records > 0 else 0, 2)
        }
    
    @staticmethod
    def get_sla_breaches(
        df: pd.DataFrame,
        mttr_col: str = "MTTR (Hours)",
        sla_threshold: float = 24.0,
        top_n: int = 10
    ) -> pd.DataFrame:
        """Get SLA breach records sorted by severity."""
        breaches = df[df[mttr_col] > sla_threshold].copy()
        breaches["breach_amount"] = breaches[mttr_col] - sla_threshold
        
        return (
            breaches
            .sort_values("breach_amount", ascending=False)
            .head(top_n)
            [["Date", "Site Name", "REGION", "Bucket", "MTTR (Hours)", "breach_amount"]]
        )


class MTTRPredictor:
    """Predict MTTR trends using time-series methods."""
    
    @staticmethod
    def calculate_trend(
        df: pd.DataFrame,
        date_col: str = "Date",
        value_col: str = "MTTR (Hours)",
        window: int = 7
    ) -> pd.DataFrame:
        """Calculate MTTR trend using moving average."""
        daily_data = (
            df.groupby(df[date_col].dt.date)
            .agg({value_col: ["sum", "mean", "count"]})
            .reset_index()
        )
        daily_data.columns = ["Date", "total_mttr", "avg_mttr", "failure_count"]
        daily_data["Date"] = pd.to_datetime(daily_data["Date"])
        daily_data = daily_data.sort_values("Date")
        
        daily_data[f"ma_{window}"] = daily_data["avg_mttr"].rolling(window=window).mean()
        
        # Simple linear regression for trend
        if len(daily_data) > 1:
            x = np.arange(len(daily_data)).reshape(-1, 1)
            y = daily_data["avg_mttr"].values
            
            valid_idx = ~np.isnan(y)
            if valid_idx.sum() > 1:
                slope, intercept = np.polyfit(x[valid_idx].flatten(), y[valid_idx], 1)
                daily_data["trend"] = slope * x.flatten() + intercept
            else:
                daily_data["trend"] = daily_data["avg_mttr"]
        
        return daily_data
    
    @staticmethod
    def forecast_mttr(
        df: pd.DataFrame,
        periods: int = 7,
        date_col: str = "Date",
        value_col: str = "MTTR (Hours)"
    ) -> pd.DataFrame:
        """Simple MTTR forecast using exponential smoothing."""
        daily_data = (
            df.groupby(df[date_col].dt.date)
            .agg({value_col: "mean"})
            .reset_index()
        )
        daily_data.columns = ["Date", "mttr"]
        daily_data["Date"] = pd.to_datetime(daily_data["Date"])
        daily_data = daily_data.sort_values("Date")
        
        if len(daily_data) < 3:
            return daily_data
        
        # Simple exponential smoothing
        alpha = 0.3
        forecast_values = []
        last_value = daily_data["mttr"].iloc[-1]
        
        for _ in range(periods):
            last_value = alpha * last_value + (1 - alpha) * last_value
            forecast_values.append(last_value)
        
        future_dates = [
            daily_data["Date"].max() + timedelta(days=i+1)
            for i in range(periods)
        ]
        
        forecast_df = pd.DataFrame({
            "Date": future_dates,
            "mttr": forecast_values,
            "type": "forecast"
        })
        
        daily_data["type"] = "actual"
        
        return pd.concat([daily_data, forecast_df], ignore_index=True)


class PerformanceMetrics:
    """Calculate performance metrics by engineer/team."""
    
    @staticmethod
    def calculate_team_metrics(
        df: pd.DataFrame,
        team_col: Optional[str] = None
    ) -> pd.DataFrame:
        """Calculate metrics grouped by team or engineer."""
        if team_col is None or team_col not in df.columns:
            return pd.DataFrame()
        
        metrics = df.groupby(team_col, dropna=False).agg({
            "MTTR (Hours)": ["sum", "mean", "min", "max", "std", "count"],
            "Site Name": "nunique"
        }).round(2)
        
        metrics.columns = ["total_mttr", "avg_mttr", "min_mttr", "max_mttr", "std_mttr", "failure_count", "sites"]
        metrics = metrics.reset_index()
        metrics.columns = [team_col, "total_mttr", "avg_mttr", "min_mttr", "max_mttr", "std_mttr", "failure_count", "sites"]
        
        # Calculate efficiency score (lower MTTR and higher resolution is better)
        metrics["efficiency_score"] = (
            (metrics["avg_mttr"].max() - metrics["avg_mttr"]) / 
            (metrics["avg_mttr"].max() - metrics["avg_mttr"].min() + 0.001) * 100
        ).round(1)
        
        return metrics.sort_values("efficiency_score", ascending=False)


def get_outage_heatmap_data(
    df: pd.DataFrame,
    date_col: str = "Date",
    mttr_col: str = "MTTR (Hours)"
) -> pd.DataFrame:
    """Create heatmap data for outages by hour of day and day of week."""
    df_copy = df.copy()
    df_copy["hour"] = pd.to_datetime(df_copy[date_col]).dt.hour
    df_copy["day_of_week"] = pd.to_datetime(df_copy[date_col]).dt.day_name()
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    heatmap_data = df_copy.pivot_table(
        index="day_of_week",
        columns="hour",
        values=mttr_col,
        aggfunc="sum",
        fill_value=0
    )
    
    heatmap_data = heatmap_data.reindex([day for day in day_order if day in heatmap_data.index])
    
    return heatmap_data


def get_failure_distribution_by_time(
    df: pd.DataFrame,
    date_col: str = "Date"
) -> Dict[str, int]:
    """Get failure count by time of day."""
    df_copy = df.copy()
    df_copy["hour"] = pd.to_datetime(df_copy[date_col]).dt.hour
    df_copy["time_period"] = pd.cut(
        df_copy["hour"],
        bins=[0, 6, 12, 18, 24],
        labels=["Night (00-06)", "Morning (06-12)", "Afternoon (12-18)", "Evening (18-24)"],
        include_lowest=True
    )
    
    return df_copy["time_period"].value_counts().to_dict()
