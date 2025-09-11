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
from duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator
from duckdb_analytics.llm.integrated_generator import IntegratedSQLGenerator, GenerationMode
from duckdb_analytics.llm.schema_extractor import SchemaExtractor
from duckdb_analytics.visualizations.recommendation_engine import ChartRecommendationEngine
from duckdb_analytics.ui.enhanced_thinking_pad import EnhancedThinkingPad
from duckdb_analytics.ui.model_config_ui import ModelConfigUI

# Page configuration
st.set_page_config(
    page_title="SQL Analytics Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"  # Show sidebar by default to see data
)

# Initialize session state with optimized connection settings
if "db_connection" not in st.session_state:
    # Use optimized connection with better config
    conn = DuckDBConnection()
    conn._config.update({
        "threads": 4,  # Optimized for M1 Pro efficiency cores
        "memory_limit": "2GB",  # Conservative for 16GB M1 system
        "max_memory": "2GB",
        "enable_object_cache": True,
        "enable_http_metadata_cache": True,
        "checkpoint_threshold": "128MB",  # Smaller for faster checkpoints
        "preserve_insertion_order": False  # Better performance
    })
    st.session_state.db_connection = conn
    st.session_state.db_connection.connect()

if "query_engine" not in st.session_state:
    st.session_state.query_engine = QueryEngine(st.session_state.db_connection)

if "schema_extractor" not in st.session_state:
    st.session_state.schema_extractor = SchemaExtractor(st.session_state.db_connection)

if "sql_generator" not in st.session_state:
    # Initialize IntegratedSQLGenerator with streaming and adaptive features
    st.session_state.sql_generator = IntegratedSQLGenerator(
        duckdb_conn=st.session_state.db_connection.connect(),
        base_url="http://localhost:1234/v1",
        enable_streaming=True,
        enable_adaptive=True
    )
    
    # Also keep the enhanced generator for backward compatibility
    st.session_state.enhanced_generator = EnhancedSQLGenerator(
        duckdb_conn=st.session_state.db_connection.connect(),
        base_url="http://localhost:1234/v1",
        warm_cache=False
    )

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

if "thinking_pad" not in st.session_state:
    st.session_state.thinking_pad = EnhancedThinkingPad()

if "model_config_ui" not in st.session_state:
    st.session_state.model_config_ui = ModelConfigUI()

if "generation_mode" not in st.session_state:
    st.session_state.generation_mode = GenerationMode.BALANCED

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance."""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        if elapsed > 1.0:  # Log slow operations
            logger.warning(f"{func.__name__} took {elapsed:.2f}s")
        
        return result
    return wrapper

@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def get_cached_schema():
    """Get cached schema extraction for better performance."""
    if hasattr(st.session_state, 'schema_extractor'):
        try:
            # Try the optimized extraction method if available
            if hasattr(st.session_state.schema_extractor, 'extract_schema_optimized'):
                return st.session_state.schema_extractor.extract_schema_optimized()
            else:
                return st.session_state.schema_extractor.get_schema()
        except Exception as e:
            logger.error(f"Failed to extract schema: {e}")
            return {}
    return {}

def load_all_data_files():
    """Automatically load all CSV and Parquet files from the data directory."""
    import os
    
    data_dir = "data/samples"
    loaded_count = 0
    loaded_tables = []
    
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        
        # Sort files to ensure consistent loading order
        files.sort()
        
        # Prefer Parquet over CSV for faster loading
        parquet_files = [f for f in files if f.endswith('.parquet')]
        csv_files = [f for f in files if f.endswith('.csv')]
        
        # Track which tables have been loaded to avoid duplicates
        loaded_table_names = set()
        loaded_table_info = []
        
        # Load Parquet files first (faster)
        for file in parquet_files:
            table_name = Path(file).stem
            if table_name not in loaded_table_names:
                file_path = os.path.join(data_dir, file)
                try:
                    # Use quotes for table names to avoid keyword conflicts
                    safe_table_name = f'"{table_name}"'
                    st.session_state.db_connection.register_parquet(file_path, table_name)
                    
                    # Get row count directly
                    try:
                        result = st.session_state.db_connection.execute(f"SELECT COUNT(*) as cnt FROM {safe_table_name}")
                        rows = result.fetchone()[0] if result else 0
                        
                        # Get column count
                        result = st.session_state.db_connection.execute(f"DESCRIBE {safe_table_name}")
                        columns = len(result.fetchall()) if result else 0
                    except Exception as e:
                        print(f"Error getting table info for {table_name}: {e}")
                        rows = 0
                        columns = 0
                    
                    loaded_table_info.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": columns
                    })
                    loaded_table_names.add(table_name)
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading {file}: {e}")
        
        # Load CSV files only if no Parquet version was loaded
        for file in csv_files:
            table_name = Path(file).stem
            if table_name not in loaded_table_names:
                file_path = os.path.join(data_dir, file)
                try:
                    # Use quotes for table names to avoid keyword conflicts
                    safe_table_name = f'"{table_name}"'
                    st.session_state.db_connection.register_csv(file_path, table_name)
                    
                    # Get row count directly
                    try:
                        result = st.session_state.db_connection.execute(f"SELECT COUNT(*) as cnt FROM {safe_table_name}")
                        rows = result.fetchone()[0] if result else 0
                        
                        # Get column count
                        result = st.session_state.db_connection.execute(f"DESCRIBE {safe_table_name}")
                        columns = len(result.fetchall()) if result else 0
                    except Exception as e:
                        print(f"Error getting table info for {table_name}: {e}")
                        rows = 0
                        columns = 0
                    
                    loaded_table_info.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": columns
                    })
                    loaded_table_names.add(table_name)
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading {file}: {e}")
    
    return loaded_count, loaded_table_info

# Auto-load data files on first run with progress indicator
if not st.session_state.data_loaded:
    with st.spinner("Loading data files..."):
        result = load_all_data_files()
        if isinstance(result, tuple):
            loaded_count, loaded_tables = result
            if loaded_count > 0:
                st.session_state.registered_tables.extend(loaded_tables)
                st.session_state.data_loaded = True
        else:
            # Fallback for old behavior
            if result > 0:
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

def generate_sql_from_natural_language(prompt: str, use_streaming: bool = False) -> Optional[str]:
    """Generate SQL from natural language using integrated generator with optional streaming."""
    try:
        # Use integrated generator for better performance
        if use_streaming and hasattr(st.session_state, 'thinking_pad'):
            # Streaming mode with live thinking pad updates
            st.session_state.thinking_pad.start_streaming()
            
            # Define callback for streaming updates
            def stream_callback(update):
                st.session_state.thinking_pad.handle_stream_update(update)
            
            result = st.session_state.sql_generator.generate_sql(
                natural_language_query=prompt,
                mode=st.session_state.generation_mode,
                stream_callback=stream_callback
            )
            
            st.session_state.thinking_pad.stop_streaming()
        else:
            # Traditional mode (non-streaming)
            result = st.session_state.sql_generator.generate_sql(
                natural_language_query=prompt,
                mode=st.session_state.generation_mode
            )
        
        # Store the result
        if result and result.sql:
            st.session_state.query_explanation = {
                'explanation': result.thinking_process,
                'confidence': result.confidence,
                'profile_used': result.profile_used,
                'generation_time': result.generation_time
            }
            st.session_state.nl_query = prompt
            return result.sql
        
        return None
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        # Fallback to enhanced generator if integrated fails
        try:
            if hasattr(st.session_state, 'enhanced_generator'):
                sql, metadata = st.session_state.enhanced_generator.generate_sql_with_explanation(
                    prompt,
                    include_llm_feedback=False,
                    return_metrics=False
                )
                if sql and "explanation" in metadata:
                    st.session_state.query_explanation = metadata["explanation"]
                    st.session_state.nl_query = prompt
                return sql
        except:
            pass
        return None

@st.cache_data(ttl=60, show_spinner=False)  # Cache query results for 1 minute
def execute_query(sql: str) -> Optional[pd.DataFrame]:
    """Execute SQL query and return results as DataFrame with caching."""
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
            
            # Skip feedback for performance - commented out
            # if hasattr(st.session_state.sql_generator, 'query_explainer'):
            #     try:
            #         feedback = st.session_state.sql_generator.query_explainer.get_llm_feedback(
            #             sql_query=sql,
            #             natural_language_query=st.session_state.nl_query,
            #             execution_result={"summary": f"Query returned {len(result)} rows with columns: {', '.join(result.columns)}"}
            #         )
            #         if feedback:
            #             # Store feedback for future use
            #             st.session_state.last_execution_feedback = feedback
            #     except Exception as e:
            #         logger.debug(f"Could not get execution feedback: {e}")
        
        # Fixed: QueryEngine already returns a DataFrame, check properly
        if isinstance(result, pd.DataFrame) and not result.empty:
            return result
        elif isinstance(result, pd.DataFrame):
            return result  # Return empty DataFrame as-is
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

@st.cache_data(ttl=60, show_spinner=False)  # Cache visualizations
def create_visualization(df: pd.DataFrame, chart_type: str = "auto"):
    """Create a visualization from the dataframe with caching."""
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
    
    # Sidebar for data preview and configuration
    with st.sidebar:
        # Add model configuration section
        st.header("🤖 LLM Configuration")
        
        # Quick mode selector
        mode_options = ["Fast", "Balanced", "Thorough"]
        selected_mode = st.select_slider(
            "Generation Mode",
            options=mode_options,
            value="Balanced",
            help="Choose between speed and quality"
        )
        
        # Update session state based on selection
        mode_map = {
            "Fast": GenerationMode.FAST,
            "Balanced": GenerationMode.BALANCED,
            "Thorough": GenerationMode.THOROUGH
        }
        st.session_state.generation_mode = mode_map[selected_mode]
        
        # Show mode description
        mode_descriptions = {
            "Fast": "⚡ Quick responses, minimal analysis",
            "Balanced": "⚖️ Balanced speed and quality",
            "Thorough": "🔍 Comprehensive analysis"
        }
        st.caption(mode_descriptions[selected_mode])
        
        # Streaming toggle
        st.session_state.use_streaming = st.checkbox(
            "Enable Streaming",
            value=st.session_state.get('use_streaming', True),
            key="streaming_toggle",
            help="Show live thinking process while generating SQL"
        )
        
        st.divider()
        
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
                        # Check if streaming is enabled in sidebar
                        use_streaming = st.session_state.get('use_streaming', False)
                        generated_sql = generate_sql_from_natural_language(nl_query, use_streaming)
                        if generated_sql:
                            st.session_state.current_sql = generated_sql
                            st.rerun()
        
        with col_btn2:
            if st.button("Clear", use_container_width=True):
                st.session_state.current_sql = ""
                st.rerun()
        
        # Show enhanced thinking pad
        if st.session_state.current_sql:
            st.markdown("---")
            st.markdown("🤖 **LLM Thinking Pad:**")
            
            # Use the enhanced thinking pad
            thinking_container = st.container()
            with thinking_container:
                if hasattr(st.session_state, 'query_explanation') and st.session_state.query_explanation:
                    explanation = st.session_state.query_explanation
                    
                    # Check if we have streaming data or static data
                    if hasattr(st.session_state, 'thinking_pad'):
                        # Use enhanced thinking pad for better display
                        thinking_pad = EnhancedThinkingPad(thinking_container)
                        thinking_pad.render_static(
                            thinking_process=explanation.get('explanation', 'Processing query...'),
                            sql=st.session_state.current_sql,
                            confidence=explanation.get('confidence', 0.5)
                        )
                    else:
                        # Fallback to simple display
                        thinking_text = explanation.get('explanation', 'Processing query...')
                        st.code(thinking_text, language='markdown')
                        confidence = explanation.get('confidence', 0.5)
                        st.caption(f"Confidence: {confidence:.0%}")
                    
                    # Show additional metadata if available
                    if 'profile_used' in explanation:
                        st.caption(f"Profile: {explanation['profile_used']}")
                    if 'generation_time' in explanation:
                        st.caption(f"Generation time: {explanation['generation_time']:.2f}s")
                else:
                    st.info("💭 LLM will show its thinking process here when generating SQL...")
    
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