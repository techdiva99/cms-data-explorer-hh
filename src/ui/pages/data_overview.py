"""
Data Overview page for the CMS Home Health Data Explorer.
Provides overview of the data and database schema.
"""

import streamlit as st
from src.ui.components import render_data_quality_warning


def show():
    """Render the Data Overview page."""
    st.header("📈 Data Overview")
    st.info("🚧 This page is being refactored into the new modular structure. Functionality will be restored shortly.")
    
    # TODO: Implement data overview functionality
    # This page should include:
    # - Database schema overview
    # - Data freshness and update information
    # - Coverage statistics
    # - Data quality metrics
