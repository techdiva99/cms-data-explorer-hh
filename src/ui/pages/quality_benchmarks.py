"""
Quality Benchmarks page for the CMS Home Health Data Explorer.
Displays quality benchmarks and statistics across different scopes.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.ui.components import (
    get_states,
    render_metrics_cards,
    render_data_quality_warning,
    render_download_button
)


def show():
    """Render the Quality Benchmarks page."""
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
                _display_quality_benchmarks(benchmarks, benchmark_scope, benchmark_state)
            else:
                st.error(benchmarks['error'])
                
        except Exception as e:
            st.error(f"Error getting benchmarks: {str(e)}")


def _display_quality_benchmarks(benchmarks, scope, state=None):
    """Display quality benchmark results."""
    
    scope_text = f"{scope}" + (f" - {state}" if state else "")
    st.subheader(f"📊 Quality Benchmarks ({scope_text})")
    
    # Display key statistics
    metrics = {
        "Total Providers": f"{benchmarks['total_providers']:,}",
        "Mean Quality": f"{benchmarks['mean_quality']:.2f}",
        "Median Quality": f"{benchmarks['median_quality']:.2f}",
        "Standard Deviation": f"{benchmarks['std_quality']:.2f}"
    }
    render_metrics_cards(metrics, columns=4)
    
    # Display percentiles
    st.subheader("📈 Quality Score Percentiles")
    percentiles = benchmarks['percentiles']
    
    percentile_metrics = {
        "25th Percentile": f"{percentiles['25th']:.2f}",
        "50th Percentile": f"{percentiles['50th']:.2f}",
        "75th Percentile": f"{percentiles['75th']:.2f}",
        "90th Percentile": f"{percentiles['90th']:.2f}"
    }
    render_metrics_cards(percentile_metrics, columns=4)
    
    # Quality distribution chart
    if 'quality_distribution' in benchmarks:
        _display_quality_distribution(benchmarks['quality_distribution'])
    
    # Quality by category if available
    if 'quality_by_category' in benchmarks:
        _display_quality_by_category(benchmarks['quality_by_category'])
    
    # Top performers if available
    if 'top_performers' in benchmarks and benchmarks['top_performers']:
        _display_top_performers(benchmarks['top_performers'])
    
    # Export functionality
    _render_benchmark_export(benchmarks, scope_text)


def _display_quality_distribution(quality_distribution):
    """Display quality score distribution chart."""
    st.subheader("📊 Quality Score Distribution")
    
    if quality_distribution:
        df = pd.DataFrame(quality_distribution)
        
        if not df.empty:
            fig = px.histogram(
                df,
                x='score_range',
                y='count',
                title="Distribution of Quality Scores",
                labels={'score_range': 'Quality Score Range', 'count': 'Number of Providers'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No quality distribution data available")
    else:
        st.info("Quality distribution data not available")


def _display_quality_by_category(quality_by_category):
    """Display quality metrics by category."""
    st.subheader("📋 Quality by Category")
    
    categories = ['ownership_type', 'provider_size', 'rural_urban', 'state']
    
    for category in categories:
        if category in quality_by_category and quality_by_category[category]:
            with st.expander(f"Quality by {category.replace('_', ' ').title()}", expanded=False):
                
                cat_data = quality_by_category[category]
                df = pd.DataFrame(cat_data)
                
                if not df.empty:
                    # Display as both chart and table
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Bar chart
                        fig = px.bar(
                            df,
                            x='category',
                            y='mean_quality',
                            title=f"Average Quality by {category.replace('_', ' ').title()}",
                            labels={'category': category.replace('_', ' ').title(), 'mean_quality': 'Average Quality Score'}
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Summary table
                        display_df = df.copy()
                        display_df['mean_quality'] = display_df['mean_quality'].round(2)
                        
                        column_config = {
                            'category': category.replace('_', ' ').title(),
                            'provider_count': st.column_config.NumberColumn('Provider Count', format='%d'),
                            'mean_quality': st.column_config.NumberColumn('Avg Quality', format='%.2f')
                        }
                        
                        st.dataframe(
                            display_df,
                            column_config=column_config,
                            hide_index=True,
                            use_container_width=True
                        )


def _display_top_performers(top_performers):
    """Display top performing providers."""
    st.subheader("🏆 Top Performers")
    
    df = pd.DataFrame(top_performers)
    
    if not df.empty:
        # Format for display
        display_columns = ['ccn', 'provider_name', 'city', 'state', 'composite_quality_score']
        available_columns = [col for col in display_columns if col in df.columns]
        
        if available_columns:
            display_df = df[available_columns].copy()
            
            column_mapping = {
                'ccn': 'CCN',
                'provider_name': 'Provider Name',
                'city': 'City',
                'state': 'State',
                'composite_quality_score': 'Quality Score'
            }
            
            display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
            
            # Format quality score
            if 'Quality Score' in display_df.columns:
                display_df['Quality Score'] = display_df['Quality Score'].round(2)
            
            st.dataframe(
                display_df,
                column_config={
                    'Quality Score': st.column_config.NumberColumn('Quality Score', format='%.2f')
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Top performers data structure not compatible for display")
    else:
        st.info("No top performers data available")


def _render_benchmark_export(benchmarks, scope_text):
    """Render export options for benchmark data."""
    st.subheader("📥 Export Benchmark Data")
    
    # Create export data
    export_data = {
        'Scope': [scope_text],
        'Total_Providers': [benchmarks['total_providers']],
        'Mean_Quality': [benchmarks['mean_quality']],
        'Median_Quality': [benchmarks['median_quality']],
        'Std_Quality': [benchmarks['std_quality']],
        'Percentile_25th': [benchmarks['percentiles']['25th']],
        'Percentile_50th': [benchmarks['percentiles']['50th']],
        'Percentile_75th': [benchmarks['percentiles']['75th']],
        'Percentile_90th': [benchmarks['percentiles']['90th']]
    }
    
    render_download_button(
        pd.DataFrame(export_data),
        f"quality_benchmarks_{scope_text.lower().replace(' ', '_').replace('-', '_')}",
        "📄 Download Benchmark Summary",
        "Download the quality benchmark summary as CSV"
    )
    
    # Export top performers if available
    if 'top_performers' in benchmarks and benchmarks['top_performers']:
        top_performers_df = pd.DataFrame(benchmarks['top_performers'])
        render_download_button(
            top_performers_df,
            f"top_performers_{scope_text.lower().replace(' ', '_').replace('-', '_')}",
            "🏆 Download Top Performers",
            "Download the top performing providers as CSV"
        )
