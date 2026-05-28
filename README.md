# Network Failure & MTTR Analytics Dashboard

A professional-grade Streamlit analytics dashboard for analyzing network failures, MTTR metrics, SLA compliance, and predictive insights with advanced features for production telecom operations.

##  Key Features

###  Executive Dashboard
- **5 KPI Metrics**: Total failures, total MTTR, average MTTR, affected sites, P95 MTTR
- **Daily Failure Trends**: Visualize failure patterns over time
- **Failure Bucket Distribution**: Understand which failure types dominate
- **Dual-Axis Analytics**: Combined failures and MTTR view
- **MTTR Trend Analysis**: Daily trends with moving averages

###  Regional Intelligence
- **Regional Comparison**: MTTR by region with color-coded performance
- **Site Type Analysis**: Performance breakdown by Macro/Micro/Repeater/Indoor
- **Regional Heatmap**: MTTR distribution across regions and failure types
- **Kenya Regional Map**: Interactive Folium-based map showing regional outage intensity
- **Geographic Clustering**: Identify problem regions at a glance

###  Site Performance
- **Top Sites Analysis**: Identify highest-impact sites by MTTR and frequency
- **Site Scatter Plot**: Correlation between operating hours and MTTR
- **Failure Frequency Ranking**: Sites with most repeated failures
- **Dynamic Top-N Selection**: Adjust number of sites displayed
- **Site Intelligence**: Full site name, region, and performance metrics

###  Failure Pattern Analysis
- **Hierarchical Sunburst**: Region → Bucket → Site Type breakdown
- **Daily Pattern Explorer**: Daily failures decomposed by site and reason
- **Hour of Day Heatmap**: Identify peak failure hours across the week
- **Day-of-Week Analysis**: Understand weekly patterns
- **Resolution Flow**: Power source → Failure type → Status visualization

###  Advanced Analytics

####  Anomaly Detection
- **IQR-Based Detection**: Automatically identifies unusual MTTR values
- **Statistical Analysis**: Z-score and interquartile range methods
- **Visual Highlighting**: Anomalies displayed in red with diamond markers
- **Impact Quantification**: Shows percentage of data points flagged
- **Trend-Based Detection**: Identifies deviations from rolling averages

####  SLA Compliance Tracking
- **Real-Time Compliance Rate**: Percentage of records meeting SLA
- **Breach Counter**: Total number of SLA breaches
- **Severity-Based SLA**: Different thresholds for Critical (4h), Major (12h), Minor (48h)
- **Breach Visualization**: Top breaches displayed in bar chart
- **Breach Details**: Sorted by severity for prioritization
- **Status Indicators**:  Good (≥95%) |  Warning (80-95%) |  Critical (<80%)

####  MTTR Trend & Forecasting
- **7-Day Forecast**: Exponential smoothing predictions
- **Trend Visualization**: Actual vs predicted MTTR
- **Moving Average**: 7-day rolling average overlay
- **Daily Aggregation**: Automatic grouping by date
- **Confidence Indicators**: Visual distinction between actual and forecast

####  Team Performance Metrics
- **Efficiency Score**: Calculated from average MTTR and failure count
- **Team Aggregation**: Automatic grouping by Engineer/Team
- **Performance Comparison**: Side-by-side metric comparison
- **Workload Distribution**: Sites and failure count per team
- **Statistical Measures**: Min, max, std deviation per team

###  Visualization Enhancements
- **Professional Styling**: Clean, modern Plotly charts
- **Responsive Design**: Charts adapt to screen and window size
- **Consistent Themes**: Dark mode and light mode support
- **Interactive Features**: Zoom, pan, hover details, click filtering
- **Detailed Tooltips**: Rich hover information with proper formatting
- **Color Coding**: Semantic colors (green=good, amber=warning, red=critical)
- **Legend Management**: Positioned for clarity, collapsible
- **Label Clarity**: Readable axes, titles, units, and annotations

###  Data Management
- **Multi-Format Support**: Excel (.xlsx, .xls) and CSV files
- **Flexible Filters**: 
  - Date range selector
  - Region, Site Type, Classification, Visibility, Bucket multiselect
  - MTTR range slider
- **Real-Time Filtering**: Charts update instantly
- **Data Validation**: Automatic cleaning and type conversion
- **Export Capability**: Download filtered data as CSV

###  Theme Support
- **Dark Mode**: Optimized for low-light environments
- **Light Mode**: Clear, bright presentation
- **Adaptive Colors**: Charts adjust to selected theme automatically
- **Consistent Styling**: All components theme-aware

##  Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Quick Start
```bash
# Clone or navigate to repository
cd Failure-report-automation

# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app_enhanced.py
```

Dashboard available at: `http://localhost:8501`

##  Data Format

### Required Columns
| Column | Type | Description |
|--------|------|-------------|
| Date | DateTime | Failure timestamp |
| REGION | String | Geographic region |
| SITE TYPE | String | Site classification |
| Site Classification | String | Severity level |
| Visibility | String | Impact visibility |
| Bucket | String | Failure category |
| MTTR (Hours) | Float | Resolution time |
| Site Name | String | Site identifier |

### Optional Columns
| Column | Type | Use Case |
|--------|------|----------|
| Total Monthly Hrs | Float | Site usage analysis |
| Source of Power | String | Infrastructure type |
| Status | String | Resolution status |
| Engineer | String | Team member metrics |
| Team | String | Team-level analysis |

##  Usage Guide

### 1. Upload Data
- Click " Upload failure report" in sidebar
- Select Excel or CSV file with required columns
- Dashboard auto-validates and processes data

### 2. Apply Filters
Use sidebar controls to narrow analysis:
- **Date Range**: Select analysis period
- **Region**: Filter by geography
- **Site Type**: Focus on specific infrastructure
- **Classification**: By severity level
- **Visibility**: By impact scope
- **Failure Bucket**: By failure type
- **MTTR Range**: By resolution time

### 3. Analyze by Section

#### Overview
- Understand total impact and trends
- Identify dominant failure types
- Monitor daily patterns

#### Regional Analysis
- Compare regions by MTTR
- Identify regional hotspots on map
- Understand type distribution by region

#### Site Performance
- Find problematic sites
- Understand site usage correlation
- Identify repeated failures

#### Patterns & Trends
- Explore hierarchical breakdown
- Understand temporal patterns
- Review resolution flow

#### Advanced Analytics
- Detect anomalies automatically
- Check SLA compliance
- Review MTTR forecast
- Compare team performance

#### Data Export
- Inspect complete dataset
- Download filtered results
- Share with stakeholders

##  Advanced Features Explained

### Anomaly Detection Algorithm
- **Method**: Interquartile Range (IQR) based
- **Formula**: Outliers = (value < Q1 - 1.5×IQR) OR (value > Q3 + 1.5×IQR)
- **Temporal**: Also detects deviations from rolling averages
- **Use Case**: Identify unusual MTTR patterns requiring investigation

### SLA Compliance Calculation
```
Compliance = (Non-breach Count / Total Count) × 100

Breach Rules:
- Critical incidents: > 4 hours
- Major incidents: > 12 hours
- Minor incidents: > 48 hours
```

### MTTR Forecasting
- **Method**: Exponential Smoothing (α=0.3)
- **Period**: 7-day forecast
- **Input**: Daily average MTTR
- **Output**: Predicted trend line
- **Accuracy**: Suitable for short-term operational planning

### Efficiency Score
```
Efficiency = ((Max MTTR - Team MTTR) / (Max - Min)) × 100

Higher scores = better performance
```

##  Customization

### Theme Colors
Edit in `visualizations.py`:
```python
SEQUENTIAL_SCALE = ["#312e81", "#4f46e5", "#06b6d4", "#22d3ee"]
DISCRETE_COLORS = [
    "#6366f1", "#0ea5e9", "#10b981", "#f59e0b", 
    "#ef4444", "#8b5cf6", "#ec4899"
]
```

### SLA Thresholds
Edit in `app_enhanced.py`:
```python
SLA_THRESHOLD_CRITICAL = 4.0    # Hours
SLA_THRESHOLD_MAJOR = 12.0      # Hours
SLA_THRESHOLD_MINOR = 48.0      # Hours
```

### Chart Heights & Margins
Modify in individual chart functions in `app_enhanced.py`:
```python
height=480,
margin=dict(l=75, r=35, t=100, b=80)
```

##  Performance Characteristics

- **Data Size**: Optimized for 100-100K records
- **Filtering**: Instant response (<1s for typical datasets)
- **Chart Rendering**: <500ms per chart
- **Memory Footprint**: ~50-200MB for typical sessions
- **Caching**: Data loaded once, reused across interactions

##  Data Quality Assurance

 **Validation**: All required columns verified on load
 **Type Conversion**: Automatic numeric and datetime conversion
 **Missing Values**: Graceful handling with NaN preservation
 **Duplicate Handling**: Preserved for accurate aggregation
 **Outlier Safety**: Calculations use robust methods
 **Zero Division**: Prevented in all computations

##  File Reference

| File | Purpose |
|------|---------|
| `app_lovable.py` | Main application (recommended version) |
| `analytics.py` | Advanced analytics module |
| `visualizations.py` | Chart and visualization functions |
| `utils.py` | Utility and helper functions |
| `generate_dummy_data.py` | Sample data generator |
| `requirements.txt` | Python dependencies |
| `DEPLOYMENT_GUIDE.md` | Setup and deployment |

##  Deployment

### Local Development
```bash
streamlit run app_lovable.py
```

### Production Setup
See `DEPLOYMENT_GUIDE.md` for:
- Docker deployment
- Server configuration
- Performance tuning
- Monitoring setup

##  Support

### Common Issues

**Map not showing?**
```bash
pip install folium streamlit-folium --upgrade
```

**Slow performance?**
- Reduce date range
- Filter to smaller regions
- Check available RAM

**Data not loading?**
- Verify file format (Excel/CSV)
- Check required columns present
- Ensure date format: YYYY-MM-DD

##  License & Attribution

Dashboard created with:
- **Streamlit**: Web framework
- **Plotly**: Interactive visualizations
- **Pandas**: Data manipulation
- **SciPy**: Statistical analysis
- **Folium**: Geographic mapping

##  Future Roadmap

Planned enhancements:
- [ ] PDF report generation
- [ ] Real-time data streaming
- [ ] Custom alerts and notifications
- [ ] Root cause analysis engine
- [ ] Database backend integration
- [ ] Scheduled report generation
- [ ] API for external integration
- [ ] Advanced ML-based forecasting

---

**Version**: 2.0 (Enhanced)
**Last Updated**: May 26, 2026
