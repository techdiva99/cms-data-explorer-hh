"""
Common UI components for the CMS Home Health Data Explorer.
Provides reusable widgets and helper functions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@st.cache_data
def get_states():
    """Get list of all states from providers table."""
    query = "SELECT DISTINCT state FROM providers ORDER BY state"
    conn = st.session_state.analytics._get_connection()
    try:
        states_df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return states_df['state'].tolist()


@st.cache_data  
def get_cities_by_state(state):
    """Get list of cities for a given state."""
    query = "SELECT DISTINCT city FROM providers WHERE state = ? ORDER BY city"
    conn = st.session_state.analytics._get_connection()
    try:
        cities_df = pd.read_sql_query(query, conn, params=[state])
    finally:
        conn.close()
    return cities_df['city'].tolist()


def render_geographic_filters(key_prefix="", include_cbsa=True, include_quality_filters=False):
    """
    Render standardized geographic filter controls.
    
    Args:
        key_prefix: Unique prefix for widget keys to avoid conflicts
        include_cbsa: Whether to include CBSA search
        include_quality_filters: Whether to include quality/rural filters
    
    Returns:
        dict: Dictionary containing filter values
    """
    filters = {}
    
    # Provider name and CCN search
    if include_quality_filters:
        col1, col2 = st.columns(2)
        with col1:
            filters['provider_name'] = st.text_input(
                "🔍 Provider Name", 
                placeholder="Enter provider name (partial matches allowed)",
                key=f"{key_prefix}_provider_name"
            )
        with col2:
            filters['ccn'] = st.text_input(
                "🏥 CCN", 
                placeholder="Enter CCN (partial matches allowed)",
                key=f"{key_prefix}_ccn"
            )
    
    # Geographic filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filters['state'] = st.selectbox(
            "Select State", 
            ["All"] + get_states(),
            key=f"{key_prefix}_state"
        )
        
    with col2:
        if filters['state'] != "All":
            cities = get_cities_by_state(filters['state'])
            filters['city'] = st.selectbox(
                "Select City", 
                ["All"] + cities,
                key=f"{key_prefix}_city"
            )
        else:
            filters['city'] = st.text_input(
                "Enter City",
                key=f"{key_prefix}_city_text"
            )
            
    with col3:
        filters['zip_code'] = st.text_input(
            "Enter ZIP Code",
            key=f"{key_prefix}_zip"
        )
    
    with col4:
        if include_cbsa:
            filters['cbsa'] = st.text_input(
                "🏙️ Metropolitan Area (CBSA)", 
                placeholder="e.g., Los Angeles, New York, Chicago",
                help="Search by Core Based Statistical Area / Metropolitan Area",
                key=f"{key_prefix}_cbsa"
            )
    
    # Quality and Geographic Classification filters
    if include_quality_filters:
        col1, col2, col3 = st.columns(3)
        with col1:
            filters['high_quality_only'] = st.checkbox(
                "High Quality Providers Only",
                key=f"{key_prefix}_high_quality"
            )
            
        with col2:
            filters['rural_filter'] = st.selectbox(
                "Rural/Urban Filter", 
                ["All", "Rural Only", "Urban Only", "Frontier Only"],
                key=f"{key_prefix}_rural_filter"
            )
            
        with col3:
            filters['min_quality'] = st.slider(
                "Minimum Quality Score", 
                1.0, 5.0, 1.0, 0.5,
                key=f"{key_prefix}_min_quality"
            )
    
    return filters


def render_download_button(data, filename, label="Download CSV", help_text=None):
    """
    Render a standardized download button for CSV data.
    
    Args:
        data: DataFrame or dict to download
        filename: Name of the file (without extension)
        label: Button label text
        help_text: Optional help text for the button
    """
    if isinstance(data, dict):
        # Convert dict to DataFrame if needed
        data = pd.DataFrame([data])
    
    if not data.empty:
        csv = data.to_csv(index=False)
        st.download_button(
            label=label,
            data=csv,
            file_name=f"{filename}.csv",
            mime="text/csv",
            help=help_text
        )


def create_provider_map(df, title="Provider Locations", height=500):
    """
    Create a standardized provider location map.
    
    Args:
        df: DataFrame with provider data including lat, lon, provider_name
        title: Map title
        height: Map height in pixels
    
    Returns:
        plotly.graph_objects.Figure: The map figure
    """
    if df.empty:
        st.warning("No data available for mapping.")
        return None
    
    # Create the map
    fig = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        hover_name="provider_name",
        hover_data={
            "lat": False,
            "lon": False,
            "city": True,
            "state": True,
            "zip_code": True
        },
        zoom=5,
        height=height,
        title=title
    )
    
    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=df['lat'].mean(), lon=df['lon'].mean())
        ),
        margin=dict(r=0, t=50, l=0, b=0),
        title_x=0.5
    )
    
    return fig


def render_metrics_cards(metrics_dict, columns=4):
    """
    Render a row of metric cards.
    
    Args:
        metrics_dict: Dict with metric_name: value pairs
        columns: Number of columns to display
    """
    cols = st.columns(columns)
    for i, (key, value) in enumerate(metrics_dict.items()):
        with cols[i % columns]:
            if isinstance(value, float):
                if value >= 1000:
                    display_value = f"{value:,.0f}"
                else:
                    display_value = f"{value:.2f}"
            else:
                display_value = str(value)
            st.metric(label=key, value=display_value)


def render_data_quality_warning(df, min_rows=1):
    """
    Show a warning if data quality is poor.
    
    Args:
        df: DataFrame to check
        min_rows: Minimum number of rows expected
    """
    if df.empty:
        st.error("No data found matching your criteria.")
        return True
    elif len(df) < min_rows:
        st.warning(f"Limited data available ({len(df)} records). Results may not be comprehensive.")
        return False
    return False


def create_quality_chart(df, x_col, y_col, title="Quality Metrics", chart_type="scatter"):
    """
    Create a standardized quality metrics chart.
    
    Args:
        df: DataFrame with quality data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        chart_type: Type of chart ("scatter", "bar", "line")
    
    Returns:
        plotly.graph_objects.Figure: The chart figure
    """
    if df.empty:
        st.warning("No data available for charting.")
        return None
    
    if chart_type == "scatter":
        fig = px.scatter(
            df, 
            x=x_col, 
            y=y_col,
            hover_data=df.columns.tolist(),
            title=title
        )
    elif chart_type == "bar":
        fig = px.bar(
            df, 
            x=x_col, 
            y=y_col,
            title=title
        )
    elif chart_type == "line":
        fig = px.line(
            df, 
            x=x_col, 
            y=y_col,
            title=title
        )
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title()
    )
    
    return fig


def create_comparison_table(df, sort_column=None, ascending=False):
    """
    Create a standardized comparison table with formatting.
    
    Args:
        df: DataFrame to display
        sort_column: Column to sort by
        ascending: Sort direction
    
    Returns:
        pd.DataFrame: Formatted DataFrame
    """
    if df.empty:
        return df
    
    # Sort if specified
    if sort_column and sort_column in df.columns:
        df = df.sort_values(sort_column, ascending=ascending)
    
    # Format numeric columns
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32']:
            if df[col].max() > 100:
                df[col] = df[col].round(0).astype(int)
            else:
                df[col] = df[col].round(2)
    
    return df
