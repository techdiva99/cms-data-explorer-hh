import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analytics import CMSAnalytics
import json

# Page configuration
st.set_page_config(
    page_title="CMS Home Health Data Explorer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analytics' not in st.session_state:
    st.session_state.analytics = CMSAnalytics()

# Title and description
st.title("🏥 CMS Home Health Data Explorer")
st.markdown("""
Explore home health provider quality metrics, market analysis, and geographic coverage.
Find high-quality providers by location and analyze competitive landscapes.
""")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page:",
    ["🔍 Provider Search", "🏙️ Metro Area Analysis", "🌾 Rural Health Analysis", "🏜️ Coverage Deserts", "📊 Market Analysis", "🎯 Quality Benchmarks", "⚖️ Provider Comparison", "📈 Data Overview"]
)

# Helper functions
@st.cache_data
def get_states():
    query = "SELECT DISTINCT state FROM providers ORDER BY state"
    conn = st.session_state.analytics._get_connection()
    try:
        states_df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return states_df['state'].tolist()

@st.cache_data  
def get_cities_by_state(state):
    query = "SELECT DISTINCT city FROM providers WHERE state = ? ORDER BY city"
    conn = st.session_state.analytics._get_connection()
    try:
        cities_df = pd.read_sql_query(query, conn, params=[state])
    finally:
        conn.close()
    return cities_df['city'].tolist()

# Page: Provider Search
if page == "🔍 Provider Search":
    st.header("Find Home Health Providers")
    
    # Search filters
    st.subheader("Search Filters")
    
    # Provider name and CCN search
    col1, col2 = st.columns(2)
    with col1:
        provider_name = st.text_input("🔍 Provider Name", placeholder="Enter provider name (partial matches allowed)")
    with col2:
        ccn_search = st.text_input("🏥 CCN", placeholder="Enter CCN (partial matches allowed)")
    
    # Geographic filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_state = st.selectbox("Select State", ["All"] + get_states())
        
    with col2:
        if search_state != "All":
            cities = get_cities_by_state(search_state)
            search_city = st.selectbox("Select City", ["All"] + cities)
        else:
            search_city = st.text_input("Enter City")
            
    with col3:
        search_zip = st.text_input("Enter ZIP Code")
    
    with col4:
        # CBSA search
        cbsa_search = st.text_input("🏙️ Metropolitan Area (CBSA)", 
                                   placeholder="e.g., Los Angeles, New York, Chicago",
                                   help="Search by Core Based Statistical Area / Metropolitan Area")
    
    # Quality and Geographic Classification filters
    col1, col2, col3 = st.columns(3)
    with col1:
        high_quality_only = st.checkbox("High Quality Providers Only")
        
    with col2:
        rural_filter = st.selectbox("Rural/Urban Filter", ["All", "Rural Only", "Urban Only", "Frontier Only"])
        
    with col3:
        min_quality = st.slider("Minimum Quality Score", 1.0, 5.0, 1.0, 0.5)
    
    # Search button
    if st.button("Search Providers", type="primary"):
        
        # Build search parameters
        search_params = {}
        if search_state != "All":
            search_params['state'] = search_state
        if search_city and search_city != "All":
            search_params['city'] = search_city
        if search_zip:
            search_params['zip_code'] = search_zip
        if provider_name:
            search_params['provider_name'] = provider_name
        if ccn_search:
            search_params['ccn'] = ccn_search
        
        # Get results
        try:
            # Handle CBSA search separately if provided
            if cbsa_search:
                results = st.session_state.analytics.find_providers_by_cbsa(cbsa_name=cbsa_search)
                
                # Apply additional filters to CBSA results
                if search_state != "All":
                    results = results[results['state'] == search_state]
                if search_city and search_city != "All":
                    results = results[results['city'].str.contains(search_city, case=False, na=False)]
                if search_zip:
                    results = results[results['zip_code'].str.contains(search_zip, na=False)]
                if provider_name:
                    results = results[results['provider_name'].str.contains(provider_name, case=False, na=False)]
                if ccn_search:
                    results = results[results['ccn'].str.contains(ccn_search, case=False, na=False)]
                if high_quality_only:
                    results = results[results['is_high_quality'] == 1]
                
                # Apply rural/urban filters
                if rural_filter == "Rural Only":
                    results = results[results['x_is_rural'] == 1]
                elif rural_filter == "Urban Only":
                    results = results[results['x_is_rural'] == 0]
                elif rural_filter == "Frontier Only":
                    results = results[results['x_is_frontier'] == 1]
                    
            elif search_params or high_quality_only or rural_filter != "All":
                results = st.session_state.analytics.find_providers_by_location(
                    **search_params,
                    high_quality_only=high_quality_only
                )
            else:
                results = st.session_state.analytics.search_providers_by_criteria(
                    min_quality_score=min_quality
                )
                
            # Filter by minimum quality
            if min_quality > 1.0:
                results = results[results['composite_quality_score'] >= min_quality]
            
            # Apply rural/urban filters if not already applied in CBSA search
            if not cbsa_search and rural_filter != "All":
                if rural_filter == "Rural Only":
                    results = results[results['x_is_rural'] == 1]
                elif rural_filter == "Urban Only":
                    results = results[results['x_is_rural'] == 0]
                elif rural_filter == "Frontier Only":
                    results = results[results['x_is_frontier'] == 1]
            
            # Calculate summary statistics
            total_patients = results['estimated_total_patients'].fillna(0).sum()
            unique_ccns = results['ccn'].nunique()  # Count unique CCNs
            unique_providers = results['provider_name'].nunique()  # Count unique provider names
            unique_states = results['state'].nunique()
            
            # Display results summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Unique CCNs", f"{unique_ccns:,}")
            with col2:
                st.metric("Unique Providers", f"{unique_providers:,}")
            with col3:
                st.metric("Total Est. Patient Volume", f"{int(total_patients):,}")
            with col4:
                st.metric("States Covered", f"{unique_states:,}")
            
            if not results.empty:
                # Display results - show all available columns including enhanced data
                display_cols = [
                    'ccn', 'provider_name', 'address', 'city', 'county', 'x_county', 'x_cbsa_name', 
                    'x_rucc_subcategory', 'x_density_category', 'state', 'zip_code',
                    'phone', 'ownership_type', 'certification_date',
                    'offers_nursing', 'offers_physical_therapy', 'offers_occupational_therapy',
                    'offers_speech_pathology', 'offers_medical_social', 'offers_home_health_aide',
                    'quality_care_star_rating', 'hhcahps_star_rating', 'composite_quality_score',
                    'is_high_quality', 'number_completed_surveys', 'survey_response_rate',
                    'estimated_total_patients', 'provider_size_category', 'unique_zips_served',
                    'latitude', 'longitude', 'x_latitude', 'x_longitude'
                ]
                
                # Only include columns that exist in the dataframe
                available_cols = [col for col in display_cols if col in results.columns]
                results_display = results[available_cols].copy()
                
                # Rename columns for display
                column_names = {
                    'ccn': 'CCN',
                    'provider_name': 'Provider Name',
                    'address': 'Address',
                    'city': 'City',
                    'county': 'County (Original)',
                    'x_county': 'County (Enhanced)',
                    'x_cbsa_name': 'Metro Area (CBSA)',
                    'x_rucc_subcategory': 'Rural-Urban Type',
                    'x_density_category': 'Population Density',
                    'state': 'State',
                    'zip_code': 'ZIP',
                    'phone': 'Phone',
                    'ownership_type': 'Ownership Type',
                    'certification_date': 'Certification Date',
                    'offers_nursing': 'Nursing',
                    'offers_physical_therapy': 'Physical Therapy',
                    'offers_occupational_therapy': 'Occupational Therapy',
                    'offers_speech_pathology': 'Speech Pathology',
                    'offers_medical_social': 'Medical Social',
                    'offers_home_health_aide': 'Home Health Aide',
                    'quality_care_star_rating': 'Quality Care Stars',
                    'hhcahps_star_rating': 'HHCAHPS Stars',
                    'composite_quality_score': 'Quality Score',
                    'is_high_quality': 'High Quality',
                    'number_completed_surveys': 'Completed Surveys',
                    'survey_response_rate': 'Response Rate %',
                    'estimated_total_patients': 'Est. Patients',
                    'provider_size_category': 'Size Category',
                    'unique_zips_served': 'Unique ZIPs Served',
                    'latitude': 'Latitude (Original)',
                    'longitude': 'Longitude (Original)',
                    'x_latitude': 'Latitude (Enhanced)',
                    'x_longitude': 'Longitude (Enhanced)'
                }
                
                results_display.columns = [column_names.get(col, col) for col in results_display.columns]
                
                # Format numeric columns
                if 'Quality Score' in results_display.columns:
                    results_display['Quality Score'] = results_display['Quality Score'].round(2)
                if 'Est. Patients' in results_display.columns:
                    results_display['Est. Patients'] = results_display['Est. Patients'].fillna(0).astype(int)
                
                # Configure column display
                column_config = {
                    'Quality Score': st.column_config.NumberColumn(
                        "Quality Score",
                        format="%.2f"
                    ),
                    'Est. Patients': st.column_config.NumberColumn(
                        "Est. Patients", 
                        format="%d"
                    )
                }
                
                st.dataframe(
                    results_display, 
                    use_container_width=True,
                    column_config=column_config
                )
                
                # Comprehensive analytics section
                st.subheader("📊 Search Results Analytics")
                
                # State-level analysis
                if unique_states > 1:
                    st.subheader("🗺️ State-Level Analysis")
                    
                    # Group by state for analysis
                    state_analysis = results.groupby('state').agg({
                        'ccn': 'nunique',  # Unique CCNs
                        'provider_name': 'nunique',  # Unique provider names
                        'county': 'nunique',  # Unique counties
                        'estimated_total_patients': ['sum', 'mean'],
                        'composite_quality_score': 'mean'
                    }).round(2)
                    
                    # Flatten column names
                    state_analysis.columns = ['Unique_CCNs', 'Unique_Providers', 'Unique_Counties', 'Total_Patients', 'Avg_Patients_Per_Provider', 'Avg_Quality_Score']
                    state_analysis = state_analysis.fillna(0)
                    state_analysis['Total_Patients'] = state_analysis['Total_Patients'].astype(int)
                    state_analysis['Avg_Patients_Per_Provider'] = state_analysis['Avg_Patients_Per_Provider'].astype(int)
                    state_analysis = state_analysis.reset_index()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # State volume distribution chart
                        fig = px.bar(
                            state_analysis.sort_values('Total_Patients', ascending=False),
                            x='state',
                            y='Total_Patients',
                            title="Total Patient Volume by State",
                            labels={'Total_Patients': 'Total Patients', 'state': 'State'}
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # State quality comparison chart
                        fig = px.bar(
                            state_analysis.sort_values('Avg_Quality_Score', ascending=False),
                            x='state',
                            y='Avg_Quality_Score',
                            title="Average Quality Score by State",
                            labels={'Avg_Quality_Score': 'Avg Quality Score', 'state': 'State'},
                            color='Avg_Quality_Score',
                            color_continuous_scale='viridis'
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # State summary table
                    st.subheader("State Summary Table")
                    st.dataframe(
                        state_analysis.sort_values('Total_Patients', ascending=False),
                        column_config={
                            'state': 'State',
                            'Unique_CCNs': st.column_config.NumberColumn('Unique CCNs', format='%d'),
                            'Unique_Providers': st.column_config.NumberColumn('Unique Providers', format='%d'),
                            'Unique_Counties': st.column_config.NumberColumn('Counties', format='%d'),
                            'Total_Patients': st.column_config.NumberColumn('Total Patients', format='%d'),
                            'Avg_Patients_Per_Provider': st.column_config.NumberColumn('Avg Patients/Provider', format='%d'),
                            'Avg_Quality_Score': st.column_config.NumberColumn('Avg Quality Score', format='%.2f')
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Enhanced County-level analysis
                county_col = 'x_county' if 'x_county' in results.columns else 'county'
                if county_col in results.columns and results[county_col].nunique() > 1:
                    st.subheader("🏘️ Enhanced County-Level Analysis")
                    st.info(f"Using {county_col} data ({results[county_col].nunique()} counties)")
                    
                    # Group by county and state for analysis
                    county_analysis = results.groupby([county_col, 'state']).agg({
                        'ccn': 'nunique',  # Unique CCNs
                        'provider_name': 'nunique',  # Unique provider names
                        'estimated_total_patients': ['sum', 'mean'],
                        'composite_quality_score': 'mean'
                    }).round(2)
                    
                    # Flatten column names
                    county_analysis.columns = ['Unique_CCNs', 'Unique_Providers', 'Total_Patients', 'Avg_Patients_Per_Provider', 'Avg_Quality_Score']
                    county_analysis = county_analysis.fillna(0)
                    county_analysis['Total_Patients'] = county_analysis['Total_Patients'].astype(int)
                    county_analysis['Avg_Patients_Per_Provider'] = county_analysis['Avg_Patients_Per_Provider'].astype(int)
                    county_analysis = county_analysis.reset_index()
                    county_analysis['County_State'] = county_analysis[county_col] + ', ' + county_analysis['state']
                    
                    # Show top counties by volume and quality
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**🔝 Top Counties by Patient Volume**")
                        top_volume_counties = county_analysis.nlargest(10, 'Total_Patients')[
                            ['County_State', 'Unique_CCNs', 'Unique_Providers', 'Total_Patients', 'Avg_Quality_Score']
                        ]
                        st.dataframe(
                            top_volume_counties,
                            column_config={
                                'County_State': 'County, State',
                                'Unique_CCNs': st.column_config.NumberColumn('CCNs', format='%d'),
                                'Unique_Providers': st.column_config.NumberColumn('Providers', format='%d'),
                                'Total_Patients': st.column_config.NumberColumn('Total Patients', format='%d'),
                                'Avg_Quality_Score': st.column_config.NumberColumn('Avg Quality', format='%.2f')
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    with col2:
                        st.write("**⭐ Top Counties by Quality Score**")
                        top_quality_counties = county_analysis.nlargest(10, 'Avg_Quality_Score')[
                            ['County_State', 'Unique_CCNs', 'Unique_Providers', 'Total_Patients', 'Avg_Quality_Score']
                        ]
                        st.dataframe(
                            top_quality_counties,
                            column_config={
                                'County_State': 'County, State',
                                'Unique_CCNs': st.column_config.NumberColumn('CCNs', format='%d'),
                                'Unique_Providers': st.column_config.NumberColumn('Providers', format='%d'),
                                'Total_Patients': st.column_config.NumberColumn('Total Patients', format='%d'),
                                'Avg_Quality_Score': st.column_config.NumberColumn('Avg Quality', format='%.2f')
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    # County scatter plot - Volume vs Quality
                    st.subheader("County Performance: Volume vs Quality (All Counties)")
                    # Clean data to handle NaN values
                    county_plot_data = county_analysis.copy()
                    county_plot_data['Total_Patients'] = county_plot_data['Total_Patients'].fillna(0)
                    county_plot_data['Avg_Quality_Score'] = county_plot_data['Avg_Quality_Score'].fillna(0)
                    county_plot_data['Unique_CCNs'] = county_plot_data['Unique_CCNs'].fillna(1)
                    
                    fig = px.scatter(
                        county_plot_data,
                        x='Total_Patients',
                        y='Avg_Quality_Score',
                        size='Unique_CCNs',
                        hover_name='County_State',
                        hover_data={
                            'Unique_CCNs': True,
                            'Unique_Providers': True,
                            'Total_Patients': ':,',
                            'Avg_Quality_Score': ':.2f'
                        },
                        title="County Performance: Patient Volume vs Quality Score (All Counties)",
                        labels={
                            'Total_Patients': 'Total Patient Volume',
                            'Avg_Quality_Score': 'Average Quality Score',
                            'Unique_CCNs': 'Number of CCNs'
                        }
                    )
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Volume and quality distribution summary
                st.subheader("📈 Volume & Quality Distribution Summary")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Volume Distribution:**")
                    volume_stats = results['estimated_total_patients'].fillna(0)
                    small_providers = (volume_stats < 100).sum()
                    medium_providers = ((volume_stats >= 100) & (volume_stats < 500)).sum()
                    large_providers = (volume_stats >= 500).sum()
                    
                    st.write(f"• Small (< 100 patients): {small_providers:,} providers")
                    st.write(f"• Medium (100-499 patients): {medium_providers:,} providers") 
                    st.write(f"• Large (500+ patients): {large_providers:,} providers")
                
                with col2:
                    st.write("**Quality Distribution:**")
                    if 'composite_quality_score' in results.columns:
                        quality_stats = results['composite_quality_score'].dropna()
                        if len(quality_stats) > 0:
                            high_quality = (quality_stats >= 4.0).sum()
                            good_quality = ((quality_stats >= 3.0) & (quality_stats < 4.0)).sum()
                            average_quality = (quality_stats < 3.0).sum()
                            
                            st.write(f"• High Quality (4.0+ stars): {high_quality:,} providers")
                            st.write(f"• Good Quality (3.0-3.9 stars): {good_quality:,} providers")
                            st.write(f"• Below Average (< 3.0 stars): {average_quality:,} providers")
                        else:
                            st.write("No quality data available")
                    else:
                        st.write("Quality data not available")
                        
            else:
                st.info("ℹ️ No providers found matching your criteria. Try adjusting your search filters.")
                
        except Exception as e:
            st.error(f"Search error: {str(e)}")

# Page: Coverage Deserts
elif page == "🏜️ Coverage Deserts":
    st.header("🏜️ Coverage Deserts Analysis")
    st.markdown("""
    **Identify underserved areas with limited home health provider coverage.**  
    Discover market opportunities by analyzing ZIP codes with few or no providers within a reasonable distance.
    """)
    
    # Coverage Desert Discovery
    with st.expander("🔍 Discover Coverage Deserts", expanded=True):
        st.subheader("Search Parameters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            radius_miles = st.slider("Search Radius (miles)", 10, 100, 25, 5,
                                    help="Maximum distance to search for providers")
        
        with col2:
            min_medicare_pop = st.number_input("Min Medicare Population", 50, 1000, 100, 50,
                                             help="Minimum Medicare eligible population in ZIP code")
        
        with col3:
            max_providers = st.selectbox("Max Providers in Area", [0, 1, 2, 3], index=2,
                                       help="Maximum number of providers to be considered underserved")
        
        with col4:
            state_filter = st.selectbox("State Filter", ["All States"] + get_states())
            desert_state = None if state_filter == "All States" else state_filter
        
        # Advanced filters
        col1, col2 = st.columns(2)
        with col1:
            rural_only = st.checkbox("Rural Areas Only", help="Focus analysis on rural ZIP codes only")
        
        if st.button("🔍 Find Coverage Deserts", type="primary"):
            try:
                with st.spinner("Analyzing coverage deserts..."):
                    desert_results = st.session_state.analytics.identify_coverage_deserts(
                        radius_miles=radius_miles,
                        min_medicare_population=min_medicare_pop,
                        max_providers_in_radius=max_providers,
                        state_filter=desert_state,
                        rural_only=rural_only
                    )
                
                if not desert_results.empty:
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Underserved ZIP Codes", f"{len(desert_results):,}")
                    with col2:
                        total_medicare = desert_results['medicare_enrolled'].sum()
                        st.metric("Total Medicare Population", f"{int(total_medicare):,}")
                    with col3:
                        avg_opportunity = desert_results['market_opportunity_score'].mean()
                        st.metric("Avg Opportunity Score", f"{avg_opportunity:.1f}")
                    with col4:
                        states_affected = desert_results['state'].nunique()
                        st.metric("States Affected", states_affected)
                    
                    # Interactive Map
                    st.subheader("🗺️ Coverage Desert Map")
                    
                    # Create map with desert areas
                    map_data = desert_results.copy()
                    map_data['size'] = map_data['medicare_enrolled'] / 50  # Scale for bubble size
                    
                    fig = px.scatter_mapbox(
                        map_data,
                        lat="latitude",
                        lon="longitude",
                        size="size",
                        color="desert_severity",
                        hover_data={
                            "zip_code": True,
                            "city": True,
                            "state": True,
                            "medicare_enrolled": ":,",
                            "providers_within_radius": True,
                            "market_opportunity_score": ":.1f"
                        },
                        color_discrete_map={
                            "Complete Desert": "red",
                            "Severe Underservice": "orange", 
                            "Moderate Underservice": "yellow"
                        },
                        title=f"Coverage Deserts ({radius_miles} mile radius)",
                        mapbox_style="open-street-map",
                        height=600,
                        zoom=4
                    )
                    fig.update_layout(mapbox_style="open-street-map")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Desert severity breakdown
                    st.subheader("📊 Desert Severity Analysis")
                    
                    severity_summary = desert_results.groupby('desert_severity').agg({
                        'zip_code': 'count',
                        'medicare_enrolled': 'sum',
                        'market_opportunity_score': 'sum'
                    }).reset_index()
                    severity_summary.columns = ['Severity', 'ZIP Codes', 'Medicare Population', 'Total Opportunity Score']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Severity distribution pie chart
                        fig = px.pie(
                            severity_summary,
                            values='ZIP Codes',
                            names='Severity',
                            title="Distribution by Severity Level",
                            color_discrete_map={
                                "Complete Desert": "red",
                                "Severe Underservice": "orange",
                                "Moderate Underservice": "yellow"
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Market opportunity by severity
                        fig = px.bar(
                            severity_summary,
                            x='Severity',
                            y='Total Opportunity Score',
                            title="Market Opportunity by Severity",
                            color='Severity',
                            color_discrete_map={
                                "Complete Desert": "red",
                                "Severe Underservice": "orange",
                                "Moderate Underservice": "yellow"
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Severity summary table
                    st.dataframe(
                        severity_summary,
                        column_config={
                            'Severity': 'Desert Severity',
                            'ZIP Codes': st.column_config.NumberColumn('ZIP Codes', format='%d'),
                            'Medicare Population': st.column_config.NumberColumn('Medicare Population', format='%d'),
                            'Total Opportunity Score': st.column_config.NumberColumn('Opportunity Score', format='%.1f')
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Top opportunities table
                    st.subheader("🎯 Top Market Opportunities")
                    
                    top_opportunities = desert_results.head(20)
                    
                    display_cols = [
                        'zip_code', 'city', 'state', 'county', 'desert_severity',
                        'medicare_enrolled', 'providers_within_radius', 'market_opportunity_score'
                    ]
                    
                    display_data = top_opportunities[display_cols].copy()
                    
                    st.dataframe(
                        display_data,
                        column_config={
                            'zip_code': 'ZIP Code',
                            'city': 'City',
                            'state': 'State',
                            'county': 'County',
                            'desert_severity': 'Severity',
                            'medicare_enrolled': st.column_config.NumberColumn('Medicare Population', format='%d'),
                            'providers_within_radius': st.column_config.NumberColumn('Providers in Area', format='%d'),
                            'market_opportunity_score': st.column_config.NumberColumn('Opportunity Score', format='%.1f')
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Export functionality
                    st.subheader("📥 Export Results")
                    
                    csv_data = desert_results.to_csv(index=False)
                    st.download_button(
                        label="📄 Download Coverage Desert Data (CSV)",
                        data=csv_data,
                        file_name=f"coverage_deserts_{radius_miles}mi_{min_medicare_pop}pop.csv",
                        mime="text/csv"
                    )
                    
                else:
                    st.info("🎉 No significant coverage deserts found with the current criteria. Try adjusting your search parameters.")
                    
            except Exception as e:
                st.error(f"Error analyzing coverage deserts: {str(e)}")
    
    # Market Potential Calculator
    with st.expander("💰 Market Potential Calculator", expanded=False):
        st.subheader("Calculate Market Potential for Specific ZIP Codes")
        
        zip_input = st.text_area(
            "Enter ZIP Codes (one per line or comma-separated):",
            placeholder="90210\n10001\n60601",
            help="Enter the ZIP codes you want to analyze for market potential"
        )
        
        if st.button("💰 Calculate Market Potential"):
            if zip_input.strip():
                # Parse ZIP codes
                zip_codes = []
                for line in zip_input.strip().split('\n'):
                    zip_codes.extend([z.strip() for z in line.split(',') if z.strip()])
                
                zip_codes = [z for z in zip_codes if z.isdigit() and len(z) == 5]
                
                if zip_codes:
                    try:
                        market_potential = st.session_state.analytics.calculate_market_potential(zip_codes)
                        
                        if 'error' not in market_potential:
                            # Display market summary
                            col1, col2, col3, col4 = st.columns(4)
                            
                            summary = market_potential['market_summary']
                            
                            with col1:
                                st.metric("ZIP Codes", summary['total_zip_codes'])
                                st.metric("States", summary['states_covered'])
                            
                            with col2:
                                st.metric("Total Population", f"{summary['total_population']:,}")
                                st.metric("Counties", summary['counties_covered'])
                            
                            with col3:
                                st.metric("Medicare Eligible", f"{summary['total_medicare_eligibles']:,}")
                                st.metric("Medicare Enrolled", f"{summary['total_medicare_enrolled']:,}")
                            
                            with col4:
                                st.metric("Rural ZIPs", summary['rural_zip_count'])
                                st.metric("Frontier ZIPs", summary['frontier_zip_count'])
                            
                            # Market opportunity
                            st.subheader("💡 Market Opportunity")
                            opportunity = market_potential['market_opportunity']
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Estimated Annual Market Value", 
                                    f"${opportunity['estimated_annual_market_value']:,.0f}",
                                    help="Rough estimate based on average Medicare home health spending"
                                )
                            
                            with col2:
                                st.metric(
                                    "Medicare Penetration", 
                                    f"{opportunity['medicare_market_penetration']:.1f}%"
                                )
                            
                            # Geographic span
                            geo_span = market_potential['geographic_span']
                            st.subheader("🗺️ Geographic Coverage")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("North-South Span", f"{geo_span['approximate_miles_north_south']:.1f} miles")
                            with col2:
                                st.metric("East-West Span", f"{geo_span['approximate_miles_east_west']:.1f} miles")
                            
                        else:
                            st.error(market_potential['error'])
                    except Exception as e:
                        st.error(f"Error calculating market potential: {str(e)}")
                else:
                    st.warning("Please enter valid 5-digit ZIP codes.")
            else:
                st.warning("Please enter at least one ZIP code.")
    
    # Provider Expansion Analysis
    with st.expander("🚀 Provider Expansion Analysis", expanded=False):
        st.subheader("Analyze Expansion Opportunities for Existing Providers")
        
        # Provider selection
        try:
            all_providers_query = """
            SELECT ccn, provider_name, city, state 
            FROM providers 
            ORDER BY provider_name
            LIMIT 1000
            """
            conn = st.session_state.analytics._get_connection()
            try:
                all_providers = pd.read_sql_query(all_providers_query, conn)
            finally:
                conn.close()
            
            # Create display options
            provider_options = ["Select a provider..."]
            provider_mapping = {"Select a provider...": None}
            
            for _, row in all_providers.iterrows():
                display_text = f"{row['provider_name']} ({row['city']}, {row['state']})"
                provider_options.append(display_text)
                provider_mapping[display_text] = row['ccn']
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_provider = st.selectbox(
                    "Select Provider for Expansion Analysis:",
                    provider_options
                )
            
            with col2:
                expansion_radius = st.slider("Expansion Radius (miles)", 25, 200, 75, 25)
            
            if selected_provider != "Select a provider..." and st.button("🚀 Analyze Expansion Opportunities"):
                selected_ccn = provider_mapping[selected_provider]
                
                try:
                    expansion_analysis = st.session_state.analytics.analyze_provider_expansion_opportunity(
                        selected_ccn, expansion_radius
                    )
                    
                    if 'error' not in expansion_analysis:
                        provider_info = expansion_analysis['provider_info']
                        analysis = expansion_analysis['expansion_analysis']
                        
                        # Provider info
                        st.subheader(f"📋 {provider_info['name']}")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Location:** {provider_info['city']}, {provider_info['state']}")
                            st.write(f"**CCN:** {provider_info['ccn']}")
                        
                        with col2:
                            st.write(f"**Quality Score:** {provider_info['current_quality_score']:.2f}")
                            st.write(f"**Search Radius:** {analysis['search_radius_miles']} miles")
                        
                        with col3:
                            st.metric("Desert Opportunities", analysis['total_desert_opportunities'])
                            st.metric("Opportunity Population", f"{analysis['total_opportunity_population']:,}")
                        
                        # Expansion opportunities
                        if analysis['total_desert_opportunities'] > 0:
                            st.subheader("🎯 Top Expansion Targets")
                            
                            targets = expansion_analysis['top_expansion_targets']
                            targets_df = pd.DataFrame(targets)
                            
                            if not targets_df.empty:
                                st.dataframe(
                                    targets_df[['zip_code', 'city', 'state', 'distance_from_provider', 
                                              'medicare_enrolled', 'market_opportunity_score']],
                                    column_config={
                                        'zip_code': 'ZIP Code',
                                        'city': 'City', 
                                        'state': 'State',
                                        'distance_from_provider': st.column_config.NumberColumn('Distance (mi)', format='%.1f'),
                                        'medicare_enrolled': st.column_config.NumberColumn('Medicare Pop', format='%d'),
                                        'market_opportunity_score': st.column_config.NumberColumn('Opportunity Score', format='%.1f')
                                    },
                                    hide_index=True,
                                    use_container_width=True
                                )
                        else:
                            st.info("🎉 No significant coverage deserts found within the expansion radius. This provider appears to be in a well-served market.")
                    
                    else:
                        st.error(expansion_analysis['error'])
                        
                except Exception as e:
                    st.error(f"Error analyzing expansion opportunities: {str(e)}")
            
        except Exception as e:
            st.error(f"Error loading providers: {str(e)}")

# Page: Market Analysis  
elif page == "📊 Market Analysis":
    st.header("Market Analysis")
    
    # Location selection
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_state = st.selectbox("Select State for Analysis", get_states())
        
    with col2:
        analysis_cities = get_cities_by_state(analysis_state)
        analysis_city = st.selectbox("Select City/County", analysis_cities)
    
    if st.button("Analyze Market", type="primary"):
        try:
            # Get market analysis
            market_data = st.session_state.analytics.get_market_analysis(analysis_city, analysis_state)
            
            # Display key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Providers", market_data['total_providers'])
                
            with col2:
                st.metric("High Quality Providers", market_data['high_quality_providers'])
                
            with col3:
                st.metric("Quality Rate", f"{market_data['high_quality_percentage']:.1f}%")
                
            with col4:
                avg_quality = market_data['average_quality_score']
                st.metric("Avg Quality Score", f"{avg_quality:.2f}" if avg_quality else "N/A")
            
            # Provider quality distribution
            if market_data['all_providers']:
                providers_df = pd.DataFrame(market_data['all_providers'])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Quality Score Distribution")
                    if 'composite_quality_score' in providers_df.columns:
                        fig = px.histogram(
                            providers_df, 
                            x='composite_quality_score',
                            nbins=20,
                            title="Provider Quality Scores"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                with col2:
                    st.subheader("Ownership Type Distribution")
                    if 'ownership_type' in providers_df.columns:
                        ownership_counts = providers_df['ownership_type'].value_counts()
                        fig = px.pie(
                            values=ownership_counts.values,
                            names=ownership_counts.index,
                            title="Provider Ownership Types"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            # Top providers
            st.subheader("Top Providers by Patient Volume")
            if market_data['top_providers']:
                top_df = pd.DataFrame(market_data['top_providers'])
                st.dataframe(top_df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")

# Page: Quality Benchmarks
elif page == "🎯 Quality Benchmarks":
    st.header("Quality Benchmarks")
    
    # Benchmark selection
    benchmark_scope = st.selectbox(
        "Select Benchmark Scope:",
        ["National", "State-specific"]
    )
    
    if benchmark_scope == "State-specific":
        benchmark_state = st.selectbox("Select State:", get_states())
    else:
        benchmark_state = None
    
    if st.button("Get Benchmarks", type="primary"):
        try:
            # Get benchmarks
            benchmarks = st.session_state.analytics.get_quality_benchmarks(state=benchmark_state)
            
            if 'error' not in benchmarks:
                # Display statistics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Providers", f"{benchmarks['total_providers']:,}")
                    st.metric("Mean Quality", f"{benchmarks['mean_quality']:.2f}")
                    
                with col2:
                    st.metric("Median Quality", f"{benchmarks['median_quality']:.2f}")
                    st.metric("Standard Deviation", f"{benchmarks['std_quality']:.2f}")
                    
                with col3:
                    st.metric("75th Percentile", f"{benchmarks['percentiles']['75th']:.2f}")
                    st.metric("90th Percentile", f"{benchmarks['percentiles']['90th']:.2f}")
                
                # Quality distribution chart
                st.subheader("Quality Distribution")
                
                quality_dist = benchmarks['quality_distribution']
                
                # Create bar chart
                categories = ['1 Star', '2 Star', '3 Star', '4 Star', '5 Star']
                values = [
                    quality_dist['1_star'],
                    quality_dist['2_star'], 
                    quality_dist['3_star'],
                    quality_dist['4_star'],
                    quality_dist['5_star']
                ]
                
                fig = px.bar(
                    x=categories,
                    y=values,
                    title=f"Provider Quality Distribution ({benchmark_scope})",
                    labels={'x': 'Star Rating', 'y': 'Number of Providers'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error("No benchmark data available for the selected scope.")
                
        except Exception as e:
            st.error(f"Benchmark error: {str(e)}")

# Page: Provider Comparison
elif page == "⚖️ Provider Comparison":
    st.header("⚖️ Provider Comparison")
    st.write("Compare a provider's performance against competitors with detailed analytics and visualizations.")
    
    # Provider selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get all providers for selection
        try:
            all_providers_query = """
            SELECT ccn, provider_name, city, state, composite_quality_score 
            FROM providers 
            WHERE composite_quality_score IS NOT NULL
            ORDER BY provider_name
            """
            conn = st.session_state.analytics._get_connection()
            try:
                all_providers = pd.read_sql_query(all_providers_query, conn)
            finally:
                conn.close()
            
            # Create display text for selectbox
            provider_options = []
            provider_mapping = {}
            for _, row in all_providers.iterrows():
                display_text = f"{row['provider_name']} ({row['city']}, {row['state']}) - Score: {row['composite_quality_score']:.2f}"
                provider_options.append(display_text)
                provider_mapping[display_text] = row['ccn']
            
            selected_provider = st.selectbox(
                "Select a Provider to Compare:",
                provider_options,
                help="Choose a provider to see how they compare against their competitors"
            )
            
        except Exception as e:
            st.error(f"Error loading providers: {str(e)}")
            selected_provider = None
            provider_mapping = {}
    
    with col2:
        comparison_scope = st.selectbox(
            "Comparison Scope:",
            ["state", "county", "national"],
            help="Choose the geographic scope for comparison"
        )
    
    if selected_provider and selected_provider in provider_mapping:
        selected_ccn = provider_mapping[selected_provider]
        
        try:
            # Get comparison analysis
            comparison_data = st.session_state.analytics.get_provider_comparison_analysis(
                selected_ccn, comparison_scope
            )
            
            if "error" not in comparison_data:
                target = comparison_data['target_provider']
                stats = comparison_data['comparison_stats']
                market = comparison_data['market_stats']
                
                # Display provider summary
                st.subheader(f"📋 {target['name']}")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Quality Score", f"{target['quality_score']:.2f}")
                with col2:
                    st.metric("Rank", f"{stats['provider_rank']} of {stats['total_providers']}")
                with col3:
                    st.metric("Percentile", f"{stats['percentile']:.1f}%")
                with col4:
                    quality_status = "🟢 High Quality" if target['is_high_quality'] else "🔴 Below Average"
                    st.metric("Status", quality_status)
                
                # Bell curve visualization
                st.subheader("📊 Quality Distribution & Position")
                
                import numpy as np
                
                # Create bell curve chart
                quality_scores = comparison_data['quality_distribution']
                provider_score = target['quality_score']
                
                # Create histogram for distribution
                fig = go.Figure()
                
                # Add histogram of all providers
                fig.add_trace(go.Histogram(
                    x=quality_scores,
                    nbinsx=30,
                    name=f'{comparison_scope.title()} Providers',
                    opacity=0.7,
                    marker_color='lightblue',
                    yaxis='y'
                ))
                
                # Add normal distribution curve
                x_range = np.linspace(min(quality_scores), max(quality_scores), 100)
                normal_curve = (1 / (market['std_quality'] * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_range - market['mean_quality']) / market['std_quality']) ** 2)
                normal_curve = normal_curve * len(quality_scores) * (max(quality_scores) - min(quality_scores)) / 30  # Scale to histogram
                
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=normal_curve,
                    mode='lines',
                    name='Normal Distribution',
                    line=dict(color='orange', width=2),
                    yaxis='y'
                ))
                
                # Add vertical line for provider position
                fig.add_vline(
                    x=provider_score,
                    line_dash="dash",
                    line_color="red",
                    line_width=3,
                    annotation_text=f"{target['name']}<br>Score: {provider_score:.2f}",
                    annotation_position="top"
                )
                
                # Add mean line
                fig.add_vline(
                    x=market['mean_quality'],
                    line_dash="dot",
                    line_color="green",
                    line_width=2,
                    annotation_text=f"Market Average<br>{market['mean_quality']:.2f}",
                    annotation_position="bottom"
                )
                
                fig.update_layout(
                    title=f"Quality Score Distribution - {comparison_scope.title()} Comparison",
                    xaxis_title="Quality Score",
                    yaxis_title="Number of Providers",
                    showlegend=True,
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistical summary
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📈 Statistical Analysis")
                    st.write(f"**Z-Score:** {stats['z_score']:.2f} standard deviations from mean")
                    if stats['z_score'] > 1:
                        st.success("🟢 Significantly above average")
                    elif stats['z_score'] > 0:
                        st.info("🔵 Above average")
                    elif stats['z_score'] > -1:
                        st.warning("🟡 Below average")
                    else:
                        st.error("🔴 Significantly below average")
                    
                    st.write(f"**Market Statistics ({comparison_scope.title()}):**")
                    st.write(f"- Mean: {market['mean_quality']:.2f}")
                    st.write(f"- Median: {market['median_quality']:.2f}")
                    st.write(f"- Std Dev: {market['std_quality']:.2f}")
                    st.write(f"- Range: {market['min_quality']:.2f} - {market['max_quality']:.2f}")
                
                with col2:
                    st.subheader("🎯 Performance Context")
                    
                    percentile_color = "🟢" if stats['percentile'] >= 75 else "🔵" if stats['percentile'] >= 50 else "🟡" if stats['percentile'] >= 25 else "🔴"
                    st.write(f"{percentile_color} **{stats['percentile']:.1f}th percentile** performance")
                    
                    if stats['percentile'] >= 90:
                        st.success("Top 10% performer - Exceptional quality!")
                    elif stats['percentile'] >= 75:
                        st.success("Top 25% performer - Very good quality")
                    elif stats['percentile'] >= 50:
                        st.info("Above median - Good quality")
                    elif stats['percentile'] >= 25:
                        st.warning("Below median - Room for improvement")
                    else:
                        st.error("Bottom 25% - Significant improvement needed")
                
                # Competitor tables
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🏆 Top Performers")
                    top_df = pd.DataFrame(comparison_data['top_performers'])
                    if not top_df.empty:
                        # Format patient numbers as integers
                        if 'estimated_total_patients' in top_df.columns:
                            top_df['estimated_total_patients'] = top_df['estimated_total_patients'].fillna(0).astype(int)
                        
                        st.dataframe(
                            top_df.round(2),
                            column_config={
                                "provider_name": "Provider Name",
                                "city": "City",
                                "composite_quality_score": "Quality Score",
                                "estimated_total_patients": st.column_config.NumberColumn(
                                    "Est. Patients",
                                    format="%d"
                                )
                            },
                            hide_index=True
                        )
                
                with col2:
                    st.subheader("⚖️ Similar Quality Providers")
                    similar_df = pd.DataFrame(comparison_data['similar_providers'])
                    if not similar_df.empty:
                        # Format patient numbers as integers
                        if 'estimated_total_patients' in similar_df.columns:
                            similar_df['estimated_total_patients'] = similar_df['estimated_total_patients'].fillna(0).astype(int)
                        
                        st.dataframe(
                            similar_df.round(2),
                            column_config={
                                "provider_name": "Provider Name",
                                "city": "City", 
                                "composite_quality_score": "Quality Score",
                                "estimated_total_patients": st.column_config.NumberColumn(
                                    "Est. Patients",
                                    format="%d"
                                )
                            },
                            hide_index=True
                        )
            else:
                st.error(comparison_data.get("error", "Unknown error"))
                
        except Exception as e:
            st.error(f"Comparison error: {str(e)}")

# Page: Data Overview
elif page == "📈 Data Overview":
    st.header("Data Overview")
    
    try:
        # Get overall statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_providers,
            COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_providers,
            AVG(composite_quality_score) as avg_quality,
            COUNT(DISTINCT state) as states_covered,
            COUNT(DISTINCT city) as cities_covered,
            SUM(estimated_total_patients) as total_patients
        FROM providers
        """
        
        conn = st.session_state.analytics._get_connection()
        try:
            stats_df = pd.read_sql_query(stats_query, conn)
        finally:
            conn.close()
        stats = stats_df.iloc[0]
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Providers", f"{int(stats['total_providers']):,}")
            st.metric("High Quality Providers", f"{int(stats['high_quality_providers']):,}")
            
        with col2:
            st.metric("Average Quality Score", f"{stats['avg_quality']:.2f}")
            st.metric("States Covered", int(stats['states_covered']))
            
        with col3:
            hq_percentage = (stats['high_quality_providers'] / stats['total_providers'] * 100)
            st.metric("High Quality %", f"{hq_percentage:.1f}%")
            total_patients = int(stats['total_patients']) if pd.notna(stats['total_patients']) else 0
            st.metric("Total Est. Patients", f"{total_patients:,}")
        
        # Geographic distribution
        st.subheader("Geographic Distribution")
        
        geo_query = """
        SELECT 
            state,
            COUNT(*) as provider_count,
            COUNT(CASE WHEN is_high_quality = 1 THEN 1 END) as high_quality_count,
            AVG(composite_quality_score) as avg_quality,
            SUM(estimated_total_patients) as total_volume
        FROM providers
        GROUP BY state
        ORDER BY provider_count DESC
        """
        
        conn = st.session_state.analytics._get_connection()
        try:
            geo_df = pd.read_sql_query(geo_query, conn)
        finally:
            conn.close()
        geo_df['high_quality_rate'] = (geo_df['high_quality_count'] / geo_df['provider_count'] * 100).round(1)
        
        # Radio button to choose between Quality and Volume
        chart_type = st.radio(
            "Select metric to display by state:",
            ["Average Quality Score", "Total Patient Volume"],
            horizontal=True
        )
        
        # Prepare data based on selection
        top_states = geo_df.head(15).copy()
        
        if chart_type == "Average Quality Score":
            y_column = 'avg_quality'
            title = "Average Quality Score by State (Top 15 by Provider Count)"
            y_label = "Average Quality Score"
            color_scale = 'viridis'
        else:
            y_column = 'total_volume'
            title = "Total Patient Volume by State (Top 15 by Provider Count)"
            y_label = "Total Estimated Patients"
            color_scale = 'blues'
            # Format volume numbers
            top_states['total_volume'] = top_states['total_volume'].fillna(0)
        
        # Create the bar chart
        fig = px.bar(
            top_states,
            x='state',
            y=y_column,
            title=title,
            labels={'state': 'State', y_column: y_label},
            color=y_column,
            color_continuous_scale=color_scale
        )
        
        # Customize the chart
        fig.update_layout(
            xaxis_title="State",
            yaxis_title=y_label,
            showlegend=False
        )
        
        # Add value labels on bars for better readability
        if chart_type == "Average Quality Score":
            fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
        else:
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show summary table with both metrics
        st.subheader("State Summary Table")
        summary_df = top_states[['state', 'provider_count', 'avg_quality', 'total_volume', 'high_quality_rate']].copy()
        summary_df['total_volume'] = summary_df['total_volume'].fillna(0).astype(int)
        
        st.dataframe(
            summary_df,
            column_config={
                'state': 'State',
                'provider_count': 'Total Providers',
                'avg_quality': st.column_config.NumberColumn('Avg Quality Score', format="%.2f"),
                'total_volume': st.column_config.NumberColumn('Total Patient Volume', format="%d"),
                'high_quality_rate': st.column_config.NumberColumn('High Quality %', format="%.1f%%")
            },
            hide_index=True,
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Data overview error: {str(e)}")

# Enhanced geographic analysis section
if st.sidebar.button("🌍 Geographic Analysis (New!)"):
        st.header("🌍 Enhanced Geographic Analysis")
        st.markdown("**Using enhanced ZIP code to county crosswalk data with lat/lng coordinates**")
        
        # Coverage improvement report
        with st.expander("📈 Data Coverage Improvement Report", expanded=True):
            try:
                coverage_report = st.session_state.analytics.get_coverage_improvement_report()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Providers", f"{coverage_report['total_providers']:,}")
                with col2:
                    st.metric("Original County Coverage", 
                             f"{coverage_report['original_county_coverage']:,}",
                             f"{round(coverage_report['original_county_coverage']/coverage_report['total_providers']*100, 1)}%")
                with col3:
                    st.metric("Enhanced County Coverage", 
                             f"{coverage_report['enhanced_county_coverage']:,}",
                             f"{round(coverage_report['enhanced_county_coverage']/coverage_report['total_providers']*100, 1)}%")
                with col4:
                    st.metric("Coverage Improvement", 
                             f"{coverage_report['improvement_count']:,}",
                             f"+{coverage_report['coverage_improvement_pct']}%")
                
                # State improvement details
                if not coverage_report['state_improvements'].empty:
                    st.subheader("States with Biggest Improvements")
                    top_improvements = coverage_report['state_improvements'].head(10)
                    
                    fig = px.bar(
                        top_improvements, 
                        x='state', 
                        y='improvement',
                        title="Number of Providers with Enhanced County Data by State",
                        color='improvement',
                        color_continuous_scale='viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show table
                    st.dataframe(
                        top_improvements[['state', 'total_providers', 'orig_county', 'enhanced_county', 'improvement']],
                        column_config={
                            'state': 'State',
                            'total_providers': 'Total Providers',
                            'orig_county': 'Original County Data',
                            'enhanced_county': 'Enhanced County Data',
                            'improvement': 'New County Records'
                        }
                    )
            except Exception as e:
                st.error(f"Error generating coverage report: {e}")
        
        # Enhanced county summary
        with st.expander("🏘️ Enhanced County Summary", expanded=True):
            try:
                county_summary = st.session_state.analytics.get_enhanced_county_summary()
                
                if not county_summary.empty:
                    st.subheader(f"County Analysis ({len(county_summary)} counties)")
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Counties", len(county_summary))
                    with col2:
                        st.metric("Total Providers", county_summary['unique_providers'].sum())
                    with col3:
                        st.metric("Avg Providers per County", round(county_summary['unique_providers'].mean(), 1))
                    
                    # County scatter plot with enhanced data
                    # Clean data to handle NaN values for the scatter plot
                    plot_data = county_summary.copy()
                    plot_data['total_estimated_patients'] = plot_data['total_estimated_patients'].fillna(0)
                    plot_data['avg_quality_score'] = plot_data['avg_quality_score'].fillna(0)
                    
                    # Filter out counties with no data for better visualization
                    plot_data = plot_data[
                        (plot_data['unique_providers'] > 0) & 
                        (plot_data['total_estimated_patients'] >= 0) &
                        (plot_data['avg_quality_score'] > 0)
                    ]
                    
                    fig = px.scatter(
                        plot_data,
                        x='unique_providers',
                        y='avg_quality_score',
                        size='total_estimated_patients',
                        color='state',
                        hover_data=['county_name', 'enhanced_county_count', 'original_county_count'],
                        title="County Provider Count vs Quality Score (Enhanced Data)",
                        labels={
                            'unique_providers': 'Number of Unique Providers',
                            'avg_quality_score': 'Average Quality Score'
                        },
                        size_max=20  # Limit maximum bubble size for better readability
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Top counties table
                    st.subheader("Top Counties by Provider Count")
                    top_counties = county_summary.head(20)
                    st.dataframe(
                        top_counties[['county_name', 'state', 'unique_providers', 'avg_quality_score', 
                                    'total_estimated_patients', 'enhanced_county_count', 'original_county_count']],
                        column_config={
                            'county_name': 'County',
                            'state': 'State',
                            'unique_providers': 'Providers',
                            'avg_quality_score': 'Avg Quality',
                            'total_estimated_patients': 'Est. Patients',
                            'enhanced_county_count': 'Enhanced Records',
                            'original_county_count': 'Original Records'
                        }
                    )
            except Exception as e:
                st.error(f"Error generating county summary: {e}")
        
        # Geographic radius search
        with st.expander("📍 Geographic Radius Search", expanded=True):
            st.subheader("Find Providers Within Distance")
            st.markdown("*Use latitude/longitude coordinates to find providers within a radius*")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                center_lat = st.number_input("Latitude", value=40.7128, format="%.4f", help="Example: 40.7128 (NYC)")
            with col2:
                center_lng = st.number_input("Longitude", value=-74.0060, format="%.4f", help="Example: -74.0060 (NYC)")
            with col3:
                radius = st.number_input("Radius (miles)", value=25, min_value=1, max_value=500)
            
            if st.button("🔍 Search by Geographic Radius"):
                try:
                    radius_results = st.session_state.analytics.get_geographic_analysis(center_lat, center_lng, radius)
                    
                    if not radius_results.empty:
                        st.success(f"Found {len(radius_results)} providers within {radius} miles")
                        
                        # Show results on map
                        fig = px.scatter_mapbox(
                            radius_results,
                            lat="x_latitude",
                            lon="x_longitude",
                            hover_data=["provider_name", "city", "state", "distance_miles"],
                            color="composite_quality_score",
                            size="estimated_total_patients",
                            color_continuous_scale="viridis",
                            size_max=15,
                            zoom=8,
                            title=f"Providers within {radius} miles"
                        )
                        fig.update_layout(mapbox_style="open-street-map")
                        fig.update_layout(height=600)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Results table
                        display_cols = ['provider_name', 'city', 'state', 'x_county', 'distance_miles', 
                                      'composite_quality_score', 'estimated_total_patients']
                        available_cols = [col for col in display_cols if col in radius_results.columns]
                        
                        st.dataframe(
                            radius_results[available_cols].round(2),
                            column_config={
                                'provider_name': 'Provider Name',
                                'city': 'City',
                                'state': 'State', 
                                'x_county': 'County',
                                'distance_miles': 'Distance (mi)',
                                'composite_quality_score': 'Quality Score',
                                'estimated_total_patients': 'Est. Patients'
                            }
                        )
                    else:
                        st.warning(f"No providers found within {radius} miles of the specified location")
                except Exception as e:
                    st.error(f"Error performing geographic search: {e}")

# Page: Metro Area Analysis
if page == "🏙️ Metro Area Analysis":
    st.header("🏙️ Metropolitan Area (CBSA) Analysis")
    st.markdown("Analyze home health provider markets by Core Based Statistical Areas (Metropolitan/Micropolitan Areas)")
    
    # CBSA Summary
    with st.expander("📊 All Metro Areas Summary", expanded=True):
        try:
            cbsa_summary = st.session_state.analytics.get_cbsa_summary()
            
            if not cbsa_summary.empty:
                st.subheader(f"Metro Area Overview ({len(cbsa_summary)} areas)")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Metro Areas", len(cbsa_summary))
                with col2:
                    st.metric("Total Providers", cbsa_summary['unique_providers'].sum())
                with col3:
                    st.metric("Total Counties", cbsa_summary['unique_counties'].sum())
                with col4:
                    st.metric("Total Patients", f"{cbsa_summary['total_estimated_patients'].sum():,}")
                
                # CBSA comparison chart
                # Clean data to handle NaN values
                cbsa_plot_data = cbsa_summary.copy()
                cbsa_plot_data['total_estimated_patients'] = cbsa_plot_data['total_estimated_patients'].fillna(0)
                cbsa_plot_data['avg_quality_score'] = cbsa_plot_data['avg_quality_score'].fillna(0)
                cbsa_plot_data['unique_providers'] = cbsa_plot_data['unique_providers'].fillna(1)
                
                fig = px.scatter(
                    cbsa_plot_data,
                    x='unique_providers',
                    y='avg_quality_score',
                    size='total_estimated_patients',
                    color='metro_type',
                    hover_data=['cbsa_name', 'unique_counties'],
                    title="Metro Area Provider Count vs Quality Score",
                    labels={
                        'unique_providers': 'Number of Providers',
                        'avg_quality_score': 'Average Quality Score'
                    },
                    size_max=25
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top metro areas table
                st.subheader("Top Metro Areas by Provider Count")
                top_cbsas = cbsa_summary.head(15)
                st.dataframe(
                    top_cbsas[['cbsa_name', 'unique_providers', 'unique_counties', 'avg_quality_score', 
                              'total_estimated_patients', 'high_quality_count']],
                    column_config={
                        'cbsa_name': 'Metro Area',
                        'unique_providers': 'Providers',
                        'unique_counties': 'Counties',
                        'avg_quality_score': 'Avg Quality',
                        'total_estimated_patients': 'Est. Patients',
                        'high_quality_count': 'High Quality'
                    }
                )
        except Exception as e:
            st.error(f"Error loading CBSA summary: {e}")
    
    # Individual CBSA Analysis
    with st.expander("🔍 Individual Metro Area Analysis", expanded=True):
        st.subheader("Select a Metro Area for Detailed Analysis")
        
        # Get list of CBSAs
        try:
            cbsa_summary = st.session_state.analytics.get_cbsa_summary()
            if not cbsa_summary.empty:
                cbsa_names = sorted(cbsa_summary['cbsa_name'].unique())
                selected_cbsa = st.selectbox("Choose Metro Area:", cbsa_names)
                
                if st.button("🔍 Analyze Metro Area"):
                    try:
                        cbsa_analysis = st.session_state.analytics.get_cbsa_analysis(selected_cbsa)
                        
                        if 'error' not in cbsa_analysis:
                            st.success(f"Analysis for {cbsa_analysis['cbsa_name']}")
                            
                            # Key metrics
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("Total Providers", cbsa_analysis['total_providers'])
                            with col2:
                                st.metric("Unique CCNs", cbsa_analysis['unique_ccns'])
                            with col3:
                                st.metric("Counties", cbsa_analysis['unique_counties'])
                            with col4:
                                st.metric("High Quality %", f"{cbsa_analysis['high_quality_percentage']}%")
                            with col5:
                                st.metric("Avg Quality", cbsa_analysis['avg_quality_score'])
                            
                            # Additional metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Patients", f"{cbsa_analysis['total_estimated_patients']:,}")
                            with col2:
                                st.metric("Market Concentration", cbsa_analysis['market_concentration_index'])
                            with col3:
                                geographic_spread = cbsa_analysis['geographic_lat_range'] + cbsa_analysis['geographic_lng_range']
                                st.metric("Geographic Spread", f"{geographic_spread:.3f}°")
                            
                            # Top providers in the CBSA
                            st.subheader("Top Providers in Metro Area")
                            top_providers = cbsa_analysis['top_providers']
                            st.dataframe(
                                top_providers,
                                column_config={
                                    'ccn': 'CCN',
                                    'provider_name': 'Provider Name',
                                    'city': 'City',
                                    'x_county': 'County',
                                    'composite_quality_score': 'Quality Score',
                                    'estimated_total_patients': 'Est. Patients'
                                }
                            )
                            
                            # Provider distribution by county
                            all_providers = cbsa_analysis['all_providers']
                            if 'x_county' in all_providers.columns:
                                county_dist = all_providers.groupby('x_county').agg({
                                    'ccn': 'nunique',
                                    'composite_quality_score': 'mean',
                                    'estimated_total_patients': 'sum'
                                }).reset_index()
                                county_dist.columns = ['County', 'Providers', 'Avg_Quality', 'Total_Patients']
                                
                                st.subheader("Provider Distribution by County")
                                fig = px.bar(
                                    county_dist.head(10),
                                    x='County',
                                    y='Providers',
                                    color='Avg_Quality',
                                    title=f"Provider Count by County in {selected_cbsa}",
                                    color_continuous_scale='viridis'
                                )
                                fig.update_xaxis(tickangle=45)
                                st.plotly_chart(fig, use_container_width=True)
                                
                                st.dataframe(county_dist, use_container_width=True)
                        else:
                            st.error(cbsa_analysis['error'])
                    except Exception as e:
                        st.error(f"Error analyzing CBSA: {e}")
        except Exception as e:
            st.error(f"Error loading CBSA list: {e}")

# Page: Rural Health Analysis
if page == "🌾 Rural Health Analysis":
    st.header("🌾 Rural Health Analysis")
    st.markdown("Analyze home health providers by rural-urban classifications and population density")
    
    # Rural-Urban Overview
    with st.expander("📊 Rural-Urban Overview", expanded=True):
        try:
            rural_analysis = st.session_state.analytics.get_rural_urban_analysis()
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            if rural_analysis['frontier_stats']['total_providers'] > 0:
                with col1:
                    st.metric("Frontier Providers", rural_analysis['frontier_stats']['total_providers'])
                with col2:
                    st.metric("Frontier CCNs", rural_analysis['frontier_stats']['unique_ccns'])
                with col3:
                    st.metric("Frontier Avg Quality", rural_analysis['frontier_stats']['avg_quality'])
                with col4:
                    st.metric("Frontier Patients", f"{rural_analysis['frontier_stats']['total_patients']:,}")
            
            # Rural vs Urban comparison
            if rural_analysis['rural_urban_comparison']:
                st.subheader("Rural vs Urban Provider Comparison")
                
                rural_urban_df = pd.DataFrame(rural_analysis['rural_urban_comparison'], 
                                            columns=['Area Type', 'Provider Count', 'Unique CCNs', 'Avg Quality', 
                                                   'Total Patients', 'High Quality Count', 'High Quality %'])
                
                # Display metrics
                col1, col2 = st.columns(2)
                for i, row in rural_urban_df.iterrows():
                    with col1 if i == 0 else col2:
                        st.metric(f"{row['Area Type']} Providers", f"{row['Provider Count']:,}")
                        st.metric(f"{row['Area Type']} Avg Quality", f"{row['Avg Quality']:.2f}")
                        st.metric(f"{row['Area Type']} High Quality %", f"{row['High Quality %']}%")
                
                # Comparison chart
                fig = px.bar(
                    rural_urban_df,
                    x='Area Type',
                    y='Provider Count',
                    color='Avg Quality',
                    title="Rural vs Urban Provider Distribution",
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(rural_urban_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading rural-urban analysis: {e}")
    
    # RUCC Distribution Analysis
    with st.expander("🏘️ Rural-Urban Continuum Codes (RUCC) Analysis", expanded=True):
        try:
            rural_analysis = st.session_state.analytics.get_rural_urban_analysis()
            rucc_distribution = rural_analysis['rucc_distribution']
            
            if not rucc_distribution.empty:
                st.subheader("USDA Rural-Urban Continuum Code Distribution")
                
                # RUCC explanation
                st.info("""
                **RUCC Categories:**
                - **Metropolitan**: Counties in metro areas
                - **Nonmetropolitan**: Counties outside metro areas (rural)
                
                **Subcategories** range from Large Metro (most urban) to Rural Non-adjacent (most rural)
                """)
                
                # RUCC distribution chart
                fig = px.sunburst(
                    rucc_distribution,
                    path=['x_rucc_category', 'x_rucc_subcategory'],
                    values='provider_count',
                    title="Provider Distribution by RUCC Categories"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # RUCC table
                st.subheader("RUCC Distribution Details")
                rucc_display = rucc_distribution.copy()
                rucc_display['high_quality_pct'] = round(
                    rucc_display['high_quality_count'] / rucc_display['provider_count'] * 100, 1
                )
                
                st.dataframe(
                    rucc_display[['x_rucc_category', 'x_rucc_subcategory', 'provider_count', 
                                'unique_ccns', 'avg_quality', 'total_patients', 'high_quality_pct']],
                    column_config={
                        'x_rucc_category': 'RUCC Category',
                        'x_rucc_subcategory': 'RUCC Subcategory',
                        'provider_count': 'Providers',
                        'unique_ccns': 'Unique CCNs',
                        'avg_quality': 'Avg Quality',
                        'total_patients': 'Total Patients',
                        'high_quality_pct': 'High Quality %'
                    }
                )
        except Exception as e:
            st.error(f"Error loading RUCC analysis: {e}")
    
    # Population Density Analysis
    with st.expander("🏙️ Population Density Analysis", expanded=True):
        try:
            density_analysis = st.session_state.analytics.get_density_category_analysis()
            
            if not density_analysis.empty:
                st.subheader("Provider Distribution by Population Density")
                
                # Density categories explanation
                st.info("""
                **Density Categories:**
                - **High Density**: >10,000 people per sq mile (Urban core)
                - **Medium Density**: 1,000-10,000 people per sq mile (Urban/Suburban)
                - **Low Density**: 100-1,000 people per sq mile (Suburban/Small town)
                - **Rural**: <100 people per sq mile (Rural areas)
                """)
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                for i, row in density_analysis.iterrows():
                    with [col1, col2, col3, col4][i % 4]:
                        st.metric(
                            f"{row['density_category'].replace('_', ' ').title()}",
                            f"{row['provider_count']:,}",
                            f"Avg Quality: {row['avg_quality_score']:.2f}"
                        )
                
                # Density distribution chart
                fig = px.bar(
                    density_analysis,
                    x='density_category',
                    y='provider_count',
                    color='avg_quality_score',
                    title="Provider Count by Population Density Category",
                    color_continuous_scale='viridis',
                    labels={'density_category': 'Density Category', 'provider_count': 'Number of Providers'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed density table
                st.dataframe(
                    density_analysis,
                    column_config={
                        'density_category': 'Density Category',
                        'provider_count': 'Providers',
                        'unique_ccns': 'Unique CCNs',
                        'states_covered': 'States',
                        'avg_quality_score': 'Avg Quality',
                        'total_estimated_patients': 'Total Patients',
                        'high_quality_percentage': 'High Quality %'
                    }
                )
        except Exception as e:
            st.error(f"Error loading density analysis: {e}")
    
    # State Rural-Urban Summary
    with st.expander("🗺️ State Rural-Urban Summary", expanded=True):
        try:
            state_rural_summary = st.session_state.analytics.get_state_rural_urban_summary()
            
            if not state_rural_summary.empty:
                st.subheader("Rural vs Urban Providers by State")
                
                # Top rural states
                top_rural_states = state_rural_summary.head(15)
                
                # Clean data to handle NaN values
                rural_plot_data = top_rural_states.copy()
                rural_plot_data['rural_providers'] = rural_plot_data['rural_providers'].fillna(1)
                rural_plot_data['rural_percentage'] = rural_plot_data['rural_percentage'].fillna(0)
                rural_plot_data['rural_avg_quality'] = rural_plot_data['rural_avg_quality'].fillna(0)
                rural_plot_data['total_providers'] = rural_plot_data['total_providers'].fillna(1)
                
                fig = px.scatter(
                    rural_plot_data,
                    x='total_providers',
                    y='rural_percentage',
                    size='rural_providers',
                    color='rural_avg_quality',
                    hover_data=['state', 'frontier_providers'],
                    title="State Rural Provider Analysis",
                    labels={
                        'total_providers': 'Total Providers',
                        'rural_percentage': 'Rural Percentage (%)',
                        'rural_avg_quality': 'Rural Avg Quality'
                    },
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # State summary table
                st.dataframe(
                    state_rural_summary,
                    column_config={
                        'state': 'State',
                        'total_providers': 'Total Providers',
                        'rural_providers': 'Rural Providers',
                        'urban_providers': 'Urban Providers',
                        'frontier_providers': 'Frontier Providers',
                        'rural_percentage': 'Rural %',
                        'rural_avg_quality': 'Rural Avg Quality',
                        'urban_avg_quality': 'Urban Avg Quality',
                        'unique_cbsas': 'CBSAs',
                        'unique_counties': 'Counties'
                    }
                )
        except Exception as e:
            st.error(f"Error loading state rural summary: {e}")
    
    # Rural Provider Search
    with st.expander("🔍 Rural Provider Search", expanded=True):
        st.subheader("Find Rural Providers")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            rural_state = st.selectbox("Select State for Rural Search", ["All"] + get_states())
        with col2:
            rucc_category = st.selectbox("RUCC Category", ["All", "Metropolitan", "Nonmetropolitan"])
        with col3:
            frontier_only = st.checkbox("Frontier Areas Only", help="Most rural areas with <6 people per sq mile")
        
        if st.button("🔍 Search Rural Providers"):
            try:
                search_params = {}
                if rural_state != "All":
                    search_params['state'] = rural_state
                if rucc_category != "All":
                    search_params['rucc_category'] = rucc_category
                if frontier_only:
                    search_params['is_frontier'] = True
                
                rural_providers = st.session_state.analytics.find_rural_providers(**search_params)
                
                if not rural_providers.empty:
                    st.success(f"Found {len(rural_providers)} rural providers")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Providers Found", len(rural_providers))
                    with col2:
                        st.metric("Unique CCNs", rural_providers['ccn'].nunique())
                    with col3:
                        st.metric("Avg Quality", f"{rural_providers['composite_quality_score'].mean():.2f}")
                    with col4:
                        st.metric("States", rural_providers['state'].nunique())
                    
                    # Results table
                    display_cols = ['ccn', 'provider_name', 'city', 'x_county', 'state', 'x_rucc_subcategory', 
                                  'x_density_category', 'composite_quality_score', 'estimated_total_patients']
                    available_cols = [col for col in display_cols if col in rural_providers.columns]
                    
                    st.dataframe(
                        rural_providers[available_cols],
                        column_config={
                            'ccn': 'CCN',
                            'provider_name': 'Provider Name',
                            'city': 'City',
                            'x_county': 'County',
                            'state': 'State',
                            'x_rucc_subcategory': 'RUCC Type',
                            'x_density_category': 'Density',
                            'composite_quality_score': 'Quality Score',
                            'estimated_total_patients': 'Est. Patients'
                        }
                    )
                else:
                    st.warning("No rural providers found with the specified criteria")
            except Exception as e:
                st.error(f"Error searching rural providers: {e}")

# Footer
st.markdown("---")
st.markdown("🏥 **CMS Home Health Data Explorer** | Built with Streamlit and SQLite")
