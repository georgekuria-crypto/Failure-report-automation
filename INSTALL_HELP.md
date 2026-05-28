# Fix for Import Errors

## Issue: ModuleNotFoundError or ImportError

If you see errors like:
```
ModuleNotFoundError: No module named 'streamlit_folium'
ImportError: cannot import name 'st_folium' from 'streamlit_folium'
```

### Solution

The dashboard has **optional** geographic mapping features that require additional packages. You can run the dashboard in two ways:

## Option A: Core Installation (Recommended for Quick Start)

This runs the dashboard with all core features except the Kenya regional map:

```bash
# Install core dependencies only
pip install streamlit pandas numpy plotly scipy openpyxl

# Run the dashboard
streamlit run app_enhanced.py
```

**Features available**:
- ✅ All basic visualizations
- ✅ All filters and analytics
- ✅ Advanced analytics (anomaly, SLA, forecasting)
- ✅ All 6 tabs working
- ❌ Kenya regional map (optional feature)

## Option B: Full Installation (With Geographic Mapping)

For the complete experience including the Kenya regional map:

```bash
# Install all dependencies including optional mapping features
pip install streamlit pandas numpy plotly scipy openpyxl folium

# Run the dashboard
streamlit run app_enhanced.py
```

**Features available**:
- ✅ All features from Option A
- ✅ Kenya regional map with zoom/pan
- ✅ Interactive geographic visualization

## Option C: Install Requirements File

The safest way using the requirements.txt:

```bash
# For core installation
pip install streamlit pandas numpy plotly scipy openpyxl

# For full installation with mapping:
# Uncomment the folium lines in requirements.txt, then:
pip install -r requirements.txt
```

## Troubleshooting

### Still getting import errors?

1. **Reinstall all dependencies**:
   ```bash
   pip install --upgrade streamlit pandas numpy plotly scipy openpyxl
   ```

2. **Check installed packages**:
   ```bash
   pip list | grep streamlit
   pip list | grep plotly
   ```

3. **Clear Python cache**:
   ```bash
   # Remove __pycache__ directory
   rm -r __pycache__
   
   # Then try again
   streamlit run app_enhanced.py
   ```

4. **Use specific Python version**:
   ```bash
   python -m pip install --upgrade streamlit pandas numpy plotly scipy openpyxl
   ```

### Map not appearing?

This is normal if folium isn't installed. The dashboard still works fully - just the map feature shows a helpful message.

To enable the map:
```bash
pip install folium
streamlit run app_enhanced.py
```

## Recommended Setup

**For most users**, install the core dependencies:
```bash
pip install streamlit pandas numpy plotly scipy openpyxl
streamlit run app_enhanced.py
```

This gives you 95% of the features immediately without extra setup.

**Later, if you want the map**:
```bash
pip install folium
# Restart the app, map will now appear
```

## Alternative: Fresh Environment

If you continue to have issues:

```bash
# Create a new virtual environment (optional but recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install everything fresh
pip install streamlit pandas numpy plotly scipy openpyxl

# Run app
streamlit run app_enhanced.py
```

---

**Status**: Dashboard runs smoothly with core installation ✅
**Map feature**: Optional, enhances experience but not required ✅
**All other features**: Work perfectly without folium ✅
