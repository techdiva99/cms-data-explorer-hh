import sqlite3
import pandas as pd
from typing import List, Dict, Tuple, Optional
import numpy as np

class CMSAnalytics:
    """
    Analytics module for CMS Home Health data with functions to support
    geographic queries, market analysis, and quality comparisons.
    """
    
    def __init__(self, db_path: str = "cms_homehealth.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get a new database connection for thread safety"""
        return sqlite3.connect(self.db_path)
    
    def find_providers_by_location(self, 
                                 zip_code: Optional[str] = None,
                                 city: Optional[str] = None, 
                                 county: Optional[str] = None,
                                 state: Optional[str] = None,
                                 provider_name: Optional[str] = None,
                                 ccn: Optional[str] = None,
                                 high_quality_only: bool = False,
                                 radius_miles: Optional[float] = None) -> pd.DataFrame:
        """
        Find providers by geographic location with various filter options.
        """
        
        base_query = """
        SELECT DISTINCT p.*
        FROM providers p
        LEFT JOIN service_areas sa ON p.ccn = sa.ccn
        WHERE 1=1
        """
        
        conditions = []
        params = []
        
        if zip_code:
            conditions.append("(p.zip_code = ? OR sa.zip_code = ?)")
            params.extend([zip_code, zip_code])
            
        if city:
            conditions.append("LOWER(p.city) LIKE LOWER(?)")
            params.append(f"%{city}%")
            
        if county:
            conditions.append("(LOWER(COALESCE(p.county, p.x_county)) LIKE LOWER(?))")
            params.append(f"%{county}%")
            
        if state:
            conditions.append("UPPER(p.state) = UPPER(?)")
            params.append(state)
            
        if provider_name:
            conditions.append("LOWER(p.provider_name) LIKE LOWER(?)")
            params.append(f"%{provider_name}%")
            
        if ccn:
            conditions.append("LOWER(p.ccn) LIKE LOWER(?)")
            params.append(f"%{ccn}%")
            
        if high_quality_only:
            conditions.append("p.is_high_quality = 1")
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
            
        base_query += " ORDER BY p.composite_quality_score DESC"
        
        conn = self._get_connection()
        try:
            result = pd.read_sql_query(base_query, conn, params=params)
        finally:
            conn.close()
        return result
    
    def get_market_analysis(self, county: str, state: str) -> Dict:
        """
        Get comprehensive market analysis for a specific county.
        """
        
        conn = self._get_connection()
        try:
            # Get county statistics
            county_query = """
            SELECT * FROM county_stats 
            WHERE LOWER(county_name) = LOWER(?) AND LOWER(state_name) = LOWER(?)
            """
            
            county_stats = pd.read_sql_query(county_query, conn, params=[county, state])
            
            # Get providers in the county/area
            providers_query = """
            SELECT * FROM providers 
            WHERE (LOWER(COALESCE(county, x_county)) LIKE LOWER(?) AND UPPER(state) = UPPER(?))
               OR (LOWER(city) LIKE LOWER(?) AND UPPER(state) = UPPER(?))
            ORDER BY composite_quality_score DESC
            """
            
            providers = pd.read_sql_query(
                providers_query, 
                conn, 
                params=[f"%{county}%", state, f"%{county}%", state]
            )
        finally:
            conn.close()
        
        # Calculate market metrics
        total_providers = len(providers)
        high_quality_providers = providers['is_high_quality'].sum()
        avg_quality = providers['composite_quality_score'].mean()
        total_estimated_patients = providers['estimated_total_patients'].sum()
        
        # Market concentration (HHI-like measure)
        market_shares = providers['estimated_total_patients'] / total_estimated_patients
        market_concentration = (market_shares ** 2).sum()
        
        # Top providers by market share
        top_providers = providers.nlargest(5, 'estimated_total_patients')[
            ['provider_name', 'composite_quality_score', 'estimated_total_patients', 'estimated_market_share']
        ]
        
        return {
            'county_stats': county_stats.to_dict('records')[0] if not county_stats.empty else {},
            'total_providers': total_providers,
            'high_quality_providers': int(high_quality_providers),
            'high_quality_percentage': (high_quality_providers / total_providers * 100) if total_providers > 0 else 0,
            'average_quality_score': float(avg_quality) if not pd.isna(avg_quality) else None,
            'total_estimated_patients': float(total_estimated_patients) if not pd.isna(total_estimated_patients) else 0,
            'market_concentration_index': float(market_concentration) if not pd.isna(market_concentration) else 0,
            'top_providers': top_providers.to_dict('records'),
            'all_providers': providers.to_dict('records')
        }
    
    def get_competitor_analysis(self, ccn: str, radius_type: str = "state") -> Dict:
        """
        Get competitor analysis for a specific provider.
        radius_type: 'state', 'county', or 'city'
        """
        
        conn = self._get_connection()
        try:
            # Get the target provider
            provider_query = "SELECT * FROM providers WHERE ccn = ?"
            target_provider = pd.read_sql_query(provider_query, conn, params=[ccn])
            
            if target_provider.empty:
                return {"error": "Provider not found"}
            
            provider = target_provider.iloc[0]
            
            # Get competitors based on radius type
            if radius_type == "state":
                competitors_query = """
                SELECT * FROM providers 
                WHERE state = ? AND ccn != ?
                ORDER BY composite_quality_score DESC
                """
                competitors = pd.read_sql_query(
                    competitors_query, 
                    conn, 
                    params=[provider['state'], ccn]
                )
            elif radius_type == "county":
                competitors_query = """
                SELECT * FROM providers 
                WHERE county = ? AND state = ? AND ccn != ?
                ORDER BY composite_quality_score DESC
                """
                competitors = pd.read_sql_query(
                    competitors_query, 
                    conn, 
                    params=[provider['county'], provider['state'], ccn]
                )
            else:  # city
                competitors_query = """
                SELECT * FROM providers 
                WHERE city = ? AND state = ? AND ccn != ?
                ORDER BY composite_quality_score DESC
                """
                competitors = pd.read_sql_query(
                    competitors_query, 
                    conn, 
                    params=[provider['city'], provider['state'], ccn]
                )
        finally:
            conn.close()
        
        # Calculate competitive metrics
        provider_rank = 1
        better_competitors = 0
        total_competitors = len(competitors)
        
        if not competitors.empty:
            provider_rank = (competitors['composite_quality_score'] > provider['composite_quality_score']).sum() + 1
            better_competitors = (competitors['composite_quality_score'] > provider['composite_quality_score']).sum()
        
        # Market share comparison
        total_market_patients = competitors['estimated_total_patients'].sum() + provider['estimated_total_patients']
        provider_market_share = provider['estimated_total_patients'] / total_market_patients if total_market_patients > 0 else 0
        
        # Top competitors
        top_competitors = competitors.head(10)[
            ['provider_name', 'composite_quality_score', 'estimated_total_patients', 'city']
        ]
        
        return {
            'target_provider': {
                'name': provider['provider_name'],
                'quality_score': provider['composite_quality_score'],
                'estimated_patients': provider['estimated_total_patients'],
                'rank': int(provider_rank),
                'market_share': float(provider_market_share)
            },
            'competitive_landscape': {
                'total_competitors': total_competitors,
                'better_competitors': int(better_competitors),
                'percentile_rank': ((total_competitors - provider_rank + 1) / total_competitors * 100) if total_competitors > 0 else 100
            },
            'top_competitors': top_competitors.to_dict('records')
        }
    
    def get_quality_benchmarks(self, state: Optional[str] = None) -> Dict:
        """
        Get quality benchmarks and statistics.
        """
        
        base_query = "SELECT * FROM providers WHERE composite_quality_score IS NOT NULL"
        params = []
        
        if state:
            base_query += " AND UPPER(state) = UPPER(?)"
            params.append(state)
        
        conn = self._get_connection()
        try:
            providers = pd.read_sql_query(base_query, conn, params=params)
        finally:
            conn.close()
        
        if providers.empty:
            return {"error": "No data available"}
        
        # Calculate percentiles and statistics
        quality_scores = providers['composite_quality_score'].dropna()
        
        benchmarks = {
            'total_providers': len(providers),
            'mean_quality': float(quality_scores.mean()),
            'median_quality': float(quality_scores.median()),
            'std_quality': float(quality_scores.std()),
            'percentiles': {
                '10th': float(quality_scores.quantile(0.1)),
                '25th': float(quality_scores.quantile(0.25)),
                '50th': float(quality_scores.quantile(0.5)),
                '75th': float(quality_scores.quantile(0.75)),
                '90th': float(quality_scores.quantile(0.9)),
                '95th': float(quality_scores.quantile(0.95))
            },
            'quality_distribution': {
                '5_star': int((quality_scores >= 4.5).sum()),
                '4_star': int(((quality_scores >= 3.5) & (quality_scores < 4.5)).sum()),
                '3_star': int(((quality_scores >= 2.5) & (quality_scores < 3.5)).sum()),
                '2_star': int(((quality_scores >= 1.5) & (quality_scores < 2.5)).sum()),
                '1_star': int((quality_scores < 1.5).sum())
            }
        }
        
        return benchmarks
    
    def search_providers_by_criteria(self, 
                                   min_quality_score: Optional[float] = None,
                                   max_quality_score: Optional[float] = None,
                                   min_patient_volume: Optional[int] = None,
                                   ownership_type: Optional[str] = None,
                                   services_offered: Optional[List[str]] = None,
                                   states: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Advanced search for providers based on multiple criteria.
        """
        
        query = "SELECT * FROM providers WHERE 1=1"
        params = []
        
        if min_quality_score is not None:
            query += " AND composite_quality_score >= ?"
            params.append(min_quality_score)
        
        if max_quality_score is not None:
            query += " AND composite_quality_score <= ?"
            params.append(max_quality_score)
        
        if min_patient_volume is not None:
            query += " AND estimated_total_patients >= ?"
            params.append(min_patient_volume)
        
        if ownership_type:
            query += " AND LOWER(ownership_type) LIKE LOWER(?)"
            params.append(f"%{ownership_type}%")
        
        if services_offered:
            for service in services_offered:
                if service.lower() == 'nursing':
                    query += " AND offers_nursing = 1"
                elif service.lower() == 'physical_therapy':
                    query += " AND offers_physical_therapy = 1"
                elif service.lower() == 'occupational_therapy':
                    query += " AND offers_occupational_therapy = 1"
                elif service.lower() == 'speech_pathology':
                    query += " AND offers_speech_pathology = 1"
                elif service.lower() == 'medical_social':
                    query += " AND offers_medical_social = 1"
                elif service.lower() == 'home_health_aide':
                    query += " AND offers_home_health_aide = 1"
        
        if states:
            placeholders = ','.join(['?' for _ in states])
            query += f" AND UPPER(state) IN ({placeholders})"
            params.extend([state.upper() for state in states])
        
        query += " ORDER BY composite_quality_score DESC"
        
        conn = self._get_connection()
        try:
            result = pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
        return result
    
    def get_geographic_coverage_analysis(self, ccn: str) -> Dict:
        """
        Analyze the geographic coverage of a specific provider.
        """
        
        conn = self._get_connection()
        try:
            # Get provider info
            provider_query = "SELECT * FROM providers WHERE ccn = ?"
            provider = pd.read_sql_query(provider_query, conn, params=[ccn])
            
            if provider.empty:
                return {"error": "Provider not found"}
        
            # Get service areas
            coverage_query = """
            SELECT sa.zip_code, p.city, p.state 
            FROM service_areas sa
            JOIN providers p ON sa.ccn = p.ccn
            WHERE sa.ccn = ?
            """
            
            coverage = pd.read_sql_query(coverage_query, conn, params=[ccn])
        finally:
            conn.close()
        
        # Calculate coverage statistics
        unique_zips = coverage['zip_code'].nunique()
        unique_cities = coverage['city'].nunique() if 'city' in coverage.columns else 0
        states_covered = coverage['state'].nunique() if 'state' in coverage.columns else 0
        
        return {
            'provider_name': provider.iloc[0]['provider_name'],
            'home_base': {
                'city': provider.iloc[0]['city'],
                'state': provider.iloc[0]['state'],
                'zip': provider.iloc[0]['zip_code']
            },
            'coverage_stats': {
                'total_zip_codes': unique_zips,
                'total_cities': unique_cities,
                'total_states': states_covered
            },
            'zip_codes_served': coverage['zip_code'].tolist() if not coverage.empty else []
        }
    
    def close(self):
        """Close database connection - no longer needed with per-method connections"""
        pass

    def get_provider_comparison_analysis(self, ccn: str, comparison_scope: str = "state") -> Dict:
        """
        Get detailed provider comparison with competitors including distribution analysis.
        comparison_scope: 'state', 'county', or 'national'
        """
        
        conn = self._get_connection()
        try:
            # Get the target provider
            provider_query = "SELECT * FROM providers WHERE ccn = ?"
            target_provider = pd.read_sql_query(provider_query, conn, params=[ccn])
            
            if target_provider.empty:
                return {"error": "Provider not found"}
            
            provider = target_provider.iloc[0]
            
            # Get comparison group based on scope
            if comparison_scope == "national":
                comparison_query = """
                SELECT * FROM providers 
                WHERE composite_quality_score IS NOT NULL
                ORDER BY composite_quality_score DESC
                """
                comparison_providers = pd.read_sql_query(comparison_query, conn)
            elif comparison_scope == "county":
                comparison_query = """
                SELECT * FROM providers 
                WHERE county = ? AND state = ? AND composite_quality_score IS NOT NULL
                ORDER BY composite_quality_score DESC
                """
                comparison_providers = pd.read_sql_query(
                    comparison_query, conn, 
                    params=[provider['county'], provider['state']]
                )
            else:  # state
                comparison_query = """
                SELECT * FROM providers 
                WHERE state = ? AND composite_quality_score IS NOT NULL
                ORDER BY composite_quality_score DESC
                """
                comparison_providers = pd.read_sql_query(
                    comparison_query, conn, 
                    params=[provider['state']]
                )
        finally:
            conn.close()
        
        # Calculate statistics
        quality_scores = comparison_providers['composite_quality_score'].dropna()
        provider_quality = provider['composite_quality_score']
        
        # Handle case where provider quality score is None
        if provider_quality is None:
            return {"error": "Provider has no quality score for comparison"}
        
        # Ensure we have enough data for comparison
        if len(quality_scores) < 2:
            return {"error": "Not enough providers in comparison scope for meaningful analysis"}
        
        # Provider ranking and percentile
        provider_rank = (quality_scores > provider_quality).sum() + 1
        percentile = ((len(quality_scores) - provider_rank + 1) / len(quality_scores)) * 100
        
        # Statistical measures
        mean_quality = quality_scores.mean()
        std_quality = quality_scores.std()
        median_quality = quality_scores.median()
        
        # Z-score (standard deviations from mean)
        z_score = (provider_quality - mean_quality) / std_quality if std_quality > 0 else 0
        
        # Get top and bottom performers for context
        top_performers = comparison_providers.head(10)[
            ['provider_name', 'city', 'composite_quality_score', 'estimated_total_patients']
        ].fillna(0)  # Fill None values with 0
        
        bottom_performers = comparison_providers.tail(10)[
            ['provider_name', 'city', 'composite_quality_score', 'estimated_total_patients']
        ].fillna(0)  # Fill None values with 0
        
        # Similar quality providers (within 0.5 points)
        similar_providers = comparison_providers[
            abs(comparison_providers['composite_quality_score'] - provider_quality) <= 0.5
        ].head(10)[['provider_name', 'city', 'composite_quality_score', 'estimated_total_patients']].fillna(0)  # Fill None values with 0
        
        return {
            'target_provider': {
                'ccn': ccn,
                'name': provider['provider_name'],
                'city': provider['city'],
                'state': provider['state'],
                'quality_score': float(provider_quality) if provider_quality is not None else 0.0,
                'estimated_patients': int(provider['estimated_total_patients']) if provider['estimated_total_patients'] is not None else 0,
                'is_high_quality': bool(provider['is_high_quality']) if provider['is_high_quality'] is not None else False
            },
            'comparison_stats': {
                'scope': comparison_scope,
                'total_providers': len(comparison_providers),
                'provider_rank': int(provider_rank),
                'percentile': float(percentile),
                'z_score': float(z_score)
            },
            'market_stats': {
                'mean_quality': float(mean_quality),
                'median_quality': float(median_quality),
                'std_quality': float(std_quality),
                'min_quality': float(quality_scores.min()),
                'max_quality': float(quality_scores.max())
            },
            'quality_distribution': quality_scores.tolist(),
            'top_performers': top_performers.to_dict('records'),
            'bottom_performers': bottom_performers.to_dict('records'),
            'similar_providers': similar_providers.to_dict('records')
        }
    
    def get_enhanced_county_summary(self) -> pd.DataFrame:
        """
        Get comprehensive county summary using enhanced x_county data.
        """
        try:
            conn = self._get_connection()
            
            query = """
            SELECT 
                COALESCE(county, x_county) as county_name,
                state,
                COUNT(DISTINCT ccn) as unique_providers,
                COUNT(DISTINCT provider_name) as unique_provider_names,
                COUNT(*) as total_records,
                AVG(x_latitude) as avg_latitude,
                AVG(x_longitude) as avg_longitude,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                COUNT(CASE WHEN x_county IS NOT NULL THEN 1 END) as enhanced_county_count,
                COUNT(CASE WHEN county IS NOT NULL THEN 1 END) as original_county_count
            FROM providers 
            WHERE COALESCE(county, x_county) IS NOT NULL
            GROUP BY COALESCE(county, x_county), state
            HAVING COUNT(*) > 0
            ORDER BY total_estimated_patients DESC
            """
            
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()
    
    def get_geographic_analysis(self, center_lat: float, center_lng: float, radius_miles: float = 50) -> pd.DataFrame:
        """
        Get providers within a geographic radius using latitude/longitude coordinates.
        """
        try:
            conn = self._get_connection()
            
            # Haversine distance formula in SQLite
            query = """
            SELECT *,
                   (3959 * acos(cos(radians(?)) * cos(radians(x_latitude)) * 
                               cos(radians(x_longitude) - radians(?)) + 
                               sin(radians(?)) * sin(radians(x_latitude)))) as distance_miles
            FROM providers 
            WHERE x_latitude IS NOT NULL 
              AND x_longitude IS NOT NULL
              AND (3959 * acos(cos(radians(?)) * cos(radians(x_latitude)) * 
                              cos(radians(x_longitude) - radians(?)) + 
                              sin(radians(?)) * sin(radians(x_latitude)))) <= ?
            ORDER BY distance_miles
            """
            
            params = [center_lat, center_lng, center_lat, center_lat, center_lng, center_lat, radius_miles]
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def get_coverage_improvement_report(self) -> Dict:
        """
        Generate a report showing how the enhanced crosswalk data improved coverage.
        """
        try:
            conn = self._get_connection()
            
            # Overall coverage statistics
            coverage_query = """
            SELECT 
                COUNT(*) as total_providers,
                COUNT(county) as original_county_coverage,
                COUNT(x_county) as enhanced_county_coverage,
                COUNT(CASE WHEN county IS NOT NULL OR x_county IS NOT NULL THEN 1 END) as combined_coverage,
                COUNT(CASE WHEN county IS NULL AND x_county IS NOT NULL THEN 1 END) as improvement_count,
                COUNT(x_latitude) as lat_lng_coverage
            FROM providers
            """
            
            coverage_stats = conn.execute(coverage_query).fetchone()
            
            # State-level improvement
            state_query = """
            SELECT 
                state,
                COUNT(*) as total_providers,
                COUNT(county) as orig_county,
                COUNT(x_county) as enhanced_county,
                COUNT(CASE WHEN county IS NULL AND x_county IS NOT NULL THEN 1 END) as improvement
            FROM providers 
            WHERE state IS NOT NULL
            GROUP BY state
            HAVING improvement > 0
            ORDER BY improvement DESC
            """
            
            state_improvements = pd.read_sql_query(state_query, conn)
            
            return {
                'total_providers': coverage_stats[0],
                'original_county_coverage': coverage_stats[1],
                'enhanced_county_coverage': coverage_stats[2],
                'combined_coverage': coverage_stats[3],
                'improvement_count': coverage_stats[4],
                'lat_lng_coverage': coverage_stats[5],
                'coverage_improvement_pct': round((coverage_stats[4] / coverage_stats[0]) * 100, 2),
                'state_improvements': state_improvements
            }
        finally:
            conn.close()

    def find_providers_by_cbsa(self, cbsa_name: Optional[str] = None, cbsa_code: Optional[str] = None) -> pd.DataFrame:
        """
        Find providers by CBSA (Core Based Statistical Area / Metropolitan Statistical Area).
        """
        try:
            conn = self._get_connection()
            
            base_query = """
            SELECT DISTINCT p.*
            FROM providers p
            WHERE 1=1
            """
            
            conditions = []
            params = []
            
            if cbsa_name:
                conditions.append("LOWER(p.x_cbsa_name) LIKE LOWER(?)")
                params.append(f"%{cbsa_name}%")
                
            if cbsa_code:
                conditions.append("p.x_cbsa_code = ?")
                params.append(cbsa_code)
            
            if conditions:
                query = base_query + " AND " + " AND ".join(conditions)
            else:
                query = base_query + " AND p.x_cbsa_name IS NOT NULL"
                
            query += " ORDER BY p.composite_quality_score DESC"
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def get_cbsa_analysis(self, cbsa_name: str) -> Dict:
        """
        Get comprehensive analysis for a specific CBSA/Metropolitan area.
        """
        try:
            conn = self._get_connection()
            
            # Get CBSA providers
            providers_query = """
            SELECT * FROM providers 
            WHERE LOWER(x_cbsa_name) LIKE LOWER(?)
            ORDER BY composite_quality_score DESC
            """
            
            providers = pd.read_sql_query(providers_query, conn, params=[f"%{cbsa_name}%"])
            
            if providers.empty:
                return {'error': f'No providers found for CBSA: {cbsa_name}'}
            
            # Calculate CBSA metrics
            total_providers = len(providers)
            unique_ccns = providers['ccn'].nunique()
            unique_counties = providers[providers['x_county'].notna()]['x_county'].nunique()
            high_quality_providers = providers['is_high_quality'].sum()
            avg_quality = providers['composite_quality_score'].mean()
            total_estimated_patients = providers['estimated_total_patients'].sum()
            
            # Geographic spread
            lat_range = providers['x_latitude'].max() - providers['x_latitude'].min() if providers['x_latitude'].notna().any() else 0
            lng_range = providers['x_longitude'].max() - providers['x_longitude'].min() if providers['x_longitude'].notna().any() else 0
            
            # Market concentration (HHI-like measure)
            if total_estimated_patients > 0:
                market_shares = providers['estimated_total_patients'] / total_estimated_patients
                market_concentration = (market_shares ** 2).sum()
            else:
                market_concentration = 0
            
            # Top providers
            top_providers = providers.head(10)[['ccn', 'provider_name', 'city', 'x_county', 'composite_quality_score', 'estimated_total_patients']]
            
            return {
                'cbsa_name': cbsa_name,
                'total_providers': int(total_providers),
                'unique_ccns': int(unique_ccns),
                'unique_counties': int(unique_counties),
                'high_quality_providers': int(high_quality_providers),
                'high_quality_percentage': round((high_quality_providers / total_providers) * 100, 1),
                'avg_quality_score': round(avg_quality, 2),
                'total_estimated_patients': int(total_estimated_patients),
                'market_concentration_index': round(market_concentration, 3),
                'geographic_lat_range': round(lat_range, 3),
                'geographic_lng_range': round(lng_range, 3),
                'top_providers': top_providers,
                'all_providers': providers
            }
        finally:
            conn.close()
    
    def get_cbsa_summary(self) -> pd.DataFrame:
        """
        Get summary statistics for all CBSAs.
        """
        try:
            conn = self._get_connection()
            
            query = """
            SELECT 
                x_cbsa_name as cbsa_name,
                x_cbsa_code as cbsa_code,
                x_metro_type as metro_type,
                COUNT(DISTINCT ccn) as unique_providers,
                COUNT(DISTINCT provider_name) as unique_provider_names,
                COUNT(*) as total_records,
                COUNT(DISTINCT x_county) as unique_counties,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                AVG(x_latitude) as avg_latitude,
                AVG(x_longitude) as avg_longitude
            FROM providers 
            WHERE x_cbsa_name IS NOT NULL
            GROUP BY x_cbsa_name, x_cbsa_code, x_metro_type
            HAVING COUNT(*) > 0
            ORDER BY total_estimated_patients DESC
            """
            
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()

    def get_rural_urban_analysis(self) -> Dict:
        """
        Get comprehensive rural-urban analysis of providers.
        """
        try:
            conn = self._get_connection()
            
            # Overall rural-urban distribution
            distribution_query = """
            SELECT 
                x_rucc_category,
                x_rucc_subcategory,
                COUNT(*) as provider_count,
                COUNT(DISTINCT ccn) as unique_ccns,
                AVG(composite_quality_score) as avg_quality,
                SUM(estimated_total_patients) as total_patients,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count
            FROM providers 
            WHERE x_rucc_category IS NOT NULL
            GROUP BY x_rucc_category, x_rucc_subcategory
            ORDER BY provider_count DESC
            """
            
            distribution = pd.read_sql_query(distribution_query, conn)
            
            # Density category analysis
            density_query = """
            SELECT 
                x_density_category,
                COUNT(*) as provider_count,
                AVG(composite_quality_score) as avg_quality,
                SUM(estimated_total_patients) as total_patients
            FROM providers 
            WHERE x_density_category IS NOT NULL
            GROUP BY x_density_category
            ORDER BY provider_count DESC
            """
            
            density_analysis = pd.read_sql_query(density_query, conn)
            
            # Rural vs Urban comparison
            rural_urban_comparison = conn.execute("""
                SELECT 
                    CASE WHEN x_is_rural = 1 THEN 'Rural' ELSE 'Urban' END as area_type,
                    COUNT(*) as provider_count,
                    COUNT(DISTINCT ccn) as unique_ccns,
                    AVG(composite_quality_score) as avg_quality,
                    SUM(estimated_total_patients) as total_patients,
                    COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                    ROUND(COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as high_quality_pct
                FROM providers 
                WHERE x_is_rural IS NOT NULL
                GROUP BY x_is_rural
            """).fetchall()
            
            # Frontier analysis
            frontier_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_frontier_providers,
                    COUNT(DISTINCT ccn) as unique_frontier_ccns,
                    AVG(composite_quality_score) as avg_frontier_quality,
                    SUM(estimated_total_patients) as total_frontier_patients
                FROM providers 
                WHERE x_is_frontier = 1
            """).fetchone()
            
            return {
                'rucc_distribution': distribution,
                'density_analysis': density_analysis,
                'rural_urban_comparison': rural_urban_comparison,
                'frontier_stats': {
                    'total_providers': frontier_stats[0] if frontier_stats[0] else 0,
                    'unique_ccns': frontier_stats[1] if frontier_stats[1] else 0,
                    'avg_quality': round(frontier_stats[2], 2) if frontier_stats[2] else 0,
                    'total_patients': frontier_stats[3] if frontier_stats[3] else 0
                }
            }
        finally:
            conn.close()
    
    def find_rural_providers(self, 
                           rucc_category: Optional[str] = None,
                           is_frontier: bool = False,
                           state: Optional[str] = None) -> pd.DataFrame:
        """
        Find providers in rural areas with specific criteria.
        """
        try:
            conn = self._get_connection()
            
            base_query = """
            SELECT DISTINCT p.*
            FROM providers p
            WHERE p.x_is_rural = 1
            """
            
            conditions = []
            params = []
            
            if rucc_category:
                conditions.append("p.x_rucc_category LIKE ?")
                params.append(f"%{rucc_category}%")
            
            if is_frontier:
                conditions.append("p.x_is_frontier = 1")
            
            if state:
                conditions.append("p.state = ?")
                params.append(state)
            
            if conditions:
                query = base_query + " AND " + " AND ".join(conditions)
            else:
                query = base_query
                
            query += " ORDER BY p.composite_quality_score DESC"
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def get_state_rural_urban_summary(self, state: Optional[str] = None) -> pd.DataFrame:
        """
        Get rural-urban summary by state.
        """
        try:
            conn = self._get_connection()
            
            base_query = """
            SELECT 
                state,
                COUNT(*) as total_providers,
                COUNT(CASE WHEN x_is_rural = 1 THEN 1 END) as rural_providers,
                COUNT(CASE WHEN x_is_rural = 0 THEN 1 END) as urban_providers,
                COUNT(CASE WHEN x_is_frontier = 1 THEN 1 END) as frontier_providers,
                ROUND(COUNT(CASE WHEN x_is_rural = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as rural_percentage,
                AVG(CASE WHEN x_is_rural = 1 THEN composite_quality_score END) as rural_avg_quality,
                AVG(CASE WHEN x_is_rural = 0 THEN composite_quality_score END) as urban_avg_quality,
                COUNT(DISTINCT x_cbsa_name) as unique_cbsas,
                COUNT(DISTINCT COALESCE(county, x_county)) as unique_counties
            FROM providers 
            WHERE x_is_rural IS NOT NULL
            """
            
            if state:
                query = base_query + " AND state = ? GROUP BY state"
                params = [state]
            else:
                query = base_query + " GROUP BY state ORDER BY rural_percentage DESC"
                params = []
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def get_density_category_analysis(self) -> pd.DataFrame:
        """
        Analyze providers by population density categories.
        """
        try:
            conn = self._get_connection()
            
            query = """
            SELECT 
                x_density_category as density_category,
                COUNT(*) as provider_count,
                COUNT(DISTINCT ccn) as unique_ccns,
                COUNT(DISTINCT state) as states_covered,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                ROUND(COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as high_quality_percentage,
                AVG(x_latitude) as avg_latitude,
                AVG(x_longitude) as avg_longitude
            FROM providers 
            WHERE x_density_category IS NOT NULL
            GROUP BY x_density_category
            ORDER BY 
                CASE x_density_category
                    WHEN 'high_density' THEN 1
                    WHEN 'medium_density' THEN 2
                    WHEN 'low_density' THEN 3
                    WHEN 'rural' THEN 4
                    ELSE 5
                END
            """
            
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()

    # ...existing code...
    
# Example usage functions for RAG system
def get_provider_summary_for_rag(ccn: str, analytics: CMSAnalytics) -> str:
    """
    Generate a comprehensive text summary of a provider for RAG indexing.
    """
    
    # Get provider data
    provider_query = "SELECT * FROM providers WHERE ccn = ?"
    conn = analytics._get_connection()
    try:
        provider_df = pd.read_sql_query(provider_query, conn, params=[ccn])
    finally:
        conn.close()
    
    if provider_df.empty:
        return ""
    
    provider = provider_df.iloc[0]
    
    # Get competitive analysis
    competitor_analysis = analytics.get_competitor_analysis(ccn)
    
    # Get coverage analysis
    coverage_analysis = analytics.get_geographic_coverage_analysis(ccn)
    
    # Create comprehensive summary
    summary = f"""
    Provider: {provider['provider_name']} (CCN: {ccn})
    Location: {provider['address']}, {provider['city']}, {provider['state']} {provider['zip_code']}
    Phone: {provider['phone']}
    Ownership: {provider['ownership_type']}
    
    Quality Metrics:
    - Overall Quality Star Rating: {provider['quality_care_star_rating']}
    - HHCAHPS Survey Star Rating: {provider['hhcahps_star_rating']}
    - Composite Quality Score: {provider['composite_quality_score']:.2f}
    - High Quality Provider: {'Yes' if provider['is_high_quality'] else 'No'}
    
    Patient Volume:
    - Completed Surveys: {provider['number_completed_surveys']}
    - Survey Response Rate: {provider['survey_response_rate']}%
    - Estimated Total Patients: {provider['estimated_total_patients']}
    - Provider Size Category: {provider['provider_size_category']}
    
    Services Offered:
    - Nursing Care: {'Yes' if provider['offers_nursing'] else 'No'}
    - Physical Therapy: {'Yes' if provider['offers_physical_therapy'] else 'No'}
    - Occupational Therapy: {'Yes' if provider['offers_occupational_therapy'] else 'No'}
    - Speech Pathology: {'Yes' if provider['offers_speech_pathology'] else 'No'}
    - Medical Social Services: {'Yes' if provider['offers_medical_social'] else 'No'}
    - Home Health Aide: {'Yes' if provider['offers_home_health_aide'] else 'No'}
    
    Geographic Coverage:
    - ZIP Codes Served: {coverage_analysis['coverage_stats']['total_zip_codes']}
    - Cities Served: {coverage_analysis['coverage_stats']['total_cities']}
    - States Covered: {coverage_analysis['coverage_stats']['total_states']}
    
    Competitive Position:
    - Quality Rank in Area: {competitor_analysis.get('target_provider', {}).get('rank', 'N/A')}
    - Market Share: {competitor_analysis.get('target_provider', {}).get('market_share', 0)*100:.2f}%
    - Better Competitors: {competitor_analysis.get('competitive_landscape', {}).get('better_competitors', 0)}
    """
    
    return summary.strip()

if __name__ == "__main__":
    # Example usage
    analytics = CMSAnalytics()
    
    # Example queries
    print("Finding high quality providers in California...")
    ca_providers = analytics.find_providers_by_location(state="CA", high_quality_only=True)
    print(f"Found {len(ca_providers)} high quality providers in CA")
    
    # Example market analysis
    if not ca_providers.empty:
        sample_city = ca_providers.iloc[0]['city']
        market_analysis = analytics.get_market_analysis(sample_city, "CA")
        print(f"\nMarket analysis for {sample_city}, CA:")
        print(f"Total providers: {market_analysis['total_providers']}")
        print(f"High quality providers: {market_analysis['high_quality_providers']}")
    
    analytics.close()
