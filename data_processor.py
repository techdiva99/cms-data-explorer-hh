import pandas as pd
import numpy as np
import sqlite3
import os
from typing import Dict, List, Tuple, Optional
import re
from geopy.geocoders import Nominatim
import time

class CMSDataProcessor:
    """
    Comprehensive CMS Home Health data processor that merges quality metrics,
    provider information, and calculates market analytics.
    """
    
    def __init__(self, data_dir: str, db_path: str = "cms_homehealth.db"):
        self.data_dir = data_dir
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.geocoder = Nominatim(user_agent="cms_data_explorer")
        
    def load_raw_data(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV files into dataframes"""
        print("Loading raw data files...")
        
        data_files = {
            'hhcahps_provider': 'HHCAHPS_Provider_Apr2025.csv',
            'hh_provider': 'HH_Provider_Apr2025.csv', 
            'hh_zip': 'HH_Zip_Apr2025.csv',
            'hhcahps_state': 'HHCAHPS_State_Apr2025.csv',
            'hh_national': 'HH_National_Apr2025.csv',
            'state_county_penetration': 'State_County_Penetration_MA_2025_06.csv'
        }
        
        dataframes = {}
        for key, filename in data_files.items():
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, low_memory=False)
                    dataframes[key] = df
                    print(f"✓ Loaded {key}: {len(df)} rows")
                except Exception as e:
                    print(f"✗ Error loading {filename}: {e}")
            else:
                print(f"✗ File not found: {filename}")
                
        return dataframes
    
    def clean_and_standardize_data(self, dataframes: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Clean and standardize the data"""
        print("Cleaning and standardizing data...")
        
        # Clean HHCAHPS Provider data
        if 'hhcahps_provider' in dataframes:
            df = dataframes['hhcahps_provider'].copy()
            
            # Convert numeric columns
            numeric_cols = [
                'HHCAHPS Survey Summary Star Rating',
                'Number of completed Surveys',
                'Survey response rate'
            ]
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Clean CCN
            df['CCN'] = df['CMS Certification Number (CCN)'].astype(str).str.zfill(6)
            
            dataframes['hhcahps_provider'] = df
            
        # Clean HH Provider data
        if 'hh_provider' in dataframes:
            df = dataframes['hh_provider'].copy()
            
            # Clean CCN
            df['CCN'] = df['CMS Certification Number (CCN)'].astype(str).str.zfill(6)
            
            # Convert quality rating
            df['Quality of patient care star rating'] = pd.to_numeric(
                df['Quality of patient care star rating'], errors='coerce'
            )
            
            # Clean ZIP codes
            df['ZIP Code'] = df['ZIP Code'].astype(str).str.replace('-', '').str[:5]
            
            dataframes['hh_provider'] = df
            
        # Clean ZIP data
        if 'hh_zip' in dataframes:
            df = dataframes['hh_zip'].copy()
            df['CCN'] = df['CMS Certification Number (CCN)'].astype(str).str.zfill(6)
            df['ZIP Code'] = df['ZIP Code'].astype(str).str.replace('-', '').str[:5]
            dataframes['hh_zip'] = df
            
        # Clean State County Penetration data
        if 'state_county_penetration' in dataframes:
            df = dataframes['state_county_penetration'].copy()
            
            # Convert enrollment numbers
            for col in ['Eligibles', 'Enrolled']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.replace('"', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert penetration percentage
            if 'Penetration' in df.columns:
                df['Penetration'] = df['Penetration'].str.replace('%', '').astype(float) / 100
                
            dataframes['state_county_penetration'] = df
            
        return dataframes
    
    def create_master_provider_dataset(self, dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Create the master provider dataset by merging all relevant data"""
        print("Creating master provider dataset...")
        
        # Start with provider info
        master_df = dataframes['hh_provider'].copy()
        
        # Merge with HHCAHPS quality data
        if 'hhcahps_provider' in dataframes:
            hhcahps_cols = [
                'CCN',
                'HHCAHPS Survey Summary Star Rating',
                'Number of completed Surveys', 
                'Survey response rate'
            ]
            hhcahps_df = dataframes['hhcahps_provider'][hhcahps_cols].copy()
            
            master_df = master_df.merge(hhcahps_df, on='CCN', how='left', suffixes=('', '_hhcahps'))
        
        # Add service area information (ZIP codes served)
        if 'hh_zip' in dataframes:
            zip_counts = dataframes['hh_zip'].groupby('CCN')['ZIP Code'].agg(['count', 'nunique']).reset_index()
            zip_counts.columns = ['CCN', 'total_zip_records', 'unique_zips_served']
            
            master_df = master_df.merge(zip_counts, on='CCN', how='left')
        
        return master_df
    
    def calculate_derived_metrics(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived metrics like patient volume and quality scores"""
        print("Calculating derived metrics...")
        
        df = master_df.copy()
        
        # Calculate estimated total patient volume
        df['estimated_total_patients'] = np.where(
            (df['Number of completed Surveys'].notna()) & 
            (df['Survey response rate'].notna()) & 
            (df['Survey response rate'] > 0),
            df['Number of completed Surveys'] / (df['Survey response rate'] / 100),
            np.nan
        )
        
        # Create composite quality score (average of available star ratings)
        quality_cols = [
            'Quality of patient care star rating',
            'HHCAHPS Survey Summary Star Rating'
        ]
        
        df['composite_quality_score'] = df[quality_cols].mean(axis=1, skipna=True)
        
        # Define high quality providers (>= 4.0 stars or top 25%)
        quality_threshold = df['composite_quality_score'].quantile(0.75)
        df['is_high_quality'] = (df['composite_quality_score'] >= 4.0) | \
                               (df['composite_quality_score'] >= quality_threshold)
        
        # Calculate provider size category
        df['provider_size_category'] = pd.cut(
            df['estimated_total_patients'],
            bins=[0, 100, 500, 1000, float('inf')],
            labels=['Small', 'Medium', 'Large', 'Very Large'],
            include_lowest=True
        )
        
        return df
    
    def add_geographic_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add county information and geographic coordinates"""
        print("Adding geographic data...")
        
        # Extract county from city or use geocoding
        df['county'] = None
        df['latitude'] = None
        df['longitude'] = None
        
        # Sample geocoding for a subset (due to rate limits)
        sample_size = min(100, len(df))
        sample_indices = df.sample(n=sample_size).index
        
        for idx in sample_indices:
            try:
                address = f"{df.loc[idx, 'City/Town']}, {df.loc[idx, 'State']}"
                location = self.geocoder.geocode(address)
                if location:
                    df.loc[idx, 'latitude'] = location.latitude
                    df.loc[idx, 'longitude'] = location.longitude
                    
                    # Try to extract county from raw address
                    raw_address = location.raw.get('display_name', '')
                    # Simple county extraction - this could be improved
                    if 'County' in raw_address:
                        county_match = re.search(r'([^,]+)\s+County', raw_address)
                        if county_match:
                            df.loc[idx, 'county'] = county_match.group(1).strip()
                            
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"Geocoding failed for {idx}: {e}")
                continue
                
        return df
    
    def calculate_market_share(self, df: pd.DataFrame, penetration_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate market share metrics"""
        print("Calculating market share metrics...")
        
        # For this example, we'll use state-level data since we don't have exact county mapping
        state_totals = penetration_df.groupby('State Name').agg({
            'Eligibles': 'sum',
            'Enrolled': 'sum'
        }).reset_index()
        
        # Merge with provider data
        df = df.merge(
            state_totals, 
            left_on='State', 
            right_on='State Name', 
            how='left'
        )
        
        # Calculate estimated market share
        df['estimated_market_share'] = np.where(
            df['Enrolled'].notna() & (df['Enrolled'] > 0),
            df['estimated_total_patients'] / df['Enrolled'],
            np.nan
        )
        
        return df
    
    def create_database_schema(self):
        """Create database tables"""
        print("Creating database schema...")
        
        # Main providers table
        providers_sql = """
        CREATE TABLE IF NOT EXISTS providers (
            ccn TEXT PRIMARY KEY,
            provider_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            phone TEXT,
            ownership_type TEXT,
            certification_date TEXT,
            offers_nursing BOOLEAN,
            offers_physical_therapy BOOLEAN,
            offers_occupational_therapy BOOLEAN,
            offers_speech_pathology BOOLEAN,
            offers_medical_social BOOLEAN,
            offers_home_health_aide BOOLEAN,
            quality_care_star_rating REAL,
            hhcahps_star_rating REAL,
            composite_quality_score REAL,
            is_high_quality BOOLEAN,
            number_completed_surveys INTEGER,
            survey_response_rate REAL,
            estimated_total_patients REAL,
            provider_size_category TEXT,
            unique_zips_served INTEGER,
            county TEXT,
            latitude REAL,
            longitude REAL,
            estimated_market_share REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Service areas table
        service_areas_sql = """
        CREATE TABLE IF NOT EXISTS service_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ccn TEXT,
            zip_code TEXT,
            FOREIGN KEY (ccn) REFERENCES providers (ccn)
        )
        """
        
        # County statistics table
        county_stats_sql = """
        CREATE TABLE IF NOT EXISTS county_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_name TEXT,
            county_name TEXT,
            fips TEXT,
            eligible_population INTEGER,
            enrolled_population INTEGER,
            penetration_rate REAL,
            total_providers INTEGER,
            high_quality_providers INTEGER,
            avg_quality_score REAL
        )
        """
        
        self.conn.execute(providers_sql)
        self.conn.execute(service_areas_sql)
        self.conn.execute(county_stats_sql)
        self.conn.commit()
    
    def save_to_database(self, master_df: pd.DataFrame, dataframes: Dict[str, pd.DataFrame]):
        """Save processed data to database"""
        print("Saving data to database...")
        
        # Save main providers data
        provider_columns = [
            'CCN', 'Provider Name', 'Address', 'City/Town', 'State', 'ZIP Code',
            'Telephone Number', 'Type of Ownership', 'Certification Date',
            'Offers Nursing Care Services', 'Offers Physical Therapy Services',
            'Offers Occupational Therapy Services', 'Offers Speech Pathology Services',
            'Offers Medical Social Services', 'Offers Home Health Aide Services',
            'Quality of patient care star rating', 'HHCAHPS Survey Summary Star Rating',
            'composite_quality_score', 'is_high_quality', 'Number of completed Surveys',
            'Survey response rate', 'estimated_total_patients', 'provider_size_category',
            'unique_zips_served', 'county', 'latitude', 'longitude', 'estimated_market_share'
        ]
        
        # Map to database column names
        column_mapping = {
            'CCN': 'ccn',
            'Provider Name': 'provider_name',
            'Address': 'address',
            'City/Town': 'city',
            'State': 'state',
            'ZIP Code': 'zip_code',
            'Telephone Number': 'phone',
            'Type of Ownership': 'ownership_type',
            'Certification Date': 'certification_date',
            'Offers Nursing Care Services': 'offers_nursing',
            'Offers Physical Therapy Services': 'offers_physical_therapy',
            'Offers Occupational Therapy Services': 'offers_occupational_therapy',
            'Offers Speech Pathology Services': 'offers_speech_pathology',
            'Offers Medical Social Services': 'offers_medical_social',
            'Offers Home Health Aide Services': 'offers_home_health_aide',
            'Quality of patient care star rating': 'quality_care_star_rating',
            'HHCAHPS Survey Summary Star Rating': 'hhcahps_star_rating',
            'Number of completed Surveys': 'number_completed_surveys',
            'Survey response rate': 'survey_response_rate'
        }
        
        # Prepare dataframe for database
        db_df = master_df[[col for col in provider_columns if col in master_df.columns]].copy()
        db_df = db_df.rename(columns=column_mapping)
        
        # Convert boolean columns
        boolean_cols = [col for col in db_df.columns if 'offers_' in col]
        for col in boolean_cols:
            db_df[col] = db_df[col].map({'Yes': True, 'No': False})
        
        db_df.to_sql('providers', self.conn, if_exists='replace', index=False)
        
        # Save service areas
        if 'hh_zip' in dataframes:
            service_areas_df = dataframes['hh_zip'][['CCN', 'ZIP Code']].copy()
            service_areas_df = service_areas_df.rename(columns={'CCN': 'ccn', 'ZIP Code': 'zip_code'})
            service_areas_df.to_sql('service_areas', self.conn, if_exists='replace', index=False)
        
        # Save county statistics
        if 'state_county_penetration' in dataframes:
            county_df = dataframes['state_county_penetration'].copy()
            county_df = county_df.rename(columns={
                'State Name': 'state_name',
                'County Name': 'county_name',
                'FIPS': 'fips',
                'Eligibles': 'eligible_population',
                'Enrolled': 'enrolled_population',
                'Penetration': 'penetration_rate'
            })
            county_df.to_sql('county_stats', self.conn, if_exists='replace', index=False)
        
        self.conn.commit()
        print("✓ Data saved to database successfully")
    
    def run_full_pipeline(self):
        """Run the complete data processing pipeline"""
        print("Starting CMS Home Health Data Processing Pipeline...")
        print("=" * 60)
        
        # Step 1: Load raw data
        dataframes = self.load_raw_data()
        
        # Step 2: Clean and standardize
        dataframes = self.clean_and_standardize_data(dataframes)
        
        # Step 3: Create master dataset
        master_df = self.create_master_provider_dataset(dataframes)
        
        # Step 4: Calculate derived metrics
        master_df = self.calculate_derived_metrics(master_df)
        
        # Step 5: Add geographic data (sample)
        master_df = self.add_geographic_data(master_df)
        
        # Step 6: Calculate market share
        if 'state_county_penetration' in dataframes:
            master_df = self.calculate_market_share(master_df, dataframes['state_county_penetration'])
        
        # Step 7: Create database
        self.create_database_schema()
        
        # Step 8: Save to database
        self.save_to_database(master_df, dataframes)
        
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print(f"Processed {len(master_df)} providers")
        print(f"Database saved to: {self.db_path}")
        
        return master_df

if __name__ == "__main__":
    # Initialize processor
    processor = CMSDataProcessor(data_dir="data")
    
    # Run the pipeline
    master_data = processor.run_full_pipeline()
    
    # Display summary statistics
    print("\nSummary Statistics:")
    print("-" * 30)
    print(f"Total providers: {len(master_data)}")
    print(f"High quality providers: {master_data['is_high_quality'].sum()}")
    print(f"Average quality score: {master_data['composite_quality_score'].mean():.2f}")
    print(f"States covered: {master_data['State'].nunique()}")
