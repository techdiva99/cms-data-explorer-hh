"""
Market Analytics Module - Market analysis and competitive intelligence
"""
import pandas as pd
from typing import List, Dict, Optional
from .base import AnalyticsBase


class MarketAnalytics(AnalyticsBase):
    """
    Market analytics for CMS Home Health data including market analysis,
    competitive intelligence, and service area gap analysis.
    """
    
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
        if total_estimated_patients > 0:
            market_shares = providers['estimated_total_patients'] / total_estimated_patients
            market_concentration = (market_shares ** 2).sum()
        else:
            market_concentration = 0
        
        # Top providers by market share
        top_providers = providers.nlargest(5, 'estimated_total_patients')[
            ['provider_name', 'composite_quality_score', 'estimated_total_patients']
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
                WHERE COALESCE(county, x_county) = ? AND state = ? AND ccn != ?
                ORDER BY composite_quality_score DESC
                """
                county = provider.get('x_county') or provider.get('county')
                competitors = pd.read_sql_query(
                    competitors_query, 
                    conn, 
                    params=[county, provider['state'], ccn]
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
            'top_competitors': top_competitors.to_dict('records'),
            'market_rank': provider_rank,
            'total_competitors': total_competitors,
            'quality_ranking': provider_rank
        }
    
    def analyze_service_area_gaps(self, provider_ccn: str) -> Dict:
        """
        Analyze potential service area expansion opportunities for a provider.
        Identifies nearby areas with limited provider coverage.
        """
        
        conn = self._get_connection()
        try:
            # Get provider information
            provider_query = "SELECT * FROM providers WHERE ccn = ?"
            provider = pd.read_sql_query(provider_query, conn, params=[provider_ccn])
            
            if provider.empty:
                return {"error": "Provider not found"}
            
            provider_data = provider.iloc[0]
            
            # Find nearby ZIP codes with limited provider coverage
            gaps_query = """
            WITH provider_coverage AS (
                SELECT DISTINCT z.zip_code, z.primary_county_name, z.state_abbr,
                       z.latitude, z.longitude, z.population, 
                       z.medicare_eligibles, z.medicare_enrolled,
                       COUNT(p.ccn) as provider_count,
                       (3959 * acos(cos(radians(?)) * cos(radians(z.latitude)) * 
                                   cos(radians(z.longitude) - radians(?)) + 
                                   sin(radians(?)) * sin(radians(z.latitude)))) as distance_miles
                FROM zip_county_crosswalk z
                LEFT JOIN providers p ON z.zip_code = p.zip_code
                WHERE z.state_abbr = ?
                  AND z.medicare_eligibles > 100
                  AND (3959 * acos(cos(radians(?)) * cos(radians(z.latitude)) * 
                                  cos(radians(z.longitude) - radians(?)) + 
                                  sin(radians(?)) * sin(radians(z.latitude)))) <= 100
                GROUP BY z.zip_code, z.primary_county_name, z.state_abbr,
                         z.latitude, z.longitude, z.population, 
                         z.medicare_eligibles, z.medicare_enrolled
                HAVING provider_count <= 2
                ORDER BY distance_miles, medicare_eligibles DESC
                LIMIT 50
            )
            SELECT * FROM provider_coverage
            """
            
            provider_lat = provider_data.get('x_latitude') or provider_data.get('latitude')
            provider_lng = provider_data.get('x_longitude') or provider_data.get('longitude')
            
            if not provider_lat or not provider_lng:
                return {"error": "Provider location coordinates not available"}
            
            gap_areas = pd.read_sql_query(
                gaps_query, 
                conn, 
                params=[
                    provider_lat, provider_lng, provider_lat,
                    provider_data['state'],
                    provider_lat, provider_lng, provider_lat
                ]
            )
            
        finally:
            conn.close()
        
        if gap_areas.empty:
            return {
                "provider_name": provider_data['provider_name'],
                "message": "No significant service area gaps identified within 100 miles",
                "expansion_opportunities": []
            }
        
        # Calculate market potential for gap areas
        total_medicare_eligibles = gap_areas['medicare_eligibles'].sum()
        total_medicare_enrolled = gap_areas['medicare_enrolled'].sum()
        avg_distance = gap_areas['distance_miles'].mean()
        
        # Prioritize opportunities
        gap_areas['opportunity_score'] = (
            gap_areas['medicare_eligibles'] * 0.4 +
            gap_areas['medicare_enrolled'] * 0.4 +
            (100 - gap_areas['distance_miles']) * 0.1 +  # Closer is better
            (3 - gap_areas['provider_count']) * 50 * 0.1  # Fewer providers is better
        )
        
        top_opportunities = gap_areas.nlargest(15, 'opportunity_score')
        
        return {
            "provider_name": provider_data['provider_name'],
            "provider_location": {
                "city": provider_data['city'],
                "state": provider_data['state'],
                "county": provider_data.get('x_county') or provider_data.get('county')
            },
            "analysis_summary": {
                "total_gap_areas_identified": len(gap_areas),
                "total_medicare_eligibles": int(total_medicare_eligibles),
                "total_medicare_enrolled": int(total_medicare_enrolled),
                "average_distance_miles": round(avg_distance, 1),
                "underserved_population": int(total_medicare_enrolled)
            },
            "top_expansion_opportunities": top_opportunities[[
                'zip_code', 'primary_county_name', 'state_abbr', 'distance_miles',
                'medicare_eligibles', 'medicare_enrolled', 'provider_count', 'opportunity_score'
            ]].to_dict('records'),
            "expansion_opportunities": gap_areas.to_dict('records')
        }
