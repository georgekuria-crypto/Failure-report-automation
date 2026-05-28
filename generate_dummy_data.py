"""
Test Data Generator for Failure Report Dashboard

This utility generates sample failure report data for testing and development purposes.
It creates a realistic dataset with 250 failure records spanning 45 days with various
regions, site types, failure buckets, and MTTR values.

Usage:
    python generate_dummy_data.py

This will generate a CSV file that can be uploaded to the dashboard for testing.

For production use, upload real failure report data from your network monitoring system.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_data():
    np.random.seed(42)
    num_records = 250
    
    # 1. Dates (last 45 days)
    start_date = datetime.now() - timedelta(days=45)
    dates = [start_date + timedelta(days=int(np.random.randint(0, 45)), hours=int(np.random.randint(0, 24)), minutes=int(np.random.randint(0, 60))) for _ in range(num_records)]
    
    # 2. Regions
    regions = ["Nairobi", "Coast", "Rift Valley", "Central", "Western"]
    region_weights = [0.4, 0.2, 0.2, 0.1, 0.1]
    region_choices = np.random.choice(regions, size=num_records, p=region_weights)
    
    # 3. Site Types
    site_types = ["Macro", "Micro", "Repeater", "Indoor"]
    site_type_weights = [0.6, 0.25, 0.1, 0.05]
    site_type_choices = np.random.choice(site_types, size=num_records, p=site_type_weights)
    
    # 4. Site Classifications
    classifications = ["Critical", "Major", "Minor"]
    class_weights = [0.2, 0.5, 0.3]
    class_choices = np.random.choice(classifications, size=num_records, p=class_weights)
    
    # 5. Visibility
    visibility_choices = np.random.choice(["High", "Medium", "Low"], size=num_records, p=[0.3, 0.5, 0.2])
    
    # 6. Failure Buckets
    buckets = ["Power Outage", "Hardware Failure", "Transmission Fiber Cut", "Software Panic", "Configuration Error"]
    bucket_weights = [0.45, 0.25, 0.15, 0.1, 0.05]
    bucket_choices = np.random.choice(buckets, size=num_records, p=bucket_weights)
    
    # 7. MTTR (Hours) - using a log-normal distribution to be realistic (most failures resolved quickly, a few take long)
    mttr_choices = np.random.lognormal(mean=1.5, sigma=1.0, size=num_records)
    mttr_choices = np.clip(mttr_choices, 0.2, 96.0) # bound between 12 mins and 4 days
    mttr_choices = np.round(mttr_choices, 2)
    
    # 8. Site Names (based on region)
    site_names = []
    site_counters = {}
    for r in region_choices:
        if r not in site_counters:
            site_counters[r] = 1
        # Randomly choose an existing site or create a new one (to simulate repeated failures)
        site_id = np.random.randint(1, 15)
        site_names.append(f"{r}_Site_{site_id:02d}")
        
    # 9. Total Monthly Hrs (mostly 720 or 744)
    total_monthly_hrs = np.random.choice([720, 744], size=num_records)
    
    # 10. Source of Power
    power_sources = ["National Grid", "Generator Backup", "Solar Hybrid", "Battery Backup"]
    power_source_choices = np.random.choice(power_sources, size=num_records, p=[0.6, 0.25, 0.1, 0.05])
    
    # 11. Status
    status_choices = np.random.choice(["Resolved", "In Progress", "Pending Vendor", "Investigating"], size=num_records, p=[0.8, 0.1, 0.05, 0.05])
    
    # Assemble DataFrame
    df = pd.DataFrame({
        "Date": dates,
        "REGION": region_choices,
        "SITE TYPE": site_type_choices,
        "Site Classification": class_choices,
        "Visibility": visibility_choices,
        "Bucket": bucket_choices,
        "MTTR (Hours)": mttr_choices,
        "Site Name": site_names,
        "Total Monthly Hrs": total_monthly_hrs,
        "Source of Power": power_source_choices,
        "Status": status_choices
    })
    
    # Save to Excel
    df.to_excel("sample_failure_report.xlsx", index=False)
    print("Successfully generated sample_failure_report.xlsx with 250 records!")

if __name__ == "__main__":
    generate_data()
