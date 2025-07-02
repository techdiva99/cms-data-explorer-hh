#!/usr/bin/env python3
"""
CMS Home Health Data Explorer - Demo Script
Demonstrates key functionality and queries
"""

import sqlite3
import pandas as pd
from analytics import CMSAnalytics

def main():
    print("🏥 CMS Home Health Data Explorer - Demo")
    print("=" * 50)
    
    # Initialize analytics
    analytics = CMSAnalytics()
    
    # Demo 1: Provider Search by Location
    print("\n📍 Demo 1: Finding High-Quality Providers in Texas")
    print("-" * 50)
    
    tx_providers = analytics.find_providers_by_location(
        state="TX", 
        high_quality_only=True
    )
    
    print(f"Found {len(tx_providers)} high-quality providers in Texas")
    
    if len(tx_providers) > 0:
        top_5 = tx_providers.head(5)
        print("\nTop 5 Providers by Quality Score:")
        for i, provider in top_5.iterrows():
            print(f"  • {provider['provider_name']}")
            print(f"    City: {provider['city']}")
            print(f"    Quality Score: {provider['composite_quality_score']:.2f}")
            print(f"    Est. Patients: {int(provider['estimated_total_patients'] or 0):,}")
            print()
    
    # Demo 2: Market Analysis
    print("\n📊 Demo 2: Market Analysis for Houston, TX")
    print("-" * 50)
    
    houston_market = analytics.get_market_analysis("Houston", "TX")
    
    print(f"Total Providers: {houston_market['total_providers']}")
    print(f"High Quality Providers: {houston_market['high_quality_providers']}")
    print(f"High Quality Rate: {houston_market['high_quality_percentage']:.1f}%")
    print(f"Average Quality Score: {houston_market['average_quality_score']:.2f}")
    
    if houston_market['top_providers']:
        print("\nTop 3 Providers by Patient Volume:")
        for i, provider in enumerate(houston_market['top_providers'][:3]):
            print(f"  {i+1}. {provider['provider_name']}")
            print(f"     Quality: {provider['composite_quality_score']:.2f}")
            print(f"     Patients: {int(provider['estimated_total_patients']):,}")
    
    # Demo 3: Quality Benchmarks
    print("\n🎯 Demo 3: National Quality Benchmarks")
    print("-" * 50)
    
    benchmarks = analytics.get_quality_benchmarks()
    
    print(f"Total Providers Nationally: {benchmarks['total_providers']:,}")
    print(f"Average Quality Score: {benchmarks['mean_quality']:.2f}")
    print(f"Median Quality Score: {benchmarks['median_quality']:.2f}")
    
    print("\nQuality Distribution:")
    quality_dist = benchmarks['quality_distribution']
    print(f"  5-Star (Excellent): {quality_dist['5_star']:,} providers")
    print(f"  4-Star (Above Avg): {quality_dist['4_star']:,} providers")
    print(f"  3-Star (Average):   {quality_dist['3_star']:,} providers")
    print(f"  2-Star (Below Avg): {quality_dist['2_star']:,} providers")
    print(f"  1-Star (Poor):      {quality_dist['1_star']:,} providers")
    
    # Demo 4: Advanced Search
    print("\n🔍 Demo 4: Advanced Provider Search")
    print("-" * 50)
    
    advanced_results = analytics.search_providers_by_criteria(
        min_quality_score=4.0,
        min_patient_volume=500,
        ownership_type="NON-PROFIT",
        services_offered=["nursing", "physical_therapy"]
    )
    
    print(f"High-quality non-profit providers with 500+ patients")
    print(f"offering nursing and PT: {len(advanced_results)} found")
    
    if len(advanced_results) > 0:
        sample = advanced_results.head(3)
        for i, provider in sample.iterrows():
            print(f"\n  • {provider['provider_name']}")
            print(f"    Location: {provider['city']}, {provider['state']}")
            print(f"    Quality: {provider['composite_quality_score']:.2f}")
            print(f"    Patients: {int(provider['estimated_total_patients'] or 0):,}")
    
    # Demo 5: Competitive Analysis
    print("\n⚔️  Demo 5: Competitive Analysis")
    print("-" * 50)
    
    # Get a sample provider for competitive analysis
    sample_provider = tx_providers.iloc[0] if len(tx_providers) > 0 else None
    
    if sample_provider is not None:
        ccn = sample_provider['ccn']
        competition = analytics.get_competitor_analysis(ccn, radius_type="state")
        
        target = competition['target_provider']
        landscape = competition['competitive_landscape']
        
        print(f"Provider: {target['name']}")
        print(f"Quality Score: {target['quality_score']:.2f}")
        print(f"State Rank: #{target['rank']}")
        print(f"Percentile Rank: {landscape['percentile_rank']:.1f}%")
        print(f"Competitors in State: {landscape['total_competitors']}")
        print(f"Better Competitors: {landscape['better_competitors']}")
        
        if competition['top_competitors']:
            print(f"\nTop 3 Competitors:")
            for i, comp in enumerate(competition['top_competitors'][:3]):
                print(f"  {i+1}. {comp['provider_name']}")
                print(f"     Quality: {comp['composite_quality_score']:.2f}")
    
    # Summary Statistics
    print("\n📈 Summary Statistics")
    print("-" * 50)
    
    # Get overall database stats
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    
    stats_query = """
    SELECT 
        COUNT(*) as total_providers,
        COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_providers,
        AVG(composite_quality_score) as avg_quality,
        COUNT(DISTINCT state) as states_covered,
        SUM(estimated_total_patients) as total_patients
    FROM providers
    WHERE composite_quality_score IS NOT NULL
    """
    
    stats = pd.read_sql_query(stats_query, conn).iloc[0]
    
    print(f"Total Providers: {int(stats['total_providers']):,}")
    print(f"High Quality Providers: {int(stats['high_quality_providers']):,}")
    print(f"High Quality Rate: {(stats['high_quality_providers']/stats['total_providers']*100):.1f}%")
    print(f"Average Quality Score: {stats['avg_quality']:.2f}")
    print(f"States Covered: {int(stats['states_covered'])}")
    print(f"Total Estimated Patients: {int(stats['total_patients'] or 0):,}")
    
    conn.close()
    analytics.close()
    
    print("\n🎉 Demo completed successfully!")
    print("\nNext Steps:")
    print("1. Launch the web app: streamlit run streamlit_app.py")
    print("2. Install ChromaDB: pip install chromadb sentence-transformers")
    print("3. Run vector_database.py to enable AI search")
    print("4. Explore the interactive web interface!")

if __name__ == "__main__":
    main()
