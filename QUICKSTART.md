# Quick Start Guide - Enhanced Dashboard

## 🚀 30-Second Setup

```bash
# 1. Navigate to project
cd "c:\Projects\Failure_reports_dashboard\Failure-report-automation"

# 2. Install dependencies (one time only)
pip install streamlit pandas numpy plotly scipy openpyxl

# 3. Run the enhanced dashboard
streamlit run app_enhanced.py

# 4. Open browser to http://localhost:8501
```

**Done!** Dashboard is running with all core enhancements.

### Optional: Add Geographic Mapping
```bash
# Later, if you want the Kenya map feature:
pip install folium
# Restart the dashboard - map will appear
```

---

## 📋 What's New

### ✨ Major Enhancements
- ✅ **Anomaly Detection**: Auto-detect unusual MTTR patterns
- ✅ **SLA Compliance**: Real-time SLA breach tracking (24-hour target)
- ✅ **MTTR Forecasting**: 7-day trend predictions
- ✅ **Kenya Regional Map**: Interactive geographic outage visualization
- ✅ **Outage Heatmaps**: Hour-of-day × day-of-week patterns
- ✅ **Team Metrics**: Engineer/team performance efficiency scores
- ✅ **Enhanced Charts**: Better spacing, labels, responsiveness
- ✅ **Advanced Analytics**: Statistical analysis and prediction models

### 📊 New Tabs
1. **🔬 Advanced Analytics** - Anomalies, SLA, forecasts, team metrics
2. Enhanced existing tabs with improved visualizations

---

## 📥 Using with Data

### Step 1: Prepare Data
Create Excel or CSV with these columns:
```
Date | REGION | SITE TYPE | Site Classification | Visibility | Bucket | MTTR (Hours) | Site Name
```

Optional columns:
```
Total Monthly Hrs | Source of Power | Status | Engineer | Team
```

### Step 2: Upload
1. Click "📁 Upload failure report" in sidebar
2. Select your file
3. Dashboard auto-processes and validates

### Step 3: Filter & Analyze
1. Use sidebar filters to narrow analysis
2. Click tabs to explore different views
3. Hover over charts for details
4. Download data from "Data Export" tab

---

## 🎯 Key Features Overview

| Feature | Location | Purpose |
|---------|----------|---------|
| KPI Cards | Top of Overview | At-a-glance metrics |
| Anomaly Detection | Advanced Analytics | Find unusual patterns |
| SLA Compliance | Advanced Analytics | Track SLA breaches |
| MTTR Forecast | Advanced Analytics | Predict trends |
| Regional Map | Regional Analysis | Geographic visualization |
| Outage Heatmap | Patterns & Trends | Time-based patterns |
| Team Metrics | Advanced Analytics | Team performance |
| Data Export | Data Export | Download results |

---

## 🔧 Common Tasks

### View Regional Performance
1. Go to **🌍 Regional Analysis** tab
2. Check "MTTR by Region" chart
3. Scroll down to see Kenya regional map
4. Select metric (Failure Count / Total MTTR / Avg MTTR)

### Find Problematic Sites
1. Go to **📍 Site Performance** tab
2. Adjust "Sites to display" slider
3. Compare MTTR and Failure Frequency charts
4. Click site names for more details

### Check SLA Compliance
1. Go to **🔬 Advanced Analytics** tab
2. Find "📋 SLA Compliance & Breaches" section
3. View compliance percentage and top breaches
4. Identify high-priority incidents

### Predict MTTR Trends
1. Go to **🔬 Advanced Analytics** tab
2. Find "📊 MTTR Trend & Forecast" section
3. View actual vs predicted MTTR
4. Plan resource allocation based on forecast

### Detect Anomalies
1. Go to **🔬 Advanced Analytics** tab
2. Find "🚨 Anomaly Detection" section
3. Review detected anomalies (red diamonds)
4. Investigate unusual patterns

### Export Data
1. Go to **📋 Data Export** tab
2. Review filtered dataset
3. Click "📥 Download as CSV"
4. File saved: `failure_report_YYYYMMDD_HHMMSS.csv`

---

## 🎨 Customization Options

### Change SLA Threshold
Edit in `app_enhanced.py` (line ~85):
```python
SLA_THRESHOLD_CRITICAL = 4.0    # Critical: > 4 hours
SLA_THRESHOLD_MAJOR = 12.0      # Major: > 12 hours
SLA_THRESHOLD_MINOR = 48.0      # Minor: > 48 hours
```

### Change Chart Colors
Edit in `visualizations.py` (lines ~19-32):
```python
SEQUENTIAL_SCALE = ["#312e81", "#4f46e5", "#06b6d4", "#22d3ee"]
DISCRETE_COLORS = ["#6366f1", "#0ea5e9", "#10b981", ...]
```

### Adjust Dashboard Theme
Click settings ⚙️ in top right → "Theme" → Dark/Light

---

## 📊 Sample Data

Generate test data:
```bash
python generate_dummy_data.py
```
Creates: `sample_failure_report.xlsx` with 250 records

---

## 🐛 Troubleshooting

### Dashboard won't start
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Try again
streamlit run app_enhanced.py
```

### Map not displaying
```bash
pip install folium streamlit-folium --upgrade
```

### Charts slow to load
- Filter to smaller date range
- Use Filters in sidebar to reduce data
- Check system RAM availability

### File upload fails
- Ensure Excel/CSV format
- Check all required columns present
- Verify Date column is in recognizable format

---

## 📞 Quick Reference

**File to Run**: `app_enhanced.py`
**URL**: `http://localhost:8501`
**Sample Data**: `generate_dummy_data.py`
**Config**: Edit in `app_enhanced.py` (lines 80-95)
**Stop Server**: Press Ctrl+C in terminal

---

## ✅ Checklist

Before sharing dashboard:
- [ ] All required columns present in data
- [ ] Date format consistent (YYYY-MM-DD)
- [ ] No special characters in filenames
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Dashboard runs without errors (`streamlit run app_enhanced.py`)
- [ ] Can upload and filter data successfully
- [ ] Exports work correctly

---

## 📖 Full Documentation

For complete documentation, see:
- **README.md** - Feature overview and data format
- **DEPLOYMENT_GUIDE.md** - Setup and deployment
- **analytics.py** - Algorithm documentation
- **visualizations.py** - Chart function references

---

**Version**: 2.0 (Enhanced)
**Python**: 3.8+
**Status**: ✅ Production Ready
