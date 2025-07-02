#!/usr/bin/env python3
"""
Create comprehensive CBSA mappings and integrate into the database.
"""

import pandas as pd
import sqlite3
import json

def get_comprehensive_county_cbsa_mapping():
    """
    Create a comprehensive county FIPS to CBSA mapping.
    This includes major metropolitan and micropolitan statistical areas.
    """
    
    # Major CBSA mappings (county FIPS -> CBSA info)
    county_cbsa_mapping = {
        # New York Metro Area
        '36005': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '36047': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '36061': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '36081': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '36085': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34003': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34013': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34017': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34019': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34023': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34027': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34029': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34031': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34035': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34037': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '34039': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        '42103': {'cbsa_code': '35620', 'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'metro_type': 'Metropolitan'},
        
        # Los Angeles Metro Area
        '06037': {'cbsa_code': '31080', 'cbsa_name': 'Los Angeles-Long Beach-Anaheim, CA', 'metro_type': 'Metropolitan'},
        '06059': {'cbsa_code': '31080', 'cbsa_name': 'Los Angeles-Long Beach-Anaheim, CA', 'metro_type': 'Metropolitan'},
        
        # Chicago Metro Area
        '17031': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17043': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17089': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17093': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17097': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17111': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '17197': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '18089': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '18127': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        '55059': {'cbsa_code': '16980', 'cbsa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'metro_type': 'Metropolitan'},
        
        # Dallas-Fort Worth Metro Area
        '48085': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48113': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48121': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48139': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48157': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48231': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48257': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48397': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48439': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        '48497': {'cbsa_code': '19100', 'cbsa_name': 'Dallas-Fort Worth-Arlington, TX', 'metro_type': 'Metropolitan'},
        
        # Houston Metro Area
        '48015': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48039': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48071': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48157': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48201': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48291': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48339': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        '48473': {'cbsa_code': '26420', 'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX', 'metro_type': 'Metropolitan'},
        
        # Washington DC Metro Area
        '11001': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '24009': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '24017': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '24021': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '24031': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '24033': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51013': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51043': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51059': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51061': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51107': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51153': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51177': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51179': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51510': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51600': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '51610': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        '54037': {'cbsa_code': '47900', 'cbsa_name': 'Washington-Arlington-Alexandria, DC-VA-MD-WV', 'metro_type': 'Metropolitan'},
        
        # Philadelphia Metro Area
        '42017': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '42029': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '42045': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '42091': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '42101': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '34005': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '34007': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '34015': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '10003': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        '24015': {'cbsa_code': '37980', 'cbsa_name': 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD', 'metro_type': 'Metropolitan'},
        
        # Miami Metro Area
        '12011': {'cbsa_code': '33100', 'cbsa_name': 'Miami-Fort Lauderdale-West Palm Beach, FL', 'metro_type': 'Metropolitan'},
        '12086': {'cbsa_code': '33100', 'cbsa_name': 'Miami-Fort Lauderdale-West Palm Beach, FL', 'metro_type': 'Metropolitan'},
        '12099': {'cbsa_code': '33100', 'cbsa_name': 'Miami-Fort Lauderdale-West Palm Beach, FL', 'metro_type': 'Metropolitan'},
        
        # Phoenix Metro Area
        '04013': {'cbsa_code': '38060', 'cbsa_name': 'Phoenix-Mesa-Scottsdale, AZ', 'metro_type': 'Metropolitan'},
        '04021': {'cbsa_code': '38060', 'cbsa_name': 'Phoenix-Mesa-Scottsdale, AZ', 'metro_type': 'Metropolitan'},
        
        # Boston Metro Area
        '25009': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '25017': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '25021': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '25023': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '25025': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '33015': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        '33017': {'cbsa_code': '14460', 'cbsa_name': 'Boston-Cambridge-Newton, MA-NH', 'metro_type': 'Metropolitan'},
        
        # San Francisco Bay Area
        '06001': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA', 'metro_type': 'Metropolitan'},
        '06013': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA', 'metro_type': 'Metropolitan'},
        '06041': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA', 'metro_type': 'Metropolitan'},
        '06075': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA', 'metro_type': 'Metropolitan'},
        '06081': {'cbsa_code': '41860', 'cbsa_name': 'San Francisco-Oakland-Hayward, CA', 'metro_type': 'Metropolitan'},
        
        # Seattle Metro Area
        '53033': {'cbsa_code': '42660', 'cbsa_name': 'Seattle-Tacoma-Bellevue, WA', 'metro_type': 'Metropolitan'},
        '53053': {'cbsa_code': '42660', 'cbsa_name': 'Seattle-Tacoma-Bellevue, WA', 'metro_type': 'Metropolitan'},
        '53061': {'cbsa_code': '42660', 'cbsa_name': 'Seattle-Tacoma-Bellevue, WA', 'metro_type': 'Metropolitan'},
        
        # Additional major metros can be added here...
    }
    
    return county_cbsa_mapping

def integrate_cbsa_data():
    """Integrate CBSA data into the database."""
    print("Integrating CBSA data into database...")
    
    # Get comprehensive mapping
    county_cbsa_mapping = get_comprehensive_county_cbsa_mapping()
    
    # Connect to database
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    
    try:
        # Add CBSA columns to zip_county_crosswalk table
        cbsa_columns = [
            "ALTER TABLE zip_county_crosswalk ADD COLUMN cbsa_code TEXT",
            "ALTER TABLE zip_county_crosswalk ADD COLUMN cbsa_name TEXT", 
            "ALTER TABLE zip_county_crosswalk ADD COLUMN metro_type TEXT"
        ]
        
        for sql in cbsa_columns:
            try:
                conn.execute(sql)
                print(f"Added column: {sql}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Column already exists: {sql}")
                else:
                    print(f"Error: {e}")
        
        # Update crosswalk table with CBSA data
        update_count = 0
        for county_fips, cbsa_info in county_cbsa_mapping.items():
            update_sql = """
            UPDATE zip_county_crosswalk 
            SET 
                cbsa_code = ?,
                cbsa_name = ?,
                metro_type = ?
            WHERE primary_county_fips = ? OR primary_county_fips_main = ?
            """
            
            result = conn.execute(update_sql, [
                cbsa_info['cbsa_code'],
                cbsa_info['cbsa_name'], 
                cbsa_info['metro_type'],
                county_fips,
                county_fips
            ])
            
            if result.rowcount > 0:
                update_count += result.rowcount
        
        print(f"Updated {update_count} records with CBSA information")
        
        # Add CBSA columns to providers table
        provider_cbsa_columns = [
            "ALTER TABLE providers ADD COLUMN x_cbsa_code TEXT",
            "ALTER TABLE providers ADD COLUMN x_cbsa_name TEXT",
            "ALTER TABLE providers ADD COLUMN x_metro_type TEXT"
        ]
        
        for sql in provider_cbsa_columns:
            try:
                conn.execute(sql)
                print(f"Added provider column: {sql}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Provider column already exists: {sql}")
                else:
                    print(f"Error: {e}")
        
        # Update providers with CBSA data from crosswalk
        provider_update_sql = """
        UPDATE providers 
        SET 
            x_cbsa_code = (
                SELECT cbsa_code 
                FROM zip_county_crosswalk 
                WHERE zip_county_crosswalk.zip_code = providers.zip_code
                AND cbsa_code IS NOT NULL
            ),
            x_cbsa_name = (
                SELECT cbsa_name 
                FROM zip_county_crosswalk 
                WHERE zip_county_crosswalk.zip_code = providers.zip_code
                AND cbsa_name IS NOT NULL
            ),
            x_metro_type = (
                SELECT metro_type 
                FROM zip_county_crosswalk 
                WHERE zip_county_crosswalk.zip_code = providers.zip_code
                AND metro_type IS NOT NULL
            )
        WHERE EXISTS (
            SELECT 1 FROM zip_county_crosswalk 
            WHERE zip_county_crosswalk.zip_code = providers.zip_code
            AND cbsa_code IS NOT NULL
        )
        """
        
        conn.execute(provider_update_sql)
        conn.commit()
        
        # Check results
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_providers,
                COUNT(x_cbsa_code) as providers_with_cbsa,
                COUNT(DISTINCT x_cbsa_code) as unique_cbsas
            FROM providers
        """).fetchone()
        
        print(f"\nCBSA Integration Results:")
        print(f"Total providers: {result[0]}")
        print(f"Providers with CBSA: {result[1]}")
        print(f"Unique CBSAs represented: {result[2]}")
        
        # Show top CBSAs
        top_cbsas = conn.execute("""
            SELECT 
                x_cbsa_name,
                COUNT(*) as provider_count
            FROM providers 
            WHERE x_cbsa_name IS NOT NULL
            GROUP BY x_cbsa_name
            ORDER BY provider_count DESC
            LIMIT 10
        """).fetchall()
        
        print(f"\nTop CBSAs by Provider Count:")
        for cbsa_name, count in top_cbsas:
            print(f"  {cbsa_name}: {count} providers")
            
    finally:
        conn.close()

def main():
    """Main function."""
    print("Starting CBSA integration...")
    integrate_cbsa_data()
    print("✅ CBSA integration completed!")

if __name__ == "__main__":
    main()
