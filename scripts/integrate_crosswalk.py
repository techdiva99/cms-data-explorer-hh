#!/usr/bin/env python3
"""
Integrate ZIP code to county crosswalk data into the CMS Home Health database.
This will add county information and geographic data for better analytics.
"""

import pandas as pd
import sqlite3
import json
from pathlib import Path

def process_crosswalk_data():
    """Process the downloaded crosswalk data and prepare it for database integration."""
    print("Processing crosswalk data...")
    
    # Read the crosswalk data
    df = pd.read_csv('zip_county_crosswalk_raw.csv')
    print(f"Loaded {len(df)} ZIP code records")
    
    # Clean and standardize the data
    df['zip'] = df['zip'].astype(str).str.zfill(5)  # Ensure 5-digit ZIP codes
    
    # Parse county weights (JSON string) to get primary county
    def get_primary_county(county_weights_json, county_fips):
        """Extract the primary county from county weights JSON."""
        if pd.isna(county_weights_json) or county_weights_json == '':
            return county_fips
        
        try:
            weights = json.loads(county_weights_json.replace("'", '"'))
            if weights:
                # Return the county FIPS with highest weight
                primary_fips = max(weights.keys(), key=lambda k: weights[k])
                return primary_fips
        except:
            pass
        
        return county_fips
    
    # Add primary county FIPS
    df['primary_county_fips'] = df.apply(
        lambda row: get_primary_county(row['county_weights'], row['county_fips']), 
        axis=1
    )
    
    # Clean numeric fields
    numeric_fields = ['lat', 'lng', 'population', 'density']
    for field in numeric_fields:
        df[field] = pd.to_numeric(df[field], errors='coerce')
    
    # Create a clean version for the database
    crosswalk_clean = df[[
        'zip', 'lat', 'lng', 'city', 'state_id', 'state_name', 
        'county_fips', 'county_name', 'primary_county_fips',
        'county_weights', 'county_names_all', 'county_fips_all',
        'population', 'density', 'timezone', 'imprecise', 'military'
    ]].copy()
    
    # Rename columns for consistency
    crosswalk_clean = crosswalk_clean.rename(columns={
        'zip': 'zip_code',
        'lat': 'latitude',
        'lng': 'longitude',
        'state_id': 'state_abbr',
        'county_fips': 'primary_county_fips_main',
        'county_name': 'primary_county_name'
    })
    
    print(f"Processed crosswalk data shape: {crosswalk_clean.shape}")
    return crosswalk_clean

def create_crosswalk_table(conn, crosswalk_df):
    """Create the ZIP code crosswalk table in the database."""
    print("Creating zip_county_crosswalk table...")
    
    # Drop existing table if it exists
    conn.execute("DROP TABLE IF EXISTS zip_county_crosswalk")
    
    # Create the new table
    create_table_sql = """
    CREATE TABLE zip_county_crosswalk (
        zip_code TEXT PRIMARY KEY,
        latitude REAL,
        longitude REAL,
        city TEXT,
        state_abbr TEXT,
        state_name TEXT,
        primary_county_fips_main TEXT,
        primary_county_name TEXT,
        primary_county_fips TEXT,
        county_weights TEXT,
        county_names_all TEXT,
        county_fips_all TEXT,
        population INTEGER,
        density REAL,
        timezone TEXT,
        imprecise BOOLEAN,
        military BOOLEAN
    )
    """
    
    conn.execute(create_table_sql)
    
    # Insert the data
    crosswalk_df.to_sql('zip_county_crosswalk', conn, if_exists='replace', index=False)
    
    # Create index for faster lookups
    conn.execute("CREATE INDEX idx_zip_county_crosswalk_zip ON zip_county_crosswalk(zip_code)")
    
    print(f"Inserted {len(crosswalk_df)} records into zip_county_crosswalk table")

def add_x_county_columns():
    """Add x_county and related columns to existing tables."""
    print("Adding x_county columns to existing tables...")
    
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    
    # Add columns to providers table
    add_columns_sql = [
        "ALTER TABLE providers ADD COLUMN x_county TEXT",
        "ALTER TABLE providers ADD COLUMN x_county_fips TEXT", 
        "ALTER TABLE providers ADD COLUMN x_latitude REAL",
        "ALTER TABLE providers ADD COLUMN x_longitude REAL",
        "ALTER TABLE providers ADD COLUMN x_data_source TEXT DEFAULT 'zip_crosswalk'"
    ]
    
    for sql in add_columns_sql:
        try:
            conn.execute(sql)
            print(f"Executed: {sql}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column already exists: {sql}")
            else:
                print(f"Error: {e}")
    
    # Update providers with crosswalk data
    update_sql = """
    UPDATE providers 
    SET 
        x_county = (
            SELECT primary_county_name 
            FROM zip_county_crosswalk 
            WHERE zip_county_crosswalk.zip_code = providers.zip_code
        ),
        x_county_fips = (
            SELECT primary_county_fips 
            FROM zip_county_crosswalk 
            WHERE zip_county_crosswalk.zip_code = providers.zip_code
        ),
        x_latitude = (
            SELECT latitude 
            FROM zip_county_crosswalk 
            WHERE zip_county_crosswalk.zip_code = providers.zip_code
        ),
        x_longitude = (
            SELECT longitude 
            FROM zip_county_crosswalk 
            WHERE zip_county_crosswalk.zip_code = providers.zip_code
        )
    WHERE EXISTS (
        SELECT 1 FROM zip_county_crosswalk 
        WHERE zip_county_crosswalk.zip_code = providers.zip_code
    )
    """
    
    conn.execute(update_sql)
    conn.commit()
    
    # Check results
    result = conn.execute("""
        SELECT 
            COUNT(*) as total_providers,
            COUNT(x_county) as providers_with_x_county,
            COUNT(county) as providers_with_orig_county,
            COUNT(CASE WHEN x_county IS NOT NULL AND county IS NULL THEN 1 END) as x_county_fills_gaps
        FROM providers
    """).fetchone()
    
    print(f"\nUpdate Results:")
    print(f"Total providers: {result[0]}")
    print(f"Providers with x_county: {result[1]}")
    print(f"Providers with original county: {result[2]}")
    print(f"x_county fills gaps where county was NULL: {result[3]}")
    
    conn.close()

def update_analytics_with_x_county():
    """Update analytics.py to use x_county as fallback."""
    print("Updating analytics.py to use x_county...")
    
    # Read current analytics file
    analytics_path = Path('analytics.py')
    if not analytics_path.exists():
        print("analytics.py not found")
        return
    
    # The analytics.py will be updated to use COALESCE(county, x_county) 
    # in relevant queries to get the best available county data
    
    print("Analytics update completed (will be applied in next step)")

def generate_coverage_report():
    """Generate a report on data coverage improvements."""
    print("\nGenerating coverage report...")
    
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    
    # Coverage analysis
    coverage_query = """
    SELECT 
        state,
        COUNT(*) as total_providers,
        COUNT(county) as orig_county_coverage,
        COUNT(x_county) as x_county_coverage,
        COUNT(CASE WHEN county IS NULL AND x_county IS NOT NULL THEN 1 END) as improvement_count,
        ROUND(COUNT(county) * 100.0 / COUNT(*), 2) as orig_coverage_pct,
        ROUND(COUNT(x_county) * 100.0 / COUNT(*), 2) as x_coverage_pct
    FROM providers 
    WHERE state IS NOT NULL
    GROUP BY state
    ORDER BY improvement_count DESC
    """
    
    coverage_df = pd.read_sql_query(coverage_query, conn)
    print("\nCoverage by State:")
    print(coverage_df.to_string(index=False))
    
    # Overall summary
    summary_query = """
    SELECT 
        COUNT(*) as total_providers,
        COUNT(county) as orig_county_count,
        COUNT(x_county) as x_county_count,
        COUNT(CASE WHEN county IS NOT NULL OR x_county IS NOT NULL THEN 1 END) as combined_coverage,
        ROUND(COUNT(county) * 100.0 / COUNT(*), 2) as orig_coverage_pct,
        ROUND(COUNT(x_county) * 100.0 / COUNT(*), 2) as x_coverage_pct,
        ROUND(COUNT(CASE WHEN county IS NOT NULL OR x_county IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as combined_coverage_pct
    FROM providers
    """
    
    summary = conn.execute(summary_query).fetchone()
    print(f"\nOverall Summary:")
    print(f"Total providers: {summary[0]}")
    print(f"Original county coverage: {summary[1]} ({summary[4]}%)")
    print(f"X_county coverage: {summary[2]} ({summary[5]}%)")
    print(f"Combined coverage: {summary[3]} ({summary[6]}%)")
    
    # Save coverage report
    coverage_df.to_csv('county_coverage_report.csv', index=False)
    print(f"\nSaved detailed coverage report to county_coverage_report.csv")
    
    conn.close()

def main():
    """Main integration function."""
    print("Starting ZIP code to county crosswalk integration...")
    
    # Step 1: Process crosswalk data
    crosswalk_df = process_crosswalk_data()
    
    # Step 2: Create crosswalk table in database
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    create_crosswalk_table(conn, crosswalk_df)
    conn.close()
    
    # Step 3: Add x_county columns and populate them
    add_x_county_columns()
    
    # Step 4: Generate coverage report
    generate_coverage_report()
    
    print("\n✅ Integration completed successfully!")
    print("\nNext steps:")
    print("1. Update analytics.py to use COALESCE(county, x_county) for better coverage")
    print("2. Test the updated functionality in the Streamlit app")
    print("3. Use x_latitude/x_longitude for geographic analysis")

if __name__ == "__main__":
    main()
