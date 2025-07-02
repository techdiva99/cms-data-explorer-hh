import streamlit as st
import sqlite3
import pandas as pd

st.title("🏥 CMS Home Health Data Explorer - Test")

# Test database connection
try:
    conn = sqlite3.connect('data/processed/cms_homehealth.db')
    count_query = "SELECT COUNT(*) as count FROM providers"
    result = pd.read_sql_query(count_query, conn)
    provider_count = result.iloc[0]['count']
    
    st.success(f"✅ Database connected successfully!")
    st.info(f"Found {provider_count:,} providers in the database")
    
    # Show first 10 providers
    sample_query = "SELECT provider_name, city, state, zip_code FROM providers LIMIT 10"
    sample_df = pd.read_sql_query(sample_query, conn)
    
    st.subheader("Sample Providers:")
    st.dataframe(sample_df)
    
    conn.close()
    
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")

st.markdown("---")
st.markdown("If you see this page, Streamlit is working correctly!")
