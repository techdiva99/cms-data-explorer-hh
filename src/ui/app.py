"""
Main Streamlit application entry point.
Handles navigation and page routing for the CMS Home Health Data Explorer.
"""

import streamlit as st
from src.analytics import CMSAnalytics
from src.ui.pages import (
    provider_search,
    metro_area_analysis,
    rural_health_analysis,
    coverage_deserts,
    market_analysis,
    quality_benchmarks,
    provider_comparison,
    data_overview
)

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
    [
        "🔍 Provider Search", 
        "🏙️ Metro Area Analysis", 
        "🌾 Rural Health Analysis", 
        "🏜️ Coverage Deserts", 
        "📊 Market Analysis", 
        "🎯 Quality Benchmarks", 
        "⚖️ Provider Comparison", 
        "📈 Data Overview"
    ]
)

# Page routing
if page == "🔍 Provider Search":
    provider_search.show()
elif page == "🏙️ Metro Area Analysis":
    metro_area_analysis.show()
elif page == "🌾 Rural Health Analysis":
    rural_health_analysis.show()
elif page == "🏜️ Coverage Deserts":
    coverage_deserts.show()
elif page == "📊 Market Analysis":
    market_analysis.show()
elif page == "🎯 Quality Benchmarks":
    quality_benchmarks.show()
elif page == "⚖️ Provider Comparison":
    provider_comparison.show()
elif page == "📈 Data Overview":
    data_overview.show()
