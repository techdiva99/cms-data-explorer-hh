"""
Coverage Deserts Analytics Module - Identify underserved areas and market opportunities
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from .base import AnalyticsBase


class CoverageDesertAnalytics(AnalyticsBase):
    """
    Coverage desert analytics for identifying underserved ZIP codes,
    calculating market potential, and analyzing provider proximity.
    """
    
    def identify_coverage_deserts(self, 
                                radius_miles: float = 25,
                                min_medicare_population: int = 100,
                                max_providers_in_radius: int = 2,
                                state_filter: Optional[str] = None,
                                rural_only: bool = False) -> pd.DataFrame:
        """
        Identify ZIP codes with limited or no home health provider coverage.
        
        Args:
            radius_miles: Maximum distance to consider for provider coverage
            min_medicare_population: Minimum Medicare eligible population in ZIP
            max_providers_in_radius: Maximum number of providers to be considered underserved
            state_filter: Optionally filter to specific state
            rural_only: If True, only analyze rural ZIP codes
        
        Returns:
            DataFrame of underserved ZIP codes with market potential data
        """
        try:
            conn = self._get_connection()
            
            # Build query to find ZIP codes with limited provider coverage
            desert_query = """
            WITH zip_provider_coverage AS (
                SELECT 
                    z.zip_code,
                    z.city,
                    z.state_abbr as state,
                    z.primary_county_name as county,
                    z.latitude,
                    z.longitude,
                    z.population,
                    z.medicare_eligibles,
                    z.medicare_enrolled,
                    z.medicare_penetration_pct,
                    z.is_rural,
                    z.is_frontier,
                    z.rucc_description,
                    z.density_category,
                    COUNT(p.ccn) as providers_in_zip,
                    -- Count providers within radius using Haversine formula
                    (
                        SELECT COUNT(DISTINCT p2.ccn)
                        FROM providers p2
                        WHERE p2.x_latitude IS NOT NULL 
                          AND p2.x_longitude IS NOT NULL
                          AND (3959 * acos(cos(radians(z.latitude)) * cos(radians(p2.x_latitude)) * 
                                          cos(radians(p2.x_longitude) - radians(z.longitude)) + 
                                          sin(radians(z.latitude)) * sin(radians(p2.x_latitude)))) <= ?
                    ) as providers_within_radius
                FROM zip_county_crosswalk z
                LEFT JOIN providers p ON z.zip_code = p.zip_code
                WHERE z.medicare_eligibles >= ?
                  AND z.latitude IS NOT NULL 
                  AND z.longitude IS NOT NULL
            """
            
            params = [radius_miles, min_medicare_population]
            
            # Add state filter if specified
            if state_filter:
                desert_query += " AND z.state_abbr = ?"
                params.append(state_filter.upper())
            
            # Add rural filter if specified
            if rural_only:
                desert_query += " AND z.is_rural = 1"
            
            desert_query += """
                GROUP BY z.zip_code, z.city, z.state_abbr, z.primary_county_name,
                         z.latitude, z.longitude, z.population, z.medicare_eligibles,
                         z.medicare_enrolled, z.medicare_penetration_pct, z.is_rural,
                         z.is_frontier, z.rucc_description, z.density_category
                HAVING providers_within_radius <= ?
            ), 
            desert_analysis AS (
                SELECT *,
                    -- Calculate market opportunity score
                    (medicare_eligibles * 0.4 + 
                     medicare_enrolled * 0.4 + 
                     (? - providers_within_radius) * 50 * 0.2) as market_opportunity_score,
                    -- Categorize desert severity
                    CASE 
                        WHEN providers_within_radius = 0 THEN 'Complete Desert'
                        WHEN providers_within_radius = 1 THEN 'Severe Underservice'
                        ELSE 'Moderate Underservice'
                    END as desert_severity
                FROM zip_provider_coverage
            )
            SELECT * FROM desert_analysis
            ORDER BY market_opportunity_score DESC
            """
            
            params.extend([max_providers_in_radius, max_providers_in_radius])
            
            desert_zips = pd.read_sql_query(desert_query, conn, params=params)
            
            return desert_zips
            
        finally:
            conn.close()
    
    def get_nearest_providers_to_zip(self, zip_code: str, max_radius: float = 100) -> pd.DataFrame:
        """
        Find the nearest home health providers to a specific ZIP code.
        
        Args:
            zip_code: Target ZIP code
            max_radius: Maximum search radius in miles
            
        Returns:
            DataFrame of nearest providers with distances
        """
        try:
            conn = self._get_connection()
            
            # First get the ZIP code coordinates
            zip_query = """
            SELECT latitude, longitude, city, state_abbr, primary_county_name,
                   medicare_eligibles, medicare_enrolled
            FROM zip_county_crosswalk 
            WHERE zip_code = ?
            """
            
            zip_info = pd.read_sql_query(zip_query, conn, params=[zip_code])
            
            if zip_info.empty:
                return pd.DataFrame()
            
            zip_lat = zip_info.iloc[0]['latitude']
            zip_lng = zip_info.iloc[0]['longitude']
            
            # Find nearest providers using Haversine distance
            providers_query = """
            SELECT p.*,
                   (3959 * acos(cos(radians(?)) * cos(radians(p.x_latitude)) * 
                               cos(radians(p.x_longitude) - radians(?)) + 
                               sin(radians(?)) * sin(radians(p.x_latitude)))) as distance_miles
            FROM providers p
            WHERE p.x_latitude IS NOT NULL 
              AND p.x_longitude IS NOT NULL
              AND (3959 * acos(cos(radians(?)) * cos(radians(p.x_latitude)) * 
                              cos(radians(p.x_longitude) - radians(?)) + 
                              sin(radians(?)) * sin(radians(p.x_latitude)))) <= ?
            ORDER BY distance_miles
            LIMIT 50
            """
            
            params = [zip_lat, zip_lng, zip_lat, zip_lat, zip_lng, zip_lat, max_radius]
            nearest_providers = pd.read_sql_query(providers_query, conn, params=params)
            
            # Add ZIP code info for context
            for col in ['target_zip', 'target_city', 'target_state', 'target_county', 
                       'target_medicare_eligibles', 'target_medicare_enrolled']:
                if col == 'target_zip':
                    nearest_providers[col] = zip_code
                elif col == 'target_city':
                    nearest_providers[col] = zip_info.iloc[0]['city']
                elif col == 'target_state':
                    nearest_providers[col] = zip_info.iloc[0]['state_abbr']
                elif col == 'target_county':
                    nearest_providers[col] = zip_info.iloc[0]['primary_county_name']
                elif col == 'target_medicare_eligibles':
                    nearest_providers[col] = zip_info.iloc[0]['medicare_eligibles']
                elif col == 'target_medicare_enrolled':
                    nearest_providers[col] = zip_info.iloc[0]['medicare_enrolled']
            
            return nearest_providers
            
        finally:
            conn.close()
    
    def calculate_market_potential(self, zip_codes_list: List[str]) -> Dict:
        """
        Calculate total market potential for a list of ZIP codes.
        
        Args:
            zip_codes_list: List of ZIP codes to analyze
            
        Returns:
            Dictionary with market potential metrics
        """
        try:
            conn = self._get_connection()
            
            if not zip_codes_list:
                return {'error': 'No ZIP codes provided'}
            
            # Create comma-separated list for SQL IN clause
            zip_placeholders = ','.join(['?' for _ in zip_codes_list])
            
            market_query = f"""
            SELECT 
                COUNT(DISTINCT zip_code) as total_zip_codes,
                COUNT(DISTINCT state_abbr) as states_covered,
                COUNT(DISTINCT primary_county_name) as counties_covered,
                SUM(population) as total_population,
                SUM(medicare_eligibles) as total_medicare_eligibles,
                SUM(medicare_enrolled) as total_medicare_enrolled,
                AVG(medicare_penetration_pct) as avg_medicare_penetration,
                COUNT(CASE WHEN is_rural = 1 THEN 1 END) as rural_zip_count,
                COUNT(CASE WHEN is_frontier = 1 THEN 1 END) as frontier_zip_count,
                MIN(latitude) as min_latitude,
                MAX(latitude) as max_latitude,
                MIN(longitude) as min_longitude,
                MAX(longitude) as max_longitude
            FROM zip_county_crosswalk
            WHERE zip_code IN ({zip_placeholders})
            """
            
            market_stats = pd.read_sql_query(market_query, conn, params=zip_codes_list)
            
            if market_stats.empty:
                return {'error': 'No data found for provided ZIP codes'}
            
            stats = market_stats.iloc[0]
            
            # Calculate geographic span
            lat_span = stats['max_latitude'] - stats['min_latitude'] if stats['max_latitude'] else 0
            lng_span = stats['max_longitude'] - stats['min_longitude'] if stats['max_longitude'] else 0
            
            # Estimate market value (simplified calculation)
            # Assuming average annual revenue per Medicare patient
            avg_revenue_per_patient = 3500  # Rough estimate
            estimated_annual_market_value = stats['total_medicare_enrolled'] * avg_revenue_per_patient
            
            return {
                'market_summary': {
                    'total_zip_codes': int(stats['total_zip_codes']),
                    'states_covered': int(stats['states_covered']),
                    'counties_covered': int(stats['counties_covered']),
                    'total_population': int(stats['total_population']) if stats['total_population'] else 0,
                    'total_medicare_eligibles': int(stats['total_medicare_eligibles']) if stats['total_medicare_eligibles'] else 0,
                    'total_medicare_enrolled': int(stats['total_medicare_enrolled']) if stats['total_medicare_enrolled'] else 0,
                    'avg_medicare_penetration_pct': round(stats['avg_medicare_penetration'], 2) if stats['avg_medicare_penetration'] else 0,
                    'rural_zip_count': int(stats['rural_zip_count']),
                    'frontier_zip_count': int(stats['frontier_zip_count'])
                },
                'geographic_span': {
                    'latitude_span_degrees': round(lat_span, 4),
                    'longitude_span_degrees': round(lng_span, 4),
                    'approximate_miles_north_south': round(lat_span * 69, 1),  # Rough conversion
                    'approximate_miles_east_west': round(lng_span * 54.6, 1)   # Rough conversion at mid-latitudes
                },
                'market_opportunity': {
                    'estimated_annual_market_value': estimated_annual_market_value,
                    'medicare_market_penetration': round(stats['avg_medicare_penetration'], 2) if stats['avg_medicare_penetration'] else 0,
                    'underserved_population': int(stats['total_medicare_enrolled']) if stats['total_medicare_enrolled'] else 0
                }
            }
            
        finally:
            conn.close()
    
    def get_coverage_desert_summary(self, state_filter: Optional[str] = None) -> Dict:
        """
        Get a comprehensive summary of coverage deserts across the US or specific state.
        
        Args:
            state_filter: Optionally filter to specific state
            
        Returns:
            Dictionary with desert analysis summary
        """
        try:
            # Identify deserts with different severity levels
            complete_deserts = self.identify_coverage_deserts(
                radius_miles=25, max_providers_in_radius=0, 
                min_medicare_population=50, state_filter=state_filter
            )
            
            severe_underservice = self.identify_coverage_deserts(
                radius_miles=25, max_providers_in_radius=1,
                min_medicare_population=50, state_filter=state_filter
            )
            
            moderate_underservice = self.identify_coverage_deserts(
                radius_miles=25, max_providers_in_radius=2,
                min_medicare_population=50, state_filter=state_filter
            )
            
            # Calculate summary statistics
            total_underserved_population = moderate_underservice['medicare_enrolled'].sum()
            total_underserved_zips = len(moderate_underservice)
            
            # Geographic distribution
            state_summary = moderate_underservice.groupby('state').agg({
                'zip_code': 'count',
                'medicare_eligibles': 'sum',
                'medicare_enrolled': 'sum',
                'market_opportunity_score': 'sum'
            }).reset_index()
            state_summary.columns = ['state', 'underserved_zips', 'medicare_eligibles', 
                                   'medicare_enrolled', 'total_opportunity_score']
            
            return {
                'desert_analysis': {
                    'complete_deserts': {
                        'zip_count': len(complete_deserts),
                        'medicare_population': complete_deserts['medicare_enrolled'].sum(),
                        'total_opportunity_score': complete_deserts['market_opportunity_score'].sum()
                    },
                    'severe_underservice': {
                        'zip_count': len(severe_underservice),
                        'medicare_population': severe_underservice['medicare_enrolled'].sum(),
                        'total_opportunity_score': severe_underservice['market_opportunity_score'].sum()
                    },
                    'moderate_underservice': {
                        'zip_count': len(moderate_underservice),
                        'medicare_population': moderate_underservice['medicare_enrolled'].sum(),
                        'total_opportunity_score': moderate_underservice['market_opportunity_score'].sum()
                    }
                },
                'summary_metrics': {
                    'total_underserved_zips': total_underserved_zips,
                    'total_underserved_medicare_population': int(total_underserved_population),
                    'states_with_deserts': len(state_summary),
                    'avg_opportunity_score_per_zip': moderate_underservice['market_opportunity_score'].mean()
                },
                'state_breakdown': state_summary.to_dict('records'),
                'top_opportunities': moderate_underservice.head(20).to_dict('records')
            }
            
        except Exception as e:
            return {'error': f'Error analyzing coverage deserts: {str(e)}'}
    
    def analyze_provider_expansion_opportunity(self, provider_ccn: str, target_radius: float = 100) -> Dict:
        """
        Analyze expansion opportunities for a specific provider into desert areas.
        
        Args:
            provider_ccn: Provider CCN to analyze
            target_radius: Radius to search for opportunities
            
        Returns:
            Dictionary with expansion analysis
        """
        try:
            conn = self._get_connection()
            
            # Get provider information
            provider_query = "SELECT * FROM providers WHERE ccn = ?"
            provider = pd.read_sql_query(provider_query, conn, params=[provider_ccn])
            
            if provider.empty:
                return {"error": "Provider not found"}
            
            provider_data = provider.iloc[0]
            provider_lat = provider_data.get('x_latitude') or provider_data.get('latitude')
            provider_lng = provider_data.get('x_longitude') or provider_data.get('longitude')
            
            if not provider_lat or not provider_lng:
                return {"error": "Provider location coordinates not available"}
            
            # Find desert areas within target radius
            nearby_deserts = self.identify_coverage_deserts(
                radius_miles=25,  # Desert definition radius
                min_medicare_population=50,
                max_providers_in_radius=1,
                state_filter=provider_data['state']
            )
            
            # Filter to those within target expansion radius
            if not nearby_deserts.empty:
                nearby_deserts['distance_from_provider'] = nearby_deserts.apply(
                    lambda row: self._calculate_distance(
                        provider_lat, provider_lng,
                        row['latitude'], row['longitude']
                    ), axis=1
                )
                
                expansion_opportunities = nearby_deserts[
                    nearby_deserts['distance_from_provider'] <= target_radius
                ].sort_values('market_opportunity_score', ascending=False)
            else:
                expansion_opportunities = pd.DataFrame()
            
            # Calculate expansion potential
            if not expansion_opportunities.empty:
                total_opportunity_population = expansion_opportunities['medicare_enrolled'].sum()
                avg_distance = expansion_opportunities['distance_from_provider'].mean()
                total_opportunity_score = expansion_opportunities['market_opportunity_score'].sum()
            else:
                total_opportunity_population = 0
                avg_distance = 0
                total_opportunity_score = 0
            
            return {
                'provider_info': {
                    'ccn': provider_ccn,
                    'name': provider_data['provider_name'],
                    'city': provider_data['city'],
                    'state': provider_data['state'],
                    'current_quality_score': provider_data.get('composite_quality_score', 0)
                },
                'expansion_analysis': {
                    'total_desert_opportunities': len(expansion_opportunities),
                    'total_opportunity_population': int(total_opportunity_population),
                    'average_distance_miles': round(avg_distance, 1),
                    'total_opportunity_score': round(total_opportunity_score, 1),
                    'search_radius_miles': target_radius
                },
                'top_expansion_targets': expansion_opportunities.head(15).to_dict('records') if not expansion_opportunities.empty else [],
                'all_opportunities': expansion_opportunities.to_dict('records') if not expansion_opportunities.empty else []
            }
            
        finally:
            conn.close()
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate Haversine distance between two points in miles.
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Radius of earth in miles
        r = 3959
        
        return c * r
