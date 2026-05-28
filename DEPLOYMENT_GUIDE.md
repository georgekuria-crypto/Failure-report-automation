# Enhanced Network Failure & MTTR Dashboard - Deployment Guide

## Overview
This is a comprehensive Streamlit-based analytics dashboard for network failure analysis with advanced features including anomaly detection, SLA tracking, MTTR forecasting, and regional mapping.

## Features Implemented

### Core Enhancements
✅ **Performance Optimized**: Streamlined data processing, efficient caching, lazy loading
✅ **Advanced Analytics**:
  - Automatic anomaly detection (IQR method)
  - SLA compliance tracking and breach detection
  - MTTR trend analysis and forecasting
  - Team/Engineer performance metrics

✅ **Enhanced Visualizations**:
  - Professional, modern chart styling with improved spacing
  - Responsive layouts that adapt to screen size
  - Detailed hover tooltips with contextual information
  - Consistent color schemes across all charts
  - Proper axis labels, legends, and annotations

✅ **Regional Analysis**:
  - Kenya regional outage map with Folium integration
  - Regional MTTR heatmaps by failure type
  - Hour-of-day vs day-of-week outage patterns

✅ **Production Features**:
  - Robust error handling and data validation
  - Missing value handling
  - CSV and Excel file support
  - Data export functionality
  - Dark/Light theme support
  - Responsive dashboard design

## Installation & Setup

### 1. Install Dependencies
```bash
cd "c:\Projects\Failure_reports_dashboard\Failure-report-automation"
pip install -r requirements.txt
```

### 2. File Structure
```
├── app.py                      # Main application (use app_enhanced.py as app.py)
├── app_enhanced.py             # Enhanced version (rename to app.py)
├── analytics.py                # Advanced analytics module
├── visualizations.py           # Visualization functions
├── utils.py                    # Utility functions
├── generate_dummy_data.py       # Demo data generator
├── sample_failure_report.xlsx   # Sample data
└── requirements.txt            # Dependencies
```

### 3. Running the Dashboard

#### Option A: Using app_enhanced.py directly
```bash
streamlit run app_enhanced.py
```

#### Option B: Replace app.py and run
```bash
# Backup original
copy app.py app_original.py

# Use enhanced version
copy app_enhanced.py app.py

# Run
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`

## Key Modules

### analytics.py
- **AnomalyDetector**: Detects outliers using IQR and Z-score methods
- **SLATracker**: Calculates SLA compliance and identifies breaches
- **MTTRPredictor**: Forecasts MTTR trends using exponential smoothing
- **PerformanceMetrics**: Calculates team/engineer efficiency scores

### visualizations.py
- **Style functions**: Consistent chart styling and theming
- **Advanced charts**: Anomaly charts, heatmaps, KPI gauges
- **Kenya map**: Interactive regional outage visualization
- **Forecast charts**: MTTR trends with predictions
- **Team metrics**: Performance comparison charts

### utils.py
- **Formatting**: Number and duration formatting
- **Statistics**: Percentile calculation, outlier detection
- **Time features**: Hour/day-of-week extraction
- **Validation**: Data quality checks

## Dashboard Sections

### 📊 Overview Tab
- Total failures, MTTR, and affected sites KPIs
- Failure bucket distribution
- Daily failure trends
- Combined failures and MTTR view
- Daily MTTR trend with range slider

### 🌍 Regional Analysis Tab
- MTTR by region comparison
- MTTR by site type
- Regional MTTR heatmap by failure type
- **Interactive Kenya regional outage map** (Folium-based)

### 📍 Site Performance Tab
- Top sites by total MTTR
- Top sites by failure frequency
- Site MTTR vs operating hours scatter plot
- Configurable site count slider

### 📈 Patterns & Trends Tab
- Hierarchical outage breakdown (Sunburst)
- Daily failures by site and reason (Sunburst)
- Resolution flow analysis (Parallel categories)
- **Outage hour heatmap** (Hour × Day of Week)

### 🔬 Advanced Analytics Tab
- **🚨 Anomaly Detection**: Identifies unusual MTTR patterns
- **📋 SLA Compliance**: Tracks SLA breaches and compliance rate
- **📊 MTTR Forecasting**: 7-day trend forecast
- **👥 Team Metrics**: Performance efficiency scores (if data available)

### 📋 Data Export Tab
- Full dataset viewer
- CSV download button
- Dynamic filtering with sidebar

## Data Format Requirements

### Required Columns
- `Date`: Datetime field (will auto-convert)
- `REGION`: Geographic region
- `SITE TYPE`: Type of site (Macro, Micro, Repeater, Indoor)
- `Site Classification`: Priority level (Critical, Major, Minor)
- `Visibility`: Visibility level (High, Medium, Low)
- `Bucket`: Failure category
- `MTTR (Hours)`: Mean Time To Recovery in hours
- `Site Name`: Identifier for site

### Optional Columns
- `Total Monthly Hrs`: For site usage analysis
- `Source of Power`: Power infrastructure type
- `Status`: Resolution status
- `Engineer`/`Team`: For team performance metrics

## Performance Optimization Notes

1. **Caching**: Data loading uses `@st.cache_data` decorator for performance
2. **Lazy Loading**: Charts only render when tabs are selected
3. **Efficient Aggregations**: Grouped operations minimize dataframe operations
4. **Memory Usage**: Filtered data reduces processing overhead

## Customization Options

### SLA Thresholds (in app.py)
```python
SLA_THRESHOLD_CRITICAL = 4.0    # Hours
SLA_THRESHOLD_MAJOR = 12.0      # Hours
SLA_THRESHOLD_MINOR = 48.0      # Hours
```

### Color Schemes
- **SEQUENTIAL_SCALE**: Used for heatmaps (blue to cyan gradient)
- **DISCRETE_COLORS**: Used for categorical charts (7 colors)

### Chart Heights & Margins
Configured per chart in visualization functions for optimal layout

## Troubleshooting

### Missing Module Errors
```bash
pip install -r requirements.txt --upgrade
```

### Map Not Displaying
Ensure `folium` and `streamlit-folium` are installed:
```bash
pip install folium streamlit-folium
```

### Slow Performance
- Ensure filtered dataset is manageable (< 10,000 rows)
- Use date range filters to reduce data
- Disable visualizations not in use

### Data Not Loading
- Verify Excel file has required columns
- Check date format compatibility
- Ensure no special characters in filenames

## Mathematical Accuracy

All calculations maintain exact precision:
- **Total MTTR**: Sum of all MTTR values
- **Average MTTR**: Mean MTTR with NaN handling
- **Failure Count**: Simple row count
- **Site Uniqueness**: Using `nunique()`
- **Percentiles**: NumPy-based calculation
- **SLA Compliance**: Threshold-based comparison
- **Anomalies**: IQR multiplier method (1.5x default)
- **Forecasting**: Exponential smoothing (α=0.3)

## Deployment to Production

1. Install dependencies: `pip install -r requirements.txt`
2. Test locally: `streamlit run app.py`
3. Set Streamlit config (~/.streamlit/config.toml):
```ini
[server]
headless = true
port = 8501
runOnSave = false

[client]
showErrorDetails = false
```

4. Run with gunicorn/waitress (optional):
```bash
streamlit run app.py --server.port=8501 --server.headless=true
```

## Support for Multiple Versions

- **app.py**: Original version (included in repo)
- **app_enhanced.py**: New enhanced version with all features
- **app_original.py**: Backup created during upgrade

To switch between versions:
```bash
# Use enhanced
copy app_enhanced.py app.py

# Revert to original
copy app_original.py app.py
```

## Version Info

- **Base**: Streamlit 1.28+
- **Plotly**: 5.14+
- **Python**: 3.8+
- **Enhanced Features**: Anomaly detection, SLA, forecasting, mapping
- **Last Updated**: 2026-05-26

## Future Enhancements

Potential additions:
- PDF report generation with ReportLab
- Real-time data integration
- Custom threshold configuration UI
- Historical trend comparison
- Root cause analysis
- Automated alerting
- Database backend integration
