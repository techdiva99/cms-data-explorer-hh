"""
Quality Analytics Module - Quality benchmarking and provider comparison
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from .base import AnalyticsBase


class QualityAnalytics(AnalyticsBase):
    """
    Quality analytics for CMS Home Health data including benchmarking,
    provider comparisons, and quality distribution analysis.
    """
    
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
                county = provider.get('x_county') or provider.get('county')
                comparison_query = """
                SELECT * FROM providers 
                WHERE COALESCE(county, x_county) = ? AND state = ? AND composite_quality_score IS NOT NULL
                ORDER BY composite_quality_score DESC
                """
                comparison_providers = pd.read_sql_query(
                    comparison_query, conn, 
                    params=[county, provider['state']]
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
