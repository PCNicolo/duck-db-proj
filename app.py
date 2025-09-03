"""
Streamlined SQL Analytics Studio
A simplified DuckDB analytics tool with natural language SQL generation and smart visualization.
"""

import streamlit as st
import pandas as pd
import duckdb
import tempfile
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import our modules
import sys
sys.path.append('src')
from duckdb_analytics.core.connection import DuckDBConnection
from duckdb_analytics.core.query_engine import QueryEngine
from duckdb_analytics.llm.sql_generator import SQLGenerator
from duckdb_analytics.llm.schema_extractor import SchemaExtractor
from duckdb_analytics.visualizations.recommendation_engine import ChartRecommendationEngine

# Page configuration
st.set_page_config(
    page_title="SQL Analytics Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"  # Show sidebar by default to see data
)

# Initialize session state
if "db_connection" not in st.session_state:
    st.session_state.db_connection = DuckDBConnection()
    st.session_state.db_connection.connect()

if "query_engine" not in st.session_state:
    st.session_state.query_engine = QueryEngine(st.session_state.db_connection)

if "schema_extractor" not in st.session_state:
    st.session_state.schema_extractor = SchemaExtractor(st.session_state.db_connection)

if "sql_generator" not in st.session_state:
    st.session_state.sql_generator = SQLGenerator(schema_extractor=st.session_state.schema_extractor)

if "chart_recommender" not in st.session_state:
    st.session_state.chart_recommender = ChartRecommendationEngine()

if "registered_tables" not in st.session_state:
    st.session_state.registered_tables = []

if "query_result" not in st.session_state:
    st.session_state.query_result = None

if "current_sql" not in st.session_state:
    st.session_state.current_sql = ""

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

if "query_explanation" not in st.session_state:
    st.session_state.query_explanation = None

if "nl_query" not in st.session_state:
    st.session_state.nl_query = ""

def load_all_data_files():
    """Automatically load all CSV and Parquet files from the data directory."""
    import os
    
    data_dir = "data/samples"
    loaded_count = 0
    
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        
        # Sort files to ensure consistent loading order
        files.sort()
        
        # Prefer Parquet over CSV for faster loading
        parquet_files = [f for f in files if f.endswith('.parquet')]
        csv_files = [f for f in files if f.endswith('.csv')]
        
        # Track which tables have been loaded to avoid duplicates
        loaded_tables = set()
        
        # Load Parquet files first (faster)
        for file in parquet_files:
            table_name = Path(file).stem
            if table_name not in loaded_tables:
                file_path = os.path.join(data_dir, file)
                try:
                    st.session_state.db_connection.register_parquet(file_path, table_name)
                    
                    # Get table info
                    info = st.session_state.db_connection.get_table_info(table_name)
                    rows = st.session_state.db_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    
                    st.session_state.registered_tables.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": len(info)
                    })
                    loaded_tables.add(table_name)
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading {file}: {e}")
        
        # Load CSV files only if no Parquet version was loaded
        for file in csv_files:
            table_name = Path(file).stem
            if table_name not in loaded_tables:
                file_path = os.path.join(data_dir, file)
                try:
                    st.session_state.db_connection.register_csv(file_path, table_name)
                    
                    # Get table info
                    info = st.session_state.db_connection.get_table_info(table_name)
                    rows = st.session_state.db_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    
                    st.session_state.registered_tables.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": len(info)
                    })
                    loaded_tables.add(table_name)
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading {file}: {e}")
    
    return loaded_count

# Auto-load data files on first run
if not st.session_state.data_loaded:
    loaded_count = load_all_data_files()
    if loaded_count > 0:
        st.session_state.data_loaded = True

def load_sample_data():
    """Load sample data for testing."""
    conn = st.session_state.db_connection
    
    # Create sample sales data
    sample_query = """
    CREATE OR REPLACE TABLE sales AS 
    SELECT 
        DATE '2024-01-01' + INTERVAL (i % 365) DAY as order_date,
        'Customer_' || (i % 100) as customer_id,
        'Product_' || (i % 50) as product_id,
        ROUND(RANDOM() * 1000, 2) as amount,
        CASE 
            WHEN i % 4 = 0 THEN 'North'
            WHEN i % 4 = 1 THEN 'South'
            WHEN i % 4 = 2 THEN 'East'
            ELSE 'West'
        END as region
    FROM generate_series(1, 1000) as t(i);
    """
    
    try:
        conn.execute(sample_query)
        st.session_state.registered_tables.append({
            "name": "sales",
            "rows": 1000,
            "columns": 5
        })
        return True
    except Exception as e:
        st.error(f"Error loading sample data: {e}")
        return False

def process_uploaded_file(uploaded_file):
    """Process an uploaded CSV or Parquet file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name
    
    table_name = Path(uploaded_file.name).stem.replace(" ", "_").replace("-", "_")
    
    try:
        if uploaded_file.name.endswith(".csv"):
            st.session_state.db_connection.register_csv(tmp_path, table_name)
        else:
            st.session_state.db_connection.register_parquet(tmp_path, table_name)
        
        # Get table info
        info = st.session_state.db_connection.get_table_info(table_name)
        rows = st.session_state.db_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        st.session_state.registered_tables.append({
            "name": table_name,
            "rows": rows,
            "columns": len(info)
        })
        return True
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False

def generate_sql_from_natural_language(prompt: str) -> Optional[str]:
    """Generate SQL from natural language using LM Studio with enhanced explanations."""
    if not st.session_state.sql_generator.is_available():
        st.warning("LM Studio is not available. Please ensure it's running on localhost:1234")
        return None
    
    try:
        # Generate SQL with enhanced explanation and LLM feedback
        sql, metadata = st.session_state.sql_generator.generate_sql_with_explanation(
            prompt,
            include_llm_feedback=True,
            return_metrics=True
        )
        
        # Store the explanation in session state for display
        if sql and "explanation" in metadata:
            st.session_state.query_explanation = metadata["explanation"]
            st.session_state.nl_query = prompt
        
        return sql
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        return None

def execute_query(sql: str) -> Optional[pd.DataFrame]:
    """Execute SQL query and return results as DataFrame."""
    try:
        result = st.session_state.query_engine.execute_query(sql)
        
        # If we have an explanation and a result, provide feedback for learning
        if (hasattr(st.session_state, 'query_explanation') and 
            st.session_state.query_explanation and 
            hasattr(st.session_state, 'nl_query') and 
            st.session_state.nl_query and
            isinstance(result, pd.DataFrame)):
            
            # Create execution summary for feedback
            execution_summary = {
                "rows_returned": len(result),
                "columns": list(result.columns),
                "success": True
            }
            
            # Request feedback with execution results
            if hasattr(st.session_state.sql_generator, 'query_explainer'):
                try:
                    feedback = st.session_state.sql_generator.query_explainer.get_llm_feedback(
                        sql_query=sql,
                        natural_language_query=st.session_state.nl_query,
                        execution_result={"summary": f"Query returned {len(result)} rows with columns: {', '.join(result.columns)}"}
                    )
                    if feedback:
                        # Store feedback for future use
                        st.session_state.last_execution_feedback = feedback
                except Exception as e:
                    logger.debug(f"Could not get execution feedback: {e}")
        
        # Fixed: QueryEngine already returns a DataFrame, check properly
        if isinstance(result, pd.DataFrame) and not result.empty:
            return result
        elif isinstance(result, pd.DataFrame):
            return result  # Return empty DataFrame as-is
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

def create_visualization(df: pd.DataFrame, chart_type: str = "auto"):
    """Create a visualization from the dataframe."""
    if df.empty:
        st.info("No data to visualize")
        return
    
    # Auto-detect chart type if needed
    if chart_type == "auto":
        recommendations = st.session_state.chart_recommender.recommend_charts(df)
        if recommendations:
            chart_type = recommendations[0].chart_type
        else:
            chart_type = "table"
    
    # Create the appropriate chart
    if chart_type == "line":
        # Assume first column is x-axis, others are y-values
        if len(df.columns) >= 2:
            fig = px.line(df, x=df.columns[0], y=df.columns[1:])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Line chart requires at least 2 columns")
    
    elif chart_type == "bar":
        if len(df.columns) >= 2:
            fig = px.bar(df, x=df.columns[0], y=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Bar chart requires at least 2 columns")
    
    elif chart_type == "scatter":
        if len(df.columns) >= 2:
            fig = px.scatter(df, x=df.columns[0], y=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Scatter plot requires at least 2 columns")
    
    elif chart_type == "pie":
        if len(df.columns) >= 2:
            fig = px.pie(df, names=df.columns[0], values=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Pie chart requires at least 2 columns")
    
    elif chart_type == "heatmap":
        # Try to create a pivot table for heatmap
        if len(df.columns) >= 3:
            try:
                pivot = df.pivot_table(index=df.columns[0], columns=df.columns[1], values=df.columns[2])
                fig = px.imshow(pivot, aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("Cannot create heatmap from this data structure")
        else:
            st.warning("Heatmap requires at least 3 columns")
    
    else:  # Default to table
        st.dataframe(df, use_container_width=True)

def main():
    """Main application."""
    
    # Sidebar for data preview
    with st.sidebar:
        st.header("📁 Data Browser")
        
        # Data loading info and controls
        if st.session_state.data_loaded:
            st.success(f"✅ Auto-loaded {len(st.session_state.registered_tables)} tables from /data/samples")
        
        # Additional file upload option
        uploaded_file = st.file_uploader("Upload Additional File", type=["csv", "parquet"], label_visibility="visible")
        if uploaded_file:
            if process_uploaded_file(uploaded_file):
                st.success(f"Added {uploaded_file.name}!")
                st.rerun()
        
        # Reload data button
        if st.button("🔄 Reload All Data", use_container_width=True):
            st.session_state.registered_tables = []
            st.session_state.data_loaded = False
            st.rerun()
        
        # Show available tables and data preview
        if st.session_state.registered_tables:
            st.divider()
            st.subheader("Available Tables")
            
            for table in st.session_state.registered_tables:
                with st.expander(f"📊 **{table['name']}** ({table['rows']:,} rows)", expanded=True):
                    try:
                        # Get table schema
                        columns_query = f"DESCRIBE {table['name']}"
                        columns_result = st.session_state.db_connection.execute(columns_query)
                        schema_df = pd.DataFrame(columns_result.fetchall())
                        
                        # Create tabs for schema and data
                        tab1, tab2 = st.tabs(["Data Preview", "Schema"])
                        
                        with tab1:
                            # Get sample data from the table
                            preview_query = f"SELECT * FROM {table['name']} LIMIT 10"
                            preview_result = st.session_state.db_connection.execute(preview_query)
                            preview_df = pd.DataFrame(preview_result.fetchall())
                            
                            # Set column names
                            if not schema_df.empty:
                                preview_df.columns = schema_df[0].tolist()[:len(preview_df.columns)]
                            
                            # Show preview with formatting
                            st.dataframe(
                                preview_df, 
                                use_container_width=True, 
                                height=250,
                                hide_index=True
                            )
                            
                            # Quick action buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📋 Use in SQL", key=f"use_{table['name']}", use_container_width=True):
                                    st.session_state.current_sql = f"SELECT * FROM {table['name']} LIMIT 100"
                                    st.rerun()
                            with col2:
                                if st.button("📊 Quick Stats", key=f"stats_{table['name']}", use_container_width=True):
                                    st.session_state.current_sql = f"SELECT COUNT(*) as total_rows, COUNT(DISTINCT {schema_df[0].iloc[0]}) as unique_{schema_df[0].iloc[0]} FROM {table['name']}"
                                    st.rerun()
                        
                        with tab2:
                            # Show schema information
                            if not schema_df.empty and len(schema_df.columns) >= 2:
                                schema_display = pd.DataFrame({
                                    'Column': schema_df[0],
                                    'Type': schema_df[1]
                                })
                                st.dataframe(
                                    schema_display, 
                                    use_container_width=True,
                                    hide_index=True,
                                    height=250
                                )
                            else:
                                st.info("Schema information not available")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")
        else:
            st.info("No data loaded. Use the buttons above to get started.")
    
    # Main content area
    st.title("📊 SQL Analytics Studio")
    
    # Show connection status
    if st.session_state.registered_tables:
        st.success(f"Connected to {len(st.session_state.registered_tables)} table(s)")
    
    st.divider()
    
    # Main layout: Chat and SQL Editor side by side
    col_chat, col_sql = st.columns([1, 1])
    
    with col_chat:
        st.subheader("💬 Chat Helper")
        
        # Natural language input
        nl_query = st.text_area(
            "Describe what you want to query:",
            placeholder="Example: Show me total sales by month",
            height=100,
            key="nl_input"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Generate SQL →", type="primary", use_container_width=True):
                if nl_query:
                    with st.spinner("Generating SQL..."):
                        generated_sql = generate_sql_from_natural_language(nl_query)
                        if generated_sql:
                            st.session_state.current_sql = generated_sql
                            st.rerun()
        
        with col_btn2:
            if st.button("Clear", use_container_width=True):
                st.session_state.current_sql = ""
                st.rerun()
        
        # Show explanation if we have a query
        if st.session_state.current_sql:
            st.markdown("---")
            st.markdown("💡 **Query Explanation:**")
            
            # Show enhanced explanation if available
            if hasattr(st.session_state, 'query_explanation') and st.session_state.query_explanation:
                explanation = st.session_state.query_explanation
                
                # Main explanation
                st.info(explanation.get('explanation', 'This query will analyze your data based on the SQL shown in the editor.'))
                
                # Show breakdown if available
                if explanation.get('query_breakdown'):
                    with st.expander("📋 Step-by-Step Breakdown", expanded=False):
                        for step in explanation['query_breakdown']:
                            st.markdown(f"**Step {step['step']}: {step['action']}**")
                            st.markdown(f"↳ {step['description']}")
                            if step.get('sql_fragment'):
                                st.code(step['sql_fragment'], language='sql')
                
                # Show confidence and feedback status
                col1, col2 = st.columns(2)
                with col1:
                    confidence = explanation.get('confidence', 0)
                    st.metric("Confidence", f"{confidence:.0%}")
                with col2:
                    if explanation.get('feedback_incorporated'):
                        st.success("✅ LLM Feedback Applied")
                    else:
                        st.info("ℹ️ Basic Explanation")
            else:
                st.info("This query will analyze your data based on the SQL shown in the editor. Click 'Run Query' to execute it.")
    
    with col_sql:
        st.subheader("📝 SQL Editor")
        
        # SQL editor
        sql_query = st.text_area(
            "SQL Query:",
            value=st.session_state.current_sql,
            height=200,
            placeholder="Enter SQL query or generate from chat...",
            key="sql_editor"
        )
        
        col_btn3, col_btn4 = st.columns(2)
        with col_btn3:
            if st.button("▶ Run Query", type="primary", use_container_width=True):
                if sql_query:
                    with st.spinner("Executing query..."):
                        result = execute_query(sql_query)
                        if result is not None:
                            st.session_state.query_result = result
                            st.session_state.current_sql = sql_query
        
        with col_btn4:
            if st.button("📋 Copy", use_container_width=True):
                st.write("SQL copied to clipboard!")  # Note: Actual clipboard functionality requires JavaScript
    
    # Results section
    if st.session_state.query_result is not None:
        st.divider()
        st.subheader("📊 Results")
        
        # View options
        col_view1, col_view2, col_view3 = st.columns([1, 1, 2])
        with col_view1:
            view_mode = st.radio("View:", ["Table", "Chart"], horizontal=True)
        
        with col_view2:
            if view_mode == "Chart":
                chart_type = st.selectbox(
                    "Chart Type:",
                    ["auto", "line", "bar", "scatter", "pie", "heatmap"],
                    label_visibility="collapsed"
                )
            else:
                chart_type = "table"
        
        # Display results
        if view_mode == "Table":
            st.dataframe(st.session_state.query_result, use_container_width=True)
        else:
            create_visualization(st.session_state.query_result, chart_type)
        
        # Show row count
        st.caption(f"Returned {len(st.session_state.query_result):,} rows")

if __name__ == "__main__":
    main()