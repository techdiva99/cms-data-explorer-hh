#!/usr/bin/env python3
"""
Download and process ZIP code to county crosswalk data from reliable sources.
"""

import pandas as pd
import requests
import sqlite3
import sys
from io import StringIO
import zipfile
import tempfile
import os

def download_hud_crosswalk():
    """Download HUD USPS ZIP Code Crosswalk data."""
    print("Attempting to download HUD crosswalk data...")
    
    # Try multiple HUD URLs (different quarters)
    hud_urls = [
        "https://www.huduser.gov/portal/datasets/usps/ZIP_COUNTY_062024.xlsx",
        "https://www.huduser.gov/portal/datasets/usps/ZIP_COUNTY_032024.xlsx",
        "https://www.huduser.gov/portal/datasets/usps/ZIP_COUNTY_122023.xlsx",
    ]
    
    for url in hud_urls:
        try:
            print(f"Trying {url}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open("hud_crosswalk.xlsx", "wb") as f:
                    f.write(response.content)
                print(f"Successfully downloaded from {url}")
                return pd.read_excel("hud_crosswalk.xlsx")
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            continue
    
    return None

def download_census_zcta():
    """Download Census ZCTA to County relationship file."""
    print("Attempting to download Census ZCTA data...")
    
    urls = [
        "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt",
        "https://www2.census.gov/geo/docs/maps-data/data/rel/zcta_county_rel_10.txt"
    ]
    
    for url in urls:
        try:
            print(f"Trying {url}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Census files are typically tab-delimited
                df = pd.read_csv(StringIO(response.text), sep='\t' if 'tab20' in url else ',')
                print(f"Successfully downloaded Census data from {url}")
                return df
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            continue
    
    return None

def download_simplemaps():
    """Download SimpleMaps ZIP code database."""
    print("Attempting to download SimpleMaps data...")
    
    try:
        # Free version URL
        url = "https://simplemaps.com/static/data/us-zips/1.82/basic/simplemaps_uszips_basicv1.82.zip"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Save and extract zip file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()
                
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall('.')
                
                # Find the CSV file
                for file in os.listdir('.'):
                    if file.endswith('.csv') and 'uszips' in file.lower():
                        df = pd.read_csv(file)
                        print(f"Successfully downloaded SimpleMaps data")
                        return df
                        
        print("No CSV file found in SimpleMaps download")
        return None
        
    except Exception as e:
        print(f"Failed to download SimpleMaps data: {e}")
        return None

def create_manual_crosswalk():
    """Create a basic ZIP to county crosswalk using known data patterns."""
    print("Creating manual crosswalk from existing data...")
    
    try:
        # Connect to existing database
        conn = sqlite3.connect('cms_homehealth.db')
        
        # Get unique ZIP codes from existing data
        query = """
        SELECT DISTINCT zip_code 
        FROM providers 
        WHERE zip_code IS NOT NULL 
        AND LENGTH(zip_code) = 5
        """
        
        existing_zips = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Found {len(existing_zips)} unique ZIP codes in existing data")
        
        # Create a basic structure for now - we'll enhance this
        crosswalk_data = []
        for _, row in existing_zips.iterrows():
            zip_code = row['zip_code']
            
            # Basic state inference from ZIP code ranges (this is approximate)
            zip_int = int(zip_code)
            state_abbr = infer_state_from_zip(zip_int)
            
            crosswalk_data.append({
                'zip': zip_code,
                'state': state_abbr,
                'county': None,  # Will be populated later
                'county_fips': None,
                'lat': None,
                'lng': None,
                'data_source': 'manual_inference'
            })
        
        return pd.DataFrame(crosswalk_data)
        
    except Exception as e:
        print(f"Error creating manual crosswalk: {e}")
        return None

def infer_state_from_zip(zip_code):
    """Basic state inference from ZIP code ranges."""
    zip_state_ranges = {
        (1, 2999): 'MA', (3000, 3899): 'NH', (4000, 4999): 'ME',
        (5000, 5999): 'VT', (6000, 6999): 'CT', (7000, 8999): 'NJ',
        (10000, 14999): 'NY', (15000, 19999): 'PA', (20000, 20599): 'DC',
        (20600, 21999): 'MD', (22000, 24699): 'VA', (24700, 26999): 'WV',
        (27000, 28999): 'NC', (29000, 29999): 'SC', (30000, 31999): 'GA',
        (32000, 34999): 'FL', (35000, 36999): 'AL', (37000, 38599): 'TN',
        (38600, 39999): 'MS', (40000, 42799): 'KY', (43000, 45999): 'OH',
        (46000, 47999): 'IN', (48000, 49999): 'MI', (50000, 52999): 'IA',
        (53000, 54999): 'WI', (55000, 56799): 'MN', (57000, 57999): 'SD',
        (58000, 58999): 'ND', (59000, 59999): 'MT', (60000, 62999): 'IL',
        (63000, 65999): 'MO', (66000, 67999): 'KS', (68000, 69999): 'NE',
        (70000, 71599): 'LA', (71600, 72999): 'AR', (73000, 74999): 'OK',
        (75000, 79999): 'TX', (80000, 81999): 'CO', (82000, 83199): 'WY',
        (83200, 83899): 'ID', (84000, 84999): 'UT', (85000, 86599): 'AZ',
        (87000, 88499): 'NM', (88500, 89999): 'NV', (90000, 96199): 'CA',
        (96700, 96999): 'HI', (97000, 97999): 'OR', (98000, 99999): 'WA'
    }
    
    for (start, end), state in zip_state_ranges.items():
        if start <= zip_code <= end:
            return state
    
    return 'Unknown'

def main():
    """Main function to download and process crosswalk data."""
    print("Starting ZIP code to county crosswalk download and processing...")
    
    crosswalk_df = None
    
    # Try different sources in order of preference
    sources = [
        ('HUD', download_hud_crosswalk),
        ('Census', download_census_zcta),
        ('SimpleMaps', download_simplemaps),
        ('Manual', create_manual_crosswalk)
    ]
    
    for source_name, download_func in sources:
        print(f"\n--- Trying {source_name} source ---")
        try:
            crosswalk_df = download_func()
            if crosswalk_df is not None and not crosswalk_df.empty:
                print(f"Successfully obtained data from {source_name}")
                print(f"Shape: {crosswalk_df.shape}")
                print(f"Columns: {list(crosswalk_df.columns)}")
                break
        except Exception as e:
            print(f"Error with {source_name} source: {e}")
            continue
    
    if crosswalk_df is None or crosswalk_df.empty:
        print("Failed to obtain crosswalk data from any source")
        sys.exit(1)
    
    # Save the raw data
    crosswalk_df.to_csv('zip_county_crosswalk_raw.csv', index=False)
    print(f"\nSaved raw crosswalk data to zip_county_crosswalk_raw.csv")
    print(f"Downloaded {len(crosswalk_df)} records")
    
    return crosswalk_df

if __name__ == "__main__":
    main()
