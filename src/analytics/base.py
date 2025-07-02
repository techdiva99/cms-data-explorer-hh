"""
Base Analytics Module - Core database connection and shared utilities
"""
import sqlite3
import pandas as pd
from typing import List, Dict, Tuple, Optional
import numpy as np


class AnalyticsBase:
    """
    Base class for CMS Analytics with shared database connection and utility functions.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use the proper database path - avoid circular import by hardcoding for now
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.db_path = os.path.join(project_root, 'data', 'processed', 'cms_homehealth.db')
        else:
            self.db_path = db_path
    
    def _get_connection(self):
        """Get a new database connection for thread safety"""
        return sqlite3.connect(self.db_path)
    
    def close(self):
        """Close database connection - no longer needed with per-method connections"""
        pass


class CMSAnalytics(AnalyticsBase):
    """
    Main analytics class that combines all specialized analytics modules.
    This serves as the unified interface for all analytics operations.
    """
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        
        # Import specialized modules here to avoid circular imports
        from .geographic import GeographicAnalytics
        from .market import MarketAnalytics  
        from .quality import QualityAnalytics
        from .rural_urban import RuralUrbanAnalytics
        from .coverage_deserts import CoverageDesertAnalytics
        
        # Initialize specialized analytics modules
        self.geographic = GeographicAnalytics(db_path)
        self.market = MarketAnalytics(db_path)
        self.quality = QualityAnalytics(db_path)
        self.rural_urban = RuralUrbanAnalytics(db_path)
        self.coverage_deserts = CoverageDesertAnalytics(db_path)
    
    # Delegate methods to specialized modules for backward compatibility
    def find_providers_by_location(self, **kwargs):
        """Find providers by geographic location - delegates to geographic module"""
        return self.geographic.find_providers_by_location(**kwargs)
    
    def get_market_analysis(self, county: str, state: str):
        """Get market analysis - delegates to market module"""
        return self.market.get_market_analysis(county, state)
    
    def get_quality_benchmarks(self, state: Optional[str] = None):
        """Get quality benchmarks - delegates to quality module"""
        return self.quality.get_quality_benchmarks(state)
    
    def get_provider_comparison_analysis(self, ccn: str, comparison_scope: str = "state"):
        """Get provider comparison - delegates to quality module"""
        return self.quality.get_provider_comparison_analysis(ccn, comparison_scope)
    
    def search_providers_by_criteria(self, **kwargs):
        """Search providers by criteria - delegates to quality module"""
        return self.quality.search_providers_by_criteria(**kwargs)
    
    def get_competitor_analysis(self, ccn: str, radius_type: str = "state"):
        """Get competitor analysis - delegates to market module"""
        return self.market.get_competitor_analysis(ccn, radius_type)
    
    def get_geographic_coverage_analysis(self, ccn: str):
        """Get geographic coverage - delegates to geographic module"""
        return self.geographic.get_geographic_coverage_analysis(ccn)
    
    def get_enhanced_county_summary(self):
        """Get enhanced county summary - delegates to geographic module"""
        return self.geographic.get_enhanced_county_summary()
    
    def get_geographic_analysis(self, center_lat: float, center_lng: float, radius_miles: float = 50):
        """Get geographic analysis - delegates to geographic module"""
        return self.geographic.get_geographic_analysis(center_lat, center_lng, radius_miles)
    
    def get_coverage_improvement_report(self):
        """Get coverage improvement report - delegates to geographic module"""
        return self.geographic.get_coverage_improvement_report()
    
    def find_providers_by_cbsa(self, cbsa_name: Optional[str] = None, cbsa_code: Optional[str] = None):
        """Find providers by CBSA - delegates to geographic module"""
        return self.geographic.find_providers_by_cbsa(cbsa_name, cbsa_code)
    
    def get_cbsa_analysis(self, cbsa_name: str):
        """Get CBSA analysis - delegates to geographic module"""
        return self.geographic.get_cbsa_analysis(cbsa_name)
    
    def get_cbsa_summary(self):
        """Get CBSA summary - delegates to geographic module"""
        return self.geographic.get_cbsa_summary()
    
    def get_rural_urban_analysis(self):
        """Get rural urban analysis - delegates to rural_urban module"""
        return self.rural_urban.get_rural_urban_analysis()
    
    def find_rural_providers(self, **kwargs):
        """Find rural providers - delegates to rural_urban module"""
        return self.rural_urban.find_rural_providers(**kwargs)
    
    def get_state_rural_urban_summary(self, state: Optional[str] = None):
        """Get state rural urban summary - delegates to rural_urban module"""
        return self.rural_urban.get_state_rural_urban_summary(state)
    
    def get_density_category_analysis(self):
        """Get density category analysis - delegates to rural_urban module"""
        return self.rural_urban.get_density_category_analysis()
    
    # NEW: Coverage desert methods
    def identify_coverage_deserts(self, **kwargs):
        """Identify coverage deserts - delegates to coverage_deserts module"""
        return self.coverage_deserts.identify_coverage_deserts(**kwargs)
    
    def get_nearest_providers_to_zip(self, zip_code: str, max_radius: float = 100):
        """Get nearest providers to ZIP - delegates to coverage_deserts module"""
        return self.coverage_deserts.get_nearest_providers_to_zip(zip_code, max_radius)
    
    def calculate_market_potential(self, zip_codes_list: List[str]):
        """Calculate market potential - delegates to coverage_deserts module"""
        return self.coverage_deserts.calculate_market_potential(zip_codes_list)
    
    def analyze_service_area_gaps(self, provider_ccn: str):
        """Analyze service area gaps - delegates to market module"""
        return self.market.analyze_service_area_gaps(provider_ccn)


# Keep the standalone function for backward compatibility
def get_provider_summary_for_rag(ccn: str, analytics: CMSAnalytics) -> str:
    """
    Generate a comprehensive provider summary for RAG (Retrieval Augmented Generation) applications.
    This function creates a detailed text summary of a provider's information and performance.
    """
    conn = analytics._get_connection()
    try:
        # Get basic provider information
        provider_query = """
        SELECT * FROM providers WHERE ccn = ?
        """
        provider_df = pd.read_sql_query(provider_query, conn, params=[ccn])
        
        if provider_df.empty:
            return f"Provider with CCN {ccn} not found."
        
        provider = provider_df.iloc[0]
        
        # Get competitor analysis
        competitor_analysis = analytics.get_competitor_analysis(ccn)
        
        # Get geographic coverage
        coverage_analysis = analytics.get_geographic_coverage_analysis(ccn)
        
        # Build comprehensive summary
        summary = f"""
Provider Summary for {provider['provider_name']} (CCN: {ccn})

BASIC INFORMATION:
- Provider Name: {provider['provider_name']}
- CCN: {provider['ccn']}
- Location: {provider['address']}, {provider['city']}, {provider['state']} {provider['zip_code']}
- Phone: {provider.get('phone', 'Not available')}
- Ownership Type: {provider.get('ownership_type', 'Not available')}
- Certification Date: {provider.get('certification_date', 'Not available')}

QUALITY METRICS:
- Quality Care Star Rating: {provider.get('quality_care_star_rating', 'Not rated')}/5
- HHCAHPS Star Rating: {provider.get('hhcahps_star_rating', 'Not rated')}/5
- Composite Quality Score: {provider.get('composite_quality_score', 'Not available')}
- High Quality Provider: {'Yes' if provider.get('is_high_quality') == 1 else 'No'}
- Survey Response Rate: {provider.get('survey_response_rate', 'Not available')}%
- Number of Completed Surveys: {provider.get('number_completed_surveys', 'Not available')}

SERVICES OFFERED:
- Skilled Nursing: {'Yes' if provider.get('offers_nursing') == 1 else 'No'}
- Physical Therapy: {'Yes' if provider.get('offers_physical_therapy') == 1 else 'No'}
- Occupational Therapy: {'Yes' if provider.get('offers_occupational_therapy') == 1 else 'No'}
- Speech Pathology: {'Yes' if provider.get('offers_speech_pathology') == 1 else 'No'}
- Medical Social Services: {'Yes' if provider.get('offers_medical_social') == 1 else 'No'}
- Home Health Aide: {'Yes' if provider.get('offers_home_health_aide') == 1 else 'No'}

VOLUME AND SIZE:
- Estimated Total Patients: {provider.get('estimated_total_patients', 'Not available')}
- Provider Size Category: {provider.get('provider_size_category', 'Not available')}
- Unique ZIP Codes Served: {provider.get('unique_zips_served', 'Not available')}

GEOGRAPHIC INFORMATION:
- County: {provider.get('county', 'Not available')}
- Enhanced County: {provider.get('x_county', 'Not available')}
- CBSA/Metro Area: {provider.get('x_cbsa_name', 'Not available')}
- Rural-Urban Classification: {provider.get('x_rucc_subcategory', 'Not available')}
- Population Density Category: {provider.get('x_density_category', 'Not available')}

COMPETITIVE POSITION:
- Market Rank: {competitor_analysis.get('market_rank', 'Not available')}
- Total Competitors in Area: {competitor_analysis.get('total_competitors', 'Not available')}
- Quality Ranking: {competitor_analysis.get('quality_ranking', 'Not available')}

GEOGRAPHIC COVERAGE:
- ZIP Codes Served: {coverage_analysis['coverage_stats']['total_zip_codes']}
- Service Area Summary: {len(coverage_analysis.get('zip_codes_served', []))} ZIP codes across multiple locations

This provider {'is a high-quality performer' if provider.get('is_high_quality') == 1 else 'has opportunities for quality improvement'} 
serving {provider.get('estimated_total_patients', 'an unknown number of')} patients with 
{provider.get('unique_zips_served', 'an unknown number of')} unique ZIP codes in their service area.
"""
        
        return summary.strip()
        
    finally:
        conn.close()
