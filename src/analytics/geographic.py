"""
Geographic Analytics Module - Location-based analysis and mapping
"""
import pandas as pd
from typing import List, Dict, Tuple, Optional
from .base import AnalyticsBase


class GeographicAnalytics(AnalyticsBase):
    """
    Geographic analytics for CMS Home Health data including location search,
    CBSA analysis, and geographic coverage analysis.
    """
    
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
        Get summary statistics for all CBSA areas with providers.
        """
        try:
            conn = self._get_connection()
            
            query = """
            SELECT 
                x_cbsa_code as cbsa_code,
                x_cbsa_name as cbsa_name,
                x_metro_type as metro_type,
                COUNT(DISTINCT ccn) as unique_providers,
                COUNT(DISTINCT x_county) as unique_counties,
                COUNT(DISTINCT state) as unique_states,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                AVG(x_latitude) as avg_latitude,
                AVG(x_longitude) as avg_longitude
            FROM providers 
            WHERE x_cbsa_name IS NOT NULL
            GROUP BY x_cbsa_code, x_cbsa_name, x_metro_type
            HAVING COUNT(*) > 0
            ORDER BY unique_providers DESC
            """
            
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()
