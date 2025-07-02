"""
Rural Urban Analytics Module - Rural/urban classification and density analysis
"""
import pandas as pd
from typing import Dict, Optional
from .base import AnalyticsBase


class RuralUrbanAnalytics(AnalyticsBase):
    """
    Rural-urban analytics for CMS Home Health data including rural-urban 
    classification analysis, density categories, and frontier area analysis.
    """
    
    def get_rural_urban_analysis(self) -> Dict:
        """
        Get comprehensive rural-urban analysis of all providers.
        """
        try:
            conn = self._get_connection()
            
            # Rural-Urban Continuum Code (RUCC) distribution
            rucc_query = """
            SELECT 
                x_rucc_description as rucc_description,
                x_rucc_category as rucc_category,
                COUNT(*) as provider_count,
                COUNT(DISTINCT ccn) as unique_ccns,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count
            FROM providers 
            WHERE x_rucc_description IS NOT NULL
            GROUP BY x_rucc_description, x_rucc_category
            ORDER BY provider_count DESC
            """
            
            distribution = pd.read_sql_query(rucc_query, conn).to_dict('records')
            
            # Density category analysis
            density_query = """
            SELECT 
                x_density_category as density_category,
                x_density_description as density_description,
                COUNT(*) as provider_count,
                COUNT(DISTINCT ccn) as unique_ccns,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                ROUND(COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as high_quality_percentage
            FROM providers 
            WHERE x_density_category IS NOT NULL
            GROUP BY x_density_category, x_density_description
            ORDER BY provider_count DESC
            """
            
            density_analysis = pd.read_sql_query(density_query, conn).to_dict('records')
            
            # Rural vs Urban comparison
            rural_urban_query = """
            SELECT 
                CASE WHEN x_is_rural = 1 THEN 'Rural' ELSE 'Urban' END as area_type,
                COUNT(*) as provider_count,
                COUNT(DISTINCT ccn) as unique_ccns,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients,
                COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
                COUNT(DISTINCT state) as states_covered,
                COUNT(DISTINCT COALESCE(county, x_county)) as counties_covered
            FROM providers 
            WHERE x_is_rural IS NOT NULL
            GROUP BY x_is_rural
            ORDER BY provider_count DESC
            """
            
            rural_urban_comparison = pd.read_sql_query(rural_urban_query, conn).to_dict('records')
            
            # Frontier area statistics
            frontier_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_providers,
                COUNT(DISTINCT ccn) as unique_ccns,
                AVG(composite_quality_score) as avg_quality_score,
                SUM(estimated_total_patients) as total_estimated_patients
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
