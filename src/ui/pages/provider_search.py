"""
Provider Search page for the CMS Home Health Data Explorer.
Allows users to search for providers by various criteria.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.ui.components import (
    render_geographic_filters,
    render_download_button,
    render_metrics_cards,
    render_data_quality_warning
)


def show():
    """Render the Provider Search page."""
    st.header("Find Home Health Providers")
    
    # Search filters
    st.subheader("Search Filters")
    
    # Use the standardized geographic filters component
    filters = render_geographic_filters(
        key_prefix="provider_search",
        include_cbsa=True,
        include_quality_filters=True
    )
    
    # Search button
    if st.button("Search Providers", type="primary"):
        
        # Build search parameters
        search_params = {}
        if filters.get('state') and filters['state'] != "All":
            search_params['state'] = filters['state']
        if filters.get('city') and filters['city'] != "All":
            search_params['city'] = filters['city']
        if filters.get('zip_code'):
            search_params['zip_code'] = filters['zip_code']
        if filters.get('provider_name'):
            search_params['provider_name'] = filters['provider_name']
        if filters.get('ccn'):
            search_params['ccn'] = filters['ccn']
        
        # Get results
        try:
            # Handle CBSA search separately if provided
            if filters.get('cbsa'):
                results = st.session_state.analytics.find_providers_by_cbsa(cbsa_name=filters['cbsa'])
                
                # Apply additional filters to CBSA results
                if filters.get('state') and filters['state'] != "All":
                    results = results[results['state'] == filters['state']]
                if filters.get('city') and filters['city'] != "All":
                    results = results[results['city'].str.contains(filters['city'], case=False, na=False)]
                if filters.get('zip_code'):
                    results = results[results['zip_code'].str.contains(filters['zip_code'], na=False)]
                if filters.get('provider_name'):
                    results = results[results['provider_name'].str.contains(filters['provider_name'], case=False, na=False)]
                if filters.get('ccn'):
                    results = results[results['ccn'].str.contains(filters['ccn'], case=False, na=False)]
                if filters.get('high_quality_only'):
                    results = results[results['is_high_quality'] == 1]
                
                # Apply rural/urban filters
                rural_filter = filters.get('rural_filter', 'All')
                if rural_filter == "Rural Only":
                    results = results[results['x_is_rural'] == 1]
                elif rural_filter == "Urban Only":
                    results = results[results['x_is_rural'] == 0]
                elif rural_filter == "Frontier Only":
                    results = results[results['x_is_frontier'] == 1]
                    
            elif search_params or filters.get('high_quality_only') or filters.get('rural_filter', 'All') != "All":
                results = st.session_state.analytics.find_providers_by_location(
                    **search_params,
                    high_quality_only=filters.get('high_quality_only', False)
                )
            else:
                results = st.session_state.analytics.search_providers_by_criteria(
                    min_quality_score=filters.get('min_quality', 1.0)
                )
                
            # Filter by minimum quality
            min_quality = filters.get('min_quality', 1.0)
            if min_quality > 1.0:
                results = results[results['composite_quality_score'] >= min_quality]
            
            # Apply rural/urban filters if not already applied in CBSA search
            rural_filter = filters.get('rural_filter', 'All')
            if not filters.get('cbsa') and rural_filter != "All":
                if rural_filter == "Rural Only":
                    results = results[results['x_is_rural'] == 1]
                elif rural_filter == "Urban Only":
                    results = results[results['x_is_rural'] == 0]
                elif rural_filter == "Frontier Only":
                    results = results[results['x_is_frontier'] == 1]
            
            # Display results
            _display_search_results(results)
                        
        except Exception as e:
            st.error(f"Search error: {str(e)}")


def _display_search_results(results):
    """Display the search results with analytics."""
    
    # Check for data quality issues
    if render_data_quality_warning(results):
        return
    
    # Calculate summary statistics
    total_patients = results['estimated_total_patients'].fillna(0).sum()
    unique_ccns = results['ccn'].nunique()
    unique_providers = results['provider_name'].nunique()
    unique_states = results['state'].nunique()
    
    # Display summary metrics
    metrics = {
        "Unique CCNs": unique_ccns,
        "Unique Providers": unique_providers,
        "Total Est. Patient Volume": int(total_patients),
        "States Covered": unique_states
    }
    render_metrics_cards(metrics, columns=4)
    
    # Display results table
    _display_results_table(results)
    
    # Comprehensive analytics section
    st.subheader("📊 Search Results Analytics")
    
    # State-level analysis
    if unique_states > 1:
        _display_state_analysis(results)
    
    # County-level analysis
    _display_county_analysis(results)
    
    # Volume and quality distribution summary
    _display_distribution_summary(results)
    
    # Download button
    render_download_button(
        results,
        "provider_search_results",
        "📥 Download Search Results",
        "Download the search results as a CSV file"
    )


def _display_results_table(results):
    """Display the results table with proper formatting."""
    
    # Define display columns
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


def _display_state_analysis(results):
    """Display state-level analysis."""
    st.subheader("🗺️ State-Level Analysis")
    
    # Group by state for analysis
    state_analysis = results.groupby('state').agg({
        'ccn': 'nunique',
        'provider_name': 'nunique',
        'county': 'nunique',
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


def _display_county_analysis(results):
    """Display county-level analysis."""
    county_col = 'x_county' if 'x_county' in results.columns else 'county'
    if county_col not in results.columns or results[county_col].nunique() <= 1:
        return
        
    st.subheader("🏘️ Enhanced County-Level Analysis")
    st.info(f"Using {county_col} data ({results[county_col].nunique()} counties)")
    
    # Group by county and state for analysis
    county_analysis = results.groupby([county_col, 'state']).agg({
        'ccn': 'nunique',
        'provider_name': 'nunique',
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


def _display_distribution_summary(results):
    """Display volume and quality distribution summary."""
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
