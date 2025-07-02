"""
Market Analysis page for the CMS Home Health Data Explorer.
Provides market analysis by location including provider distribution and quality metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.ui.components import (
    get_states,
    get_cities_by_state,
    render_metrics_cards,
    render_data_quality_warning,
    render_download_button
)


def show():
    """Render the Market Analysis page."""
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
            
            _display_market_analysis(market_data, analysis_city, analysis_state)
                
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")


def _display_market_analysis(market_data, city, state):
    """Display market analysis results."""
    
    # Display key metrics
    high_quality_percentage = market_data.get('high_quality_percentage', 0)
    avg_quality = market_data.get('average_quality_score')
    
    metrics = {
        "Total Providers": market_data['total_providers'],
        "High Quality Providers": market_data['high_quality_providers'],
        "Quality Rate": f"{high_quality_percentage:.1f}%",
        "Avg Quality Score": f"{avg_quality:.2f}" if avg_quality else "N/A"
    }
    render_metrics_cards(metrics, columns=4)
    
    # Provider analysis
    if market_data['all_providers']:
        providers_df = pd.DataFrame(market_data['all_providers'])
        
        if not render_data_quality_warning(providers_df):
            _display_provider_distribution(providers_df)
            _display_top_providers(market_data)
            
            # Download button
            render_download_button(
                providers_df,
                f"market_analysis_{city}_{state}",
                "📥 Download Market Analysis Data",
                f"Download the market analysis data for {city}, {state}"
            )


def _display_provider_distribution(providers_df):
    """Display provider distribution charts."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quality Score Distribution")
        if 'composite_quality_score' in providers_df.columns:
            # Filter out null quality scores for histogram
            quality_data = providers_df['composite_quality_score'].dropna()
            if len(quality_data) > 0:
                fig = px.histogram(
                    providers_df.dropna(subset=['composite_quality_score']), 
                    x='composite_quality_score',
                    nbins=20,
                    title="Provider Quality Scores",
                    labels={'composite_quality_score': 'Quality Score', 'count': 'Number of Providers'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No quality score data available")
        else:
            st.info("Quality score data not available")
        
    with col2:
        st.subheader("Ownership Type Distribution")
        if 'ownership_type' in providers_df.columns:
            ownership_counts = providers_df['ownership_type'].value_counts()
            if len(ownership_counts) > 0:
                fig = px.pie(
                    values=ownership_counts.values,
                    names=ownership_counts.index,
                    title="Provider Ownership Types"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No ownership type data available")
        else:
            st.info("Ownership type data not available")


def _display_top_providers(market_data):
    """Display top providers table."""
    st.subheader("Top Providers by Patient Volume")
    
    if market_data['top_providers']:
        top_df = pd.DataFrame(market_data['top_providers'])
        
        # Format the dataframe for better display
        if not top_df.empty:
            # Rename columns for better display
            column_mapping = {
                'ccn': 'CCN',
                'provider_name': 'Provider Name',
                'city': 'City',
                'state': 'State',
                'estimated_total_patients': 'Est. Patients',
                'composite_quality_score': 'Quality Score',
                'ownership_type': 'Ownership Type'
            }
            
            # Only include columns that exist
            display_cols = [col for col in column_mapping.keys() if col in top_df.columns]
            display_df = top_df[display_cols].copy()
            display_df.columns = [column_mapping[col] for col in display_cols]
            
            # Format numeric columns
            if 'Quality Score' in display_df.columns:
                display_df['Quality Score'] = display_df['Quality Score'].round(2)
            if 'Est. Patients' in display_df.columns:
                display_df['Est. Patients'] = display_df['Est. Patients'].fillna(0).astype(int)
            
            # Configure column display
            column_config = {}
            if 'Quality Score' in display_df.columns:
                column_config['Quality Score'] = st.column_config.NumberColumn(
                    "Quality Score",
                    format="%.2f"
                )
            if 'Est. Patients' in display_df.columns:
                column_config['Est. Patients'] = st.column_config.NumberColumn(
                    "Est. Patients",
                    format="%d"
                )
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                column_config=column_config,
                hide_index=True
            )
        else:
            st.info("No provider data available")
    else:
        st.info("No top providers data available")
