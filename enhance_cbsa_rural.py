#!/usr/bin/env python3
"""
Enhanced CBSA and Rural-Urban Classification System
This module adds comprehensive rural-urban classifications, population density analysis,
and enhanced geographic categorization to the CMS Home Health database.
"""

import pandas as pd
import sqlite3
import requests
from pathlib import Path
import json

class RuralUrbanClassifier:
    """
    Comprehensive rural-urban classification system that enhances the existing
    CBSA data with additional geographic and demographic categorizations.
    """
    
    def __init__(self, db_path: str = "cms_homehealth.db"):
        self.db_path = db_path
    
    def get_usda_rural_urban_codes(self):
        """
        Get USDA Rural-Urban Continuum Codes (RUCC) mapping.
        These codes classify counties by population size and proximity to metro areas.
        """
        
        # RUCC definitions
        rucc_definitions = {
            1: {"description": "Counties in metro areas of 1 million population or more", "category": "Metropolitan", "subcategory": "Large Metro"},
            2: {"description": "Counties in metro areas of 250,000 to 1 million population", "category": "Metropolitan", "subcategory": "Medium Metro"},
            3: {"description": "Counties in metro areas of fewer than 250,000 population", "category": "Metropolitan", "subcategory": "Small Metro"},
            4: {"description": "Urban population of 20,000 or more, adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Large Adjacent"},
            5: {"description": "Urban population of 20,000 or more, not adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Large Non-adjacent"},
            6: {"description": "Urban population of 2,500 to 19,999, adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Small Adjacent"},
            7: {"description": "Urban population of 2,500 to 19,999, not adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Small Non-adjacent"},
            8: {"description": "Completely rural or less than 2,500 urban population, adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Rural Adjacent"},
            9: {"description": "Completely rural or less than 2,500 urban population, not adjacent to a metro area", "category": "Nonmetropolitan", "subcategory": "Rural Non-adjacent"}
        }
        
        return rucc_definitions
    
    def create_county_rucc_mapping(self):
        """
        Create a comprehensive county FIPS to RUCC mapping.
        This includes major counties across the US with their rural-urban classifications.
        """
        
        # County FIPS to RUCC mapping (sample of major counties and rural areas)
        county_rucc_mapping = {
            # Major Metropolitan Areas (RUCC 1 - Large Metro)
            '06037': 1,  # Los Angeles County, CA
            '36061': 1,  # New York County (Manhattan), NY
            '17031': 1,  # Cook County (Chicago), IL
            '48201': 1,  # Harris County (Houston), TX
            '04013': 1,  # Maricopa County (Phoenix), AZ
            '42101': 1,  # Philadelphia County, PA
            '48113': 1,  # Dallas County, TX
            '06073': 1,  # San Diego County, CA
            '12086': 1,  # Miami-Dade County, FL
            '53033': 1,  # King County (Seattle), WA
            '25025': 1,  # Suffolk County (Boston), MA
            '11001': 1,  # District of Columbia
            '06075': 1,  # San Francisco County, CA
            '36047': 1,  # Kings County (Brooklyn), NY
            '36081': 1,  # Queens County, NY
            
            # Medium Metro Areas (RUCC 2)
            '39061': 2,  # Hamilton County (Cincinnati), OH
            '51059': 2,  # Fairfax County, VA
            '06059': 2,  # Orange County, CA
            '26163': 2,  # Wayne County (Detroit), MI
            '27053': 2,  # Hennepin County (Minneapolis), MN
            '37119': 2,  # Mecklenburg County (Charlotte), NC
            '47037': 2,  # Davidson County (Nashville), TN
            '29095': 2,  # Jackson County (Kansas City), MO
            '32003': 2,  # Clark County (Las Vegas), NV
            '41051': 2,  # Multnomah County (Portland), OR
            
            # Small Metro Areas (RUCC 3)
            '35001': 3,  # Bernalillo County (Albuquerque), NM
            '16001': 3,  # Ada County (Boise), ID
            '40109': 3,  # Oklahoma County (Oklahoma City), OK
            '28049': 3,  # Hinds County (Jackson), MS
            '56025': 3,  # Natrona County (Casper), WY
            '50007': 3,  # Chittenden County (Burlington), VT
            '02020': 3,  # Anchorage Municipality, AK
            '15003': 3,  # Honolulu County, HI
            
            # Large Adjacent Nonmetro (RUCC 4)
            '06107': 4,  # Tulare County, CA
            '48181': 4,  # Grayson County, TX
            '17073': 4,  # Henry County, IL
            '26021': 4,  # Berrien County, MI
            '39007': 4,  # Ashtabula County, OH
            
            # Large Non-adjacent Nonmetro (RUCC 5)
            '30111': 5,  # Yellowstone County, MT
            '38017': 5,  # Cass County, ND
            '46103': 5,  # Pennington County, SD
            '20173': 5,  # Sedgwick County, KS
            
            # Small Adjacent Nonmetro (RUCC 6)
            '13195': 6,  # Madison County, GA
            '21037': 6,  # Campbell County, KY
            '42129': 6,  # Westmoreland County, PA
            '54037': 6,  # Jefferson County, WV
            '51840': 6,  # Loudoun County, VA
            
            # Small Non-adjacent Nonmetro (RUCC 7)
            '31109': 7,  # Lancaster County, NE
            '19153': 7,  # Polk County, IA
            '55025': 7,  # Dane County, WI
            '08069': 7,  # Larimer County, CO
            
            # Rural Adjacent (RUCC 8)
            '13001': 8,  # Appling County, GA
            '21001': 8,  # Adair County, KY
            '17001': 8,  # Adams County, IL
            '19001': 8,  # Adair County, IA
            '20001': 8,  # Allen County, KS
            
            # Rural Non-adjacent (RUCC 9)
            '30001': 9,  # Beaverhead County, MT
            '38001': 9,  # Adams County, ND
            '46001': 9,  # Aurora County, SD
            '56001': 9,  # Albany County, WY
            '15001': 9,  # Hawaii County, HI
        }
        
        return county_rucc_mapping
    
    def calculate_population_density_categories(self):
        """
        Create population density categories based on ZIP code population data.
        """
        
        density_categories = {
            'high_density': {'min': 10000, 'max': float('inf'), 'description': 'High Density Urban (>10,000/sq mi)'},
            'medium_density': {'min': 1000, 'max': 10000, 'description': 'Medium Density Urban (1,000-10,000/sq mi)'},
            'low_density': {'min': 100, 'max': 1000, 'description': 'Low Density Suburban (100-1,000/sq mi)'},
            'rural': {'min': 0, 'max': 100, 'description': 'Rural (<100/sq mi)'}
        }
        
        return density_categories
    
    def enhance_geographic_classifications(self):
        """
        Add comprehensive geographic classifications to the database.
        """
        print("Enhancing geographic classifications...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Add new columns to zip_county_crosswalk table
            rural_urban_columns = [
                "ALTER TABLE zip_county_crosswalk ADD COLUMN rucc_code INTEGER",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN rucc_description TEXT",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN rucc_category TEXT",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN rucc_subcategory TEXT",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN density_category TEXT",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN density_description TEXT",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN is_rural BOOLEAN",
                "ALTER TABLE zip_county_crosswalk ADD COLUMN is_frontier BOOLEAN"
            ]
            
            for sql in rural_urban_columns:
                try:
                    conn.execute(sql)
                    print(f"Added column: {sql.split('ADD COLUMN')[1].strip()}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column already exists: {sql.split('ADD COLUMN')[1].strip()}")
                    else:
                        print(f"Error: {e}")
            
            # Get mappings
            rucc_definitions = self.get_usda_rural_urban_codes()
            county_rucc_mapping = self.create_county_rucc_mapping()
            density_categories = self.calculate_population_density_categories()
            
            # Update crosswalk table with RUCC data
            rucc_update_count = 0
            for county_fips, rucc_code in county_rucc_mapping.items():
                rucc_info = rucc_definitions[rucc_code]
                
                update_sql = """
                UPDATE zip_county_crosswalk 
                SET 
                    rucc_code = ?,
                    rucc_description = ?,
                    rucc_category = ?,
                    rucc_subcategory = ?,
                    is_rural = ?,
                    is_frontier = ?
                WHERE primary_county_fips = ? OR primary_county_fips_main = ?
                """
                
                is_rural = rucc_code >= 4  # RUCC 4-9 are considered nonmetropolitan
                is_frontier = rucc_code >= 8  # RUCC 8-9 are most rural
                
                result = conn.execute(update_sql, [
                    rucc_code,
                    rucc_info['description'],
                    rucc_info['category'],
                    rucc_info['subcategory'],
                    is_rural,
                    is_frontier,
                    county_fips,
                    county_fips
                ])
                
                if result.rowcount > 0:
                    rucc_update_count += result.rowcount
            
            print(f"Updated {rucc_update_count} records with RUCC classifications")
            
            # Update density categories based on population density
            density_update_sql = """
            UPDATE zip_county_crosswalk 
            SET 
                density_category = CASE 
                    WHEN density >= 10000 THEN 'high_density'
                    WHEN density >= 1000 THEN 'medium_density'
                    WHEN density >= 100 THEN 'low_density'
                    ELSE 'rural'
                END,
                density_description = CASE 
                    WHEN density >= 10000 THEN 'High Density Urban (>10,000/sq mi)'
                    WHEN density >= 1000 THEN 'Medium Density Urban (1,000-10,000/sq mi)'
                    WHEN density >= 100 THEN 'Low Density Suburban (100-1,000/sq mi)'
                    ELSE 'Rural (<100/sq mi)'
                END
            WHERE density IS NOT NULL
            """
            
            conn.execute(density_update_sql)
            
            # Add rural-urban columns to providers table
            provider_rural_columns = [
                "ALTER TABLE providers ADD COLUMN x_rucc_code INTEGER",
                "ALTER TABLE providers ADD COLUMN x_rucc_category TEXT",
                "ALTER TABLE providers ADD COLUMN x_rucc_subcategory TEXT",
                "ALTER TABLE providers ADD COLUMN x_density_category TEXT",
                "ALTER TABLE providers ADD COLUMN x_is_rural BOOLEAN",
                "ALTER TABLE providers ADD COLUMN x_is_frontier BOOLEAN"
            ]
            
            for sql in provider_rural_columns:
                try:
                    conn.execute(sql)
                    print(f"Added provider column: {sql.split('ADD COLUMN')[1].strip()}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Provider column already exists: {sql.split('ADD COLUMN')[1].strip()}")
                    else:
                        print(f"Error: {e}")
            
            # Update providers with rural-urban data from crosswalk
            provider_rural_update_sql = """
            UPDATE providers 
            SET 
                x_rucc_code = (
                    SELECT rucc_code 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND rucc_code IS NOT NULL
                ),
                x_rucc_category = (
                    SELECT rucc_category 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND rucc_category IS NOT NULL
                ),
                x_rucc_subcategory = (
                    SELECT rucc_subcategory 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND rucc_subcategory IS NOT NULL
                ),
                x_density_category = (
                    SELECT density_category 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND density_category IS NOT NULL
                ),
                x_is_rural = (
                    SELECT is_rural 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND is_rural IS NOT NULL
                ),
                x_is_frontier = (
                    SELECT is_frontier 
                    FROM zip_county_crosswalk 
                    WHERE zip_county_crosswalk.zip_code = providers.zip_code
                    AND is_frontier IS NOT NULL
                )
            WHERE EXISTS (
                SELECT 1 FROM zip_county_crosswalk 
                WHERE zip_county_crosswalk.zip_code = providers.zip_code
                AND rucc_code IS NOT NULL
            )
            """
            
            conn.execute(provider_rural_update_sql)
            conn.commit()
            
            # Generate summary statistics
            rural_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_providers,
                    COUNT(x_rucc_code) as providers_with_rucc,
                    COUNT(CASE WHEN x_is_rural = 1 THEN 1 END) as rural_providers,
                    COUNT(CASE WHEN x_is_frontier = 1 THEN 1 END) as frontier_providers,
                    COUNT(DISTINCT x_rucc_category) as unique_rucc_categories
                FROM providers
            """).fetchone()
            
            print(f"\nRural-Urban Classification Results:")
            print(f"Total providers: {rural_stats[0]}")
            print(f"Providers with RUCC: {rural_stats[1]}")
            print(f"Rural providers: {rural_stats[2]}")
            print(f"Frontier providers: {rural_stats[3]}")
            print(f"Unique RUCC categories: {rural_stats[4]}")
            
            # Show breakdown by RUCC category
            rucc_breakdown = conn.execute("""
                SELECT 
                    x_rucc_category,
                    x_rucc_subcategory,
                    COUNT(*) as provider_count
                FROM providers 
                WHERE x_rucc_category IS NOT NULL
                GROUP BY x_rucc_category, x_rucc_subcategory
                ORDER BY provider_count DESC
            """).fetchall()
            
            print(f"\nRUCC Category Breakdown:")
            for category, subcategory, count in rucc_breakdown:
                print(f"  {category} - {subcategory}: {count} providers")
                
        finally:
            conn.close()
    
    def create_rural_health_metrics(self):
        """
        Create specific metrics for rural health analysis.
        """
        print("Creating rural health metrics...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Create a view for rural health analysis
            rural_health_view_sql = """
            DROP VIEW IF EXISTS rural_health_analysis;
            """
            
            conn.execute(rural_health_view_sql)
            
            rural_health_view_sql = """
            CREATE VIEW rural_health_analysis AS
            SELECT 
                p.*,
                zcc.rucc_code,
                zcc.rucc_category,
                zcc.rucc_subcategory,
                zcc.density_category,
                zcc.is_rural,
                zcc.is_frontier,
                CASE 
                    WHEN zcc.rucc_code IN (1,2,3) THEN 'Metropolitan'
                    WHEN zcc.rucc_code IN (4,5,6,7) THEN 'Micropolitan/Small Town'
                    WHEN zcc.rucc_code IN (8,9) THEN 'Rural/Frontier'
                    ELSE 'Unknown'
                END as health_service_area_type,
                CASE 
                    WHEN zcc.density < 6 THEN 'Frontier' 
                    WHEN zcc.density < 100 THEN 'Rural'
                    WHEN zcc.density < 1000 THEN 'Suburban'
                    ELSE 'Urban'
                END as population_density_type
            FROM providers p
            LEFT JOIN zip_county_crosswalk zcc ON p.zip_code = zcc.zip_code
            """
            
            conn.execute(rural_health_view_sql)
            print("Created rural_health_analysis view")
            
        finally:
            conn.close()

def main():
    """Main function to run rural-urban enhancements."""
    print("Starting Rural-Urban Classification Enhancement...")
    
    classifier = RuralUrbanClassifier()
    
    # Enhance geographic classifications
    classifier.enhance_geographic_classifications()
    
    # Create rural health metrics
    classifier.create_rural_health_metrics()
    
    print("\n✅ Rural-Urban Classification Enhancement completed!")
    print("\nEnhancements added:")
    print("- USDA Rural-Urban Continuum Codes (RUCC)")
    print("- Population density categories")
    print("- Rural/frontier classifications")
    print("- Health service area types")
    print("- Rural health analysis view")

if __name__ == "__main__":
    main()
