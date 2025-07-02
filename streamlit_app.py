import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analytics import CMSAnalytics
from vector_database import CMSVectorDatabase
import json

# Optional imports for mapping functionality
try:
    import folium
    from streamlit_folium import st_folium
    MAPPING_AVAILABLE = True
except ImportError:
    MAPPING_AVAILABLE = False
    st.warning("⚠️ Mapping functionality not available. Install folium and streamlit-folium for maps.")

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
    
if 'vector_db' not in st.session_state:
    try:
        st.session_state.vector_db = CMSVectorDatabase()
        VECTOR_DB_AVAILABLE = True
    except ImportError:
        st.session_state.vector_db = None
        VECTOR_DB_AVAILABLE = False

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
    ["🔍 Provider Search", "📊 Market Analysis", "🎯 Quality Benchmarks", "🤖 AI Assistant", "📈 Data Overview"]
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
    col1, col2, col3 = st.columns(3)
    
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
    
    # Quality filters
    col1, col2 = st.columns(2)
    with col1:
        high_quality_only = st.checkbox("High Quality Providers Only")
        
    with col2:
        min_quality = st.slider("Minimum Quality Score", 1.0, 5.0, 1.0, 0.5)
    
    # Service filters
    st.subheader("Services Offered")
    service_cols = st.columns(3)
    
    services = []
    with service_cols[0]:
        if st.checkbox("Nursing Care"):
            services.append("nursing")
        if st.checkbox("Physical Therapy"):
            services.append("physical_therapy")
            
    with service_cols[1]:
        if st.checkbox("Occupational Therapy"):
            services.append("occupational_therapy")
        if st.checkbox("Speech Pathology"):
            services.append("speech_pathology")
            
    with service_cols[2]:
        if st.checkbox("Medical Social Services"):
            services.append("medical_social")
        if st.checkbox("Home Health Aide"):
            services.append("home_health_aide")
    
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
        
        # Get results
        try:
            if search_params:
                results = st.session_state.analytics.find_providers_by_location(
                    **search_params,
                    high_quality_only=high_quality_only
                )
            else:
                results = st.session_state.analytics.search_providers_by_criteria(
                    min_quality_score=min_quality,
                    services_offered=services if services else None
                )
                
            # Filter by minimum quality
            if min_quality > 1.0:
                results = results[results['composite_quality_score'] >= min_quality]
            
            st.success(f"Found {len(results)} providers")
            
            if not results.empty:
                # Display results
                display_cols = [
                    'provider_name', 'city', 'state', 'zip_code',
                    'composite_quality_score', 'estimated_total_patients',
                    'ownership_type'
                ]
                
                results_display = results[display_cols].copy()
                results_display.columns = [
                    'Provider Name', 'City', 'State', 'ZIP',
                    'Quality Score', 'Est. Patients', 'Ownership'
                ]
                
                # Format numeric columns
                results_display['Quality Score'] = results_display['Quality Score'].round(2)
                results_display['Est. Patients'] = results_display['Est. Patients'].fillna(0).astype(int)
                
                st.dataframe(results_display, use_container_width=True)
                
                # Show provider details
                if len(results) > 0:
                    st.subheader("Provider Details")
                    selected_idx = st.selectbox(
                        "Select a provider for details:",
                        range(len(results)),
                        format_func=lambda x: results.iloc[x]['provider_name']
                    )
                    
                    selected_provider = results.iloc[selected_idx]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Quality Score", f"{selected_provider['composite_quality_score']:.2f}")
                        st.metric("Estimated Patients", f"{int(selected_provider['estimated_total_patients'] or 0):,}")
                        
                    with col2:
                        st.metric("Survey Response Rate", f"{selected_provider['survey_response_rate']:.1f}%")
                        st.metric("ZIP Codes Served", int(selected_provider['unique_zips_served'] or 0))
                        
                    # Services offered
                    st.subheader("Services Offered")
                    service_cols = st.columns(3)
                    
                    services_offered = []
                    if selected_provider.get('offers_nursing'):
                        services_offered.append("✅ Nursing Care")
                    if selected_provider.get('offers_physical_therapy'):
                        services_offered.append("✅ Physical Therapy")
                    if selected_provider.get('offers_occupational_therapy'):
                        services_offered.append("✅ Occupational Therapy")
                    if selected_provider.get('offers_speech_pathology'):
                        services_offered.append("✅ Speech Pathology")
                    if selected_provider.get('offers_medical_social'):
                        services_offered.append("✅ Medical Social Services")
                    if selected_provider.get('offers_home_health_aide'):
                        services_offered.append("✅ Home Health Aide")
                    
                    for i, service in enumerate(services_offered):
                        with service_cols[i % 3]:
                            st.write(service)
                            
            else:
                st.warning("No providers found matching your criteria.")
                
        except Exception as e:
            st.error(f"Search error: {str(e)}")

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
                    fig = px.histogram(
                        providers_df, 
                        x='composite_quality_score',
                        nbins=20,
                        title="Provider Quality Scores"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                with col2:
                    st.subheader("Ownership Type Distribution")
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
                top_df.columns = ['Provider Name', 'Quality Score', 'Est. Patients', 'Market Share']
                top_df['Quality Score'] = top_df['Quality Score'].round(2)
                top_df['Est. Patients'] = top_df['Est. Patients'].fillna(0).astype(int)
                top_df['Market Share'] = (top_df['Market Share'] * 100).round(2).astype(str) + '%'
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
                
                # Percentile table
                st.subheader("Quality Percentiles")
                percentiles_df = pd.DataFrame([
                    {"Percentile": "10th", "Quality Score": f"{benchmarks['percentiles']['10th']:.2f}"},
                    {"Percentile": "25th", "Quality Score": f"{benchmarks['percentiles']['25th']:.2f}"},
                    {"Percentile": "50th (Median)", "Quality Score": f"{benchmarks['percentiles']['50th']:.2f}"},
                    {"Percentile": "75th", "Quality Score": f"{benchmarks['percentiles']['75th']:.2f}"},
                    {"Percentile": "90th", "Quality Score": f"{benchmarks['percentiles']['90th']:.2f}"},
                    {"Percentile": "95th", "Quality Score": f"{benchmarks['percentiles']['95th']:.2f}"}
                ])
                st.dataframe(percentiles_df, use_container_width=True)
                
            else:
                st.error("No benchmark data available for the selected scope.")
                
        except Exception as e:
            st.error(f"Benchmark error: {str(e)}")

# Page: AI Assistant
elif page == "🤖 AI Assistant":
    st.header("AI-Powered Data Assistant")
    st.markdown("Ask questions about home health providers using natural language.")
    
    # Sample questions
    with st.expander("💡 Sample Questions"):
        st.markdown("""
        - "Find high quality home health providers in Los Angeles"
        - "What are the quality benchmarks for home health agencies?"
        - "Show me providers that offer physical therapy in Texas"
        - "Compare quality scores between nonprofit and for-profit providers"
        - "Which counties have the highest Medicare penetration rates?"
        """)
    
    # Chat interface
    user_question = st.text_input("Ask a question about the data:", placeholder="e.g., Find the best home health providers in Miami")
    
    if user_question and st.button("Ask AI Assistant", type="primary"):
        if not VECTOR_DB_AVAILABLE or st.session_state.vector_db is None:
            st.error("AI Assistant requires ChromaDB. Please install: `pip install chromadb sentence-transformers`")
        else:
            with st.spinner("Searching data and generating response..."):
                try:
                    # Perform RAG query
                    rag_results = st.session_state.vector_db.rag_query(user_question, n_context=5)
                
                # Display results
                st.subheader("🔍 Retrieved Information")
                
                if rag_results['context_documents']:
                    for i, doc in enumerate(rag_results['context_documents'][:3]):
                        with st.expander(f"Result {i+1}: {doc['source_type'].title()} - {doc['id']}"):
                            st.write(doc['document'][:500] + "..." if len(doc['document']) > 500 else doc['document'])
                            st.json(doc['metadata'])
                    
                    # Context summary
                    st.subheader("📊 Search Summary")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Provider Results", rag_results['provider_count'])
                    with col2:
                        st.metric("County Results", rag_results['county_count'])
                    with col3:
                        st.metric("Benchmark Results", rag_results['benchmark_count'])
                        
                    # Note about LLM integration
                    st.info("""
                    🤖 **Next Step**: The retrieved context above would be sent to a Large Language Model (LLM) 
                    like GPT-4, Claude, or Llama to generate a comprehensive answer to your question.
                    
                    For a complete RAG implementation, integrate with OpenAI API, Anthropic Claude, or run a local model.
                    """)
                    
                else:
                    st.warning("No relevant information found for your question. Try rephrasing or asking about providers, quality metrics, or geographic areas.")
                    
                except Exception as e:
                    st.error(f"AI Assistant error: {str(e)}")

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
            AVG(composite_quality_score) as avg_quality
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Provider count by state
            fig = px.bar(
                geo_df.head(15),
                x='state',
                y='provider_count',
                title="Providers by State (Top 15)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Quality rate by state
            fig = px.bar(
                geo_df.head(15),
                x='state', 
                y='avg_quality',
                title="Average Quality Score by State (Top 15)"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Vector database statistics
        st.subheader("Vector Database Status")
        if VECTOR_DB_AVAILABLE and st.session_state.vector_db:
            vector_stats = st.session_state.vector_db.get_collection_stats()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Provider Documents", vector_stats.get('providers', 0))
            with col2:
                st.metric("County Documents", vector_stats.get('counties', 0))
            with col3:
                st.metric("Benchmark Documents", vector_stats.get('benchmarks', 0))
                
            if sum(vector_stats.values()) == 0:
                st.warning("Vector database not initialized. Run the vector_database.py script to enable AI search.")
        else:
            st.warning("Vector database not available. Install ChromaDB to enable AI search: `pip install chromadb sentence-transformers`")
            
    except Exception as e:
        st.error(f"Data overview error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("🏥 **CMS Home Health Data Explorer** | Built with Streamlit, ChromaDB, and SQLite")
