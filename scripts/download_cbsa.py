#!/usr/bin/env python3
"""
Download ZIP code to CBSA (Core Based Statistical Area) crosswalk data.
"""

import pandas as pd
import requests
import sqlite3
import sys
from io import StringIO
import tempfile
import os
import zipfile

def download_census_cbsa_crosswalk():
    """Download Census ZIP Code to CBSA crosswalk."""
    print("Downloading Census ZIP Code to CBSA crosswalk...")
    
    urls = [
        # 2023 CBSA to ZIP crosswalk
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xls",
        # ZIP to CBSA relationship file
        "https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html"
    ]
    
    # Try direct download of CBSA delineation file
    try:
        url = "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xls"
        print(f"Downloading CBSA delineation file from {url}")
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            with open("cbsa_delineation_2023.xls", "wb") as f:
                f.write(response.content)
            
            # Read the Excel file
            df = pd.read_excel("cbsa_delineation_2023.xls")
            print(f"Downloaded CBSA delineation file with {len(df)} records")
            return df
    except Exception as e:
        print(f"Error downloading CBSA file: {e}")
    
    return None

def download_hud_cbsa_crosswalk():
    """Try to download HUD crosswalk with CBSA data."""
    print("Attempting HUD USPS crosswalk with CBSA data...")
    
    # HUD sometimes has more comprehensive files
    urls = [
        "https://www.huduser.gov/portal/datasets/usps_crosswalk.html",
        # Try direct file URLs
        "https://www.huduser.gov/portal/datasets/usps/ZIP_CBSA_062024.xlsx",
        "https://www.huduser.gov/portal/datasets/usps/ZIP_CBSA_032024.xlsx"
    ]
    
    for url in urls:
        if url.endswith('.xlsx'):
            try:
                print(f"Trying {url}")
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    filename = f"hud_cbsa_{url.split('_')[-1]}"
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    
                    df = pd.read_excel(filename)
                    print(f"Successfully downloaded HUD CBSA data: {len(df)} records")
                    return df
            except Exception as e:
                print(f"Failed {url}: {e}")
    
    return None

def create_cbsa_from_county():
    """Create CBSA mapping using county FIPS codes and known CBSA definitions."""
    print("Creating CBSA mapping from county data...")
    
    # Load county to CBSA mapping (this is a simplified version)
    # In a real implementation, you'd want the full Census crosswalk
    county_cbsa_mapping = {
        # Major metro areas - sample mappings
        '06037': {'cbsa_code': '31080', 'cbsa_name': 'Los Angeles-Long Beach-Anaheim, CA'},
        '36061': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA'},
        '17031': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI'},
        '48201': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX'},
        '04013': {'cbsa_code': '38060', 'cbsa_name': 'Phoenix-Mesa-Scottsdale, AZ'},
        '42101': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD'},
        '48113': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX'},
        '06073': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA'},
        '12086': {'cbsa_code': '33100', 'cbsa_name': 'Miami-Fort Lauderdale-West Palm Beach, FL'},
        '53033': {'cbsa_code': '42660', 'cbsa_name': 'Seattle-Tacoma-Bellevue, WA'},
    }
    
    # Read existing crosswalk data
    try:
        conn = sqlite3.connect('data/processed/cms_homehealth.db')
        
        # Get county FIPS from our existing data
        query = """
        SELECT DISTINCT 
            zip_code,
            primary_county_fips,
            primary_county_name,
            state_abbr
        FROM zip_county_crosswalk 
        WHERE primary_county_fips IS NOT NULL
        """
        
        zip_county_df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Add CBSA information where available
        cbsa_data = []
        for _, row in zip_county_df.iterrows():
            county_fips = row['primary_county_fips']
            cbsa_info = county_cbsa_mapping.get(county_fips, {
                'cbsa_code': None,
                'cbsa_name': None
            })
            
            cbsa_data.append({
                'zip_code': row['zip_code'],
                'county_fips': county_fips,
                'county_name': row['primary_county_name'],
                'state_abbr': row['state_abbr'],
                'cbsa_code': cbsa_info['cbsa_code'],
                'cbsa_name': cbsa_info['cbsa_name']
            })
        
        return pd.DataFrame(cbsa_data)
        
    except Exception as e:
        print(f"Error creating CBSA mapping: {e}")
        return None

def download_comprehensive_cbsa_data():
    """Download comprehensive CBSA data from multiple sources."""
    print("Downloading comprehensive ZIP to CBSA mapping...")
    
    # This uses a known good source for ZIP to CBSA mapping
    try:
        # Missouri Census Data Center has good crosswalk files
        url = "https://mcdc.missouri.edu/applications/geocorr2022.html"
        
        # Alternative: use a known CSV source
        # This is a placeholder - in practice you'd use the actual Census files
        
        # For now, let's enhance our existing data with CBSA where we can infer it
        return create_cbsa_from_county()
        
    except Exception as e:
        print(f"Error downloading comprehensive CBSA data: {e}")
        return None

def main():
    """Main function to download CBSA crosswalk data."""
    print("Starting CBSA crosswalk download...")
    
    cbsa_df = None
    
    # Try different sources
    sources = [
        ('HUD CBSA', download_hud_cbsa_crosswalk),
        ('Census CBSA', download_census_cbsa_crosswalk),
        ('County-based CBSA', create_cbsa_from_county),
        ('Comprehensive CBSA', download_comprehensive_cbsa_data)
    ]
    
    for source_name, download_func in sources:
        print(f"\n--- Trying {source_name} ---")
        try:
            cbsa_df = download_func()
            if cbsa_df is not None and not cbsa_df.empty:
                print(f"Successfully obtained CBSA data from {source_name}")
                print(f"Shape: {cbsa_df.shape}")
                print(f"Columns: {list(cbsa_df.columns)}")
                break
        except Exception as e:
            print(f"Error with {source_name}: {e}")
    
    if cbsa_df is not None and not cbsa_df.empty:
        # Save the CBSA data
        cbsa_df.to_csv('zip_cbsa_crosswalk.csv', index=False)
        print(f"\nSaved CBSA crosswalk to zip_cbsa_crosswalk.csv")
        print(f"Records with CBSA data: {cbsa_df['cbsa_code'].notna().sum()}")
        
        # Show sample
        print("\nSample CBSA data:")
        print(cbsa_df.head())
        
        return cbsa_df
    else:
        print("Failed to obtain CBSA data")
        return None

if __name__ == "__main__":
    main()
