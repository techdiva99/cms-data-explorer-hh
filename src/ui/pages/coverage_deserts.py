"""
Coverage Deserts Analysis page for the CMS Home Health Data Explorer.
Identifies underserved areas and market opportunities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from src.ui.components import (
    get_states,
    render_download_button,
    render_metrics_cards,
    render_data_quality_warning
)


def show():
    """Render the Coverage Deserts Analysis page."""
    st.header("🏜️ Coverage Deserts Analysis")
    st.markdown("""
    **Identify underserved areas with limited home health provider coverage.**  
    Discover market opportunities by analyzing ZIP codes with few or no providers within a reasonable distance.
    """)
    
    # Coverage Desert Discovery
    with st.expander("🔍 Discover Coverage Deserts", expanded=True):
        _render_desert_discovery()
    
    # Market Potential Calculator
    with st.expander("💰 Market Potential Calculator", expanded=False):
        _render_market_potential_calculator()
    
    # Provider Expansion Analysis
    with st.expander("🚀 Provider Expansion Analysis", expanded=False):
        _render_expansion_analysis()


def _render_desert_discovery():
    """Render the coverage desert discovery section."""
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
            
            _display_desert_results(desert_results, radius_miles, min_medicare_pop)
                
        except Exception as e:
            st.error(f"Error analyzing coverage deserts: {str(e)}")


def _display_desert_results(desert_results, radius_miles, min_medicare_pop):
    """Display coverage desert analysis results."""
    
    if render_data_quality_warning(desert_results):
        st.info("🎉 No significant coverage deserts found with the current criteria. Try adjusting your search parameters.")
        return
    
    # Summary metrics
    total_medicare = desert_results['medicare_enrolled'].sum()
    avg_opportunity = desert_results['market_opportunity_score'].mean()
    states_affected = desert_results['state'].nunique()
    
    metrics = {
        "Underserved ZIP Codes": len(desert_results),
        "Total Medicare Population": int(total_medicare),
        "Avg Opportunity Score": f"{avg_opportunity:.1f}",
        "States Affected": states_affected
    }
    render_metrics_cards(metrics, columns=4)
    
    # Interactive Map
    st.subheader("🗺️ Coverage Desert Map")
    _create_desert_map(desert_results, radius_miles)
    
    # Desert severity breakdown
    st.subheader("📊 Desert Severity Analysis")
    _display_severity_analysis(desert_results)
    
    # Top opportunities table
    st.subheader("🎯 Top Market Opportunities")
    _display_opportunities_table(desert_results)
    
    # Export functionality
    st.subheader("📥 Export Results")
    render_download_button(
        desert_results,
        f"coverage_deserts_{radius_miles}mi_{min_medicare_pop}pop",
        "📄 Download Coverage Desert Data (CSV)"
    )


def _create_desert_map(desert_results, radius_miles):
    """Create the coverage desert map visualization."""
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


def _display_severity_analysis(desert_results):
    """Display desert severity analysis charts and table."""
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


def _display_opportunities_table(desert_results):
    """Display the top market opportunities table."""
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


def _render_market_potential_calculator():
    """Render the market potential calculator section."""
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
                        _display_market_potential_results(market_potential)
                    else:
                        st.error(market_potential['error'])
                except Exception as e:
                    st.error(f"Error calculating market potential: {str(e)}")
            else:
                st.warning("Please enter valid 5-digit ZIP codes.")
        else:
            st.warning("Please enter at least one ZIP code.")


def _display_market_potential_results(market_potential):
    """Display market potential calculation results."""
    # Display market summary
    summary = market_potential['market_summary']
    
    # Basic metrics
    basic_metrics = {
        "ZIP Codes": summary['total_zip_codes'],
        "Total Population": summary['total_population'],
        "Medicare Eligible": summary['total_medicare_eligibles'],
        "Medicare Enrolled": summary['total_medicare_enrolled']
    }
    render_metrics_cards(basic_metrics, columns=4)
    
    # Geographic metrics  
    geo_metrics = {
        "States": summary['states_covered'],
        "Counties": summary['counties_covered'],
        "Rural ZIPs": summary['rural_zip_count'],
        "Frontier ZIPs": summary['frontier_zip_count']
    }
    render_metrics_cards(geo_metrics, columns=4)
    
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


def _render_expansion_analysis():
    """Render the provider expansion analysis section."""
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
                    _display_expansion_results(expansion_analysis)
                else:
                    st.error(expansion_analysis['error'])
                    
            except Exception as e:
                st.error(f"Error analyzing expansion opportunities: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading providers: {str(e)}")


def _display_expansion_results(expansion_analysis):
    """Display provider expansion analysis results."""
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
