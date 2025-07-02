#!/usr/bin/env python3
"""
Live test script for CMS Home Health Data Explorer
"""

def test_database():
    """Test database connectivity and data"""
    print("🗄️ Testing Database...")
    
    import sqlite3
    import pandas as pd
    
    # Connect to database
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    
    # Test 1: Basic counts
    total_providers = pd.read_sql("SELECT COUNT(*) as count FROM providers", conn).iloc[0]['count']
    print(f"✅ Total Providers: {total_providers:,}")
    
    hq_providers = pd.read_sql("SELECT COUNT(*) as count FROM providers WHERE is_high_quality = 1", conn).iloc[0]['count']
    print(f"✅ High Quality Providers: {hq_providers:,} ({hq_providers/total_providers*100:.1f}%)")
    
    # Test 2: Sample data
    sample_providers = pd.read_sql("""
        SELECT provider_name, city, state, composite_quality_score 
        FROM providers 
        WHERE is_high_quality = 1 
        ORDER BY composite_quality_score DESC 
        LIMIT 3
    """, conn)
    
    print("\n🏆 Top 3 High Quality Providers:")
    for _, row in sample_providers.iterrows():
        print(f"   • {row['provider_name']}")
        print(f"     {row['city']}, {row['state']} - Score: {row['composite_quality_score']:.2f}")
    
    # Test 3: Geographic distribution
    top_states = pd.read_sql("""
        SELECT state, COUNT(*) as count 
        FROM providers 
        GROUP BY state 
        ORDER BY count DESC 
        LIMIT 5
    """, conn)
    
    print("\n📍 Top 5 States by Provider Count:")
    for _, row in top_states.iterrows():
        print(f"   {row['state']}: {row['count']:,} providers")
    
    conn.close()
    return True

def test_analytics():
    """Test analytics module"""
    print("\n📊 Testing Analytics Module...")
    
    from analytics import CMSAnalytics
    
    analytics = CMSAnalytics()
    
    # Test California high-quality providers
    ca_providers = analytics.find_providers_by_location(state="CA", high_quality_only=True)
    print(f"✅ California High-Quality Providers: {len(ca_providers):,}")
    
    if len(ca_providers) > 0:
        top_ca = ca_providers.head(3)
        print("   Top 3 CA Providers:")
        for _, provider in top_ca.iterrows():
            print(f"   • {provider['provider_name']} ({provider['city']})")
    
    # Test quality benchmarks
    benchmarks = analytics.get_quality_benchmarks()
    print(f"✅ National Average Quality: {benchmarks['mean_quality']:.2f}")
    print(f"✅ Total Providers in Benchmark: {benchmarks['total_providers']:,}")
    
    analytics.close()
    return True

def test_search_scenarios():
    """Test common search scenarios"""
    print("\n🔍 Testing Search Scenarios...")
    
    from analytics import CMSAnalytics
    analytics = CMSAnalytics()
    
    # Scenario 1: Find providers in Texas
    tx_providers = analytics.find_providers_by_location(state="TX")
    print(f"✅ Texas Providers: {len(tx_providers):,}")
    
    # Scenario 2: High-quality providers with minimum volume
    quality_providers = analytics.search_providers_by_criteria(
        min_quality_score=4.0,
        min_patient_volume=100
    )
    print(f"✅ High-Quality Providers (4+ stars, 100+ patients): {len(quality_providers):,}")
    
    # Scenario 3: Market analysis for major city
    if len(tx_providers) > 0:
        # Get a city from Texas results
        sample_city = tx_providers.iloc[0]['city']
        market_data = analytics.get_market_analysis(sample_city, "TX")
        print(f"✅ Market Analysis for {sample_city}, TX:")
        print(f"   Total Providers: {market_data['total_providers']}")
        print(f"   High Quality: {market_data['high_quality_providers']}")
    
    analytics.close()
    return True

def main():
    print("🧪 CMS Home Health Data Explorer - Live Testing")
    print("=" * 55)
    
    try:
        test_database()
        test_analytics()
        test_search_scenarios()
        
        print("\n" + "=" * 55)
        print("🎉 ALL TESTS PASSED!")
        print("\n📋 Your system is ready for use:")
        print("1. Visit: http://localhost:8502")
        print("2. Try the Provider Search feature")
        print("3. Explore Market Analysis")
        print("4. Review Quality Benchmarks")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
