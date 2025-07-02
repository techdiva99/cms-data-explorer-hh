"""
Main entry point for the CMS Home Health Data Explorer.
Uses the new modular UI structure.
"""

import sys
import os

# Add src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import and run the main UI application
import streamlit as st
from analytics.base import CMSAnalytics
from ui.pages import (
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

# App title and description
st.title("🏥 CMS Home Health Data Explorer")
st.markdown("""
Explore home health care providers, quality metrics, and market analysis 
across the United States using CMS data.
""")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page:",
    [
        "Data Overview",
        "Provider Search", 
        "Metro Area Analysis",
        "Rural Health Analysis",
        "Coverage Deserts",
        "Market Analysis",
        "Quality Benchmarks",
        "Provider Comparison"
    ]
)

# Route to appropriate page
if page == "Data Overview":
    data_overview.show_page()
elif page == "Provider Search":
    provider_search.show_page()
elif page == "Metro Area Analysis":
    metro_area_analysis.show_page()
elif page == "Rural Health Analysis":
    rural_health_analysis.show_page() 
elif page == "Coverage Deserts":
    coverage_deserts.show_page()
elif page == "Market Analysis":
    market_analysis.show_page()
elif page == "Quality Benchmarks":
    quality_benchmarks.show_page()
elif page == "Provider Comparison":
    provider_comparison.show_page()
