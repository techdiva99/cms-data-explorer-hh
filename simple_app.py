"""
Simple CMS Home Health Data Explorer - Working Version
"""

import streamlit as st
import sqlite3
import pandas as pd
import sys
import os

# Add src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import analytics
from analytics.base import CMSAnalytics

# Page configuration
st.set_page_config(
    page_title="CMS Home Health Data Explorer",
    page_icon="🏥",
    layout="wide"
)

# Initialize analytics
@st.cache_resource
def get_analytics():
    return CMSAnalytics()

analytics = get_analytics()

# App title
st.title("🏥 CMS Home Health Data Explorer")
st.markdown("**Explore home health care providers across the United States**")

# Sidebar
st.sidebar.title("Search & Filter")

# State filter
states_query = "SELECT DISTINCT state FROM providers ORDER BY state"
conn = analytics._get_connection()
states_df = pd.read_sql_query(states_query, conn)
states = ['All'] + states_df['state'].tolist()
selected_state = st.sidebar.selectbox("Select State:", states)

# Provider search
provider_name = st.sidebar.text_input("Provider Name (partial match):")

# Quality filter
quality_filter = st.sidebar.checkbox("High Quality Providers Only")

# Main content
st.header("Provider Search Results")

# Build query
query = "SELECT * FROM providers WHERE 1=1"
params = []

if selected_state != 'All':
    query += " AND state = ?"
    params.append(selected_state)

if provider_name:
    query += " AND provider_name LIKE ?"
    params.append(f"%{provider_name}%")

if quality_filter:
    query += " AND is_high_quality = 1"

query += " LIMIT 100"

# Execute query and display results
try:
    df = pd.read_sql_query(query, conn, params=params)
    
    if df.empty:
        st.warning("No providers found matching your criteria.")
    else:
        st.success(f"Found {len(df)} providers")
        
        # Display results
        st.dataframe(
            df[['provider_name', 'city', 'state', 'zip_code', 'is_high_quality', 'composite_quality_score']],
            use_container_width=True
        )
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Providers", len(df))
        
        with col2:
            high_quality = df['is_high_quality'].sum() if 'is_high_quality' in df.columns else 0
            st.metric("High Quality", high_quality)
        
        with col3:
            avg_score = df['composite_quality_score'].mean() if 'composite_quality_score' in df.columns else 0
            st.metric("Avg Quality Score", f"{avg_score:.2f}")

except Exception as e:
    st.error(f"Error querying database: {e}")
finally:
    conn.close()

# Footer
st.markdown("---")
st.markdown("**Data Source:** CMS Home Health Compare")
