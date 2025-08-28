"""Enhanced SQL Editor Component for Streamlit."""

import streamlit as st
import time
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
from datetime import datetime
import re
import logging

# Try to import optional dependencies
try:
    import streamlit_ace as st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False
    
try:
    import sqlparse
    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False

logger = logging.getLogger(__name__)

# SQL Keywords for syntax highlighting
SQL_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 
    'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'UNION',
    'AS', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'DISTINCT',
    'CREATE', 'TABLE', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER',
    'INTO', 'VALUES', 'SET', 'WITH', 'PARTITION', 'OVER', 'WINDOW',
    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'CAST', 'COALESCE',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'STDDEV', 'VARIANCE'
}

# DuckDB specific keywords
DUCKDB_KEYWORDS = {
    'PIVOT', 'UNPIVOT', 'ASOF', 'POSITIONAL', 'COLUMNS', 'EXCLUDE',
    'REPLACE', 'QUALIFY', 'SAMPLE', 'TABLESAMPLE', 'USING'
}


class EnhancedSQLEditor:
    """Enhanced SQL Editor with syntax highlighting, shortcuts, and improved UX."""
    
    def __init__(self, query_engine=None, db_connection=None):
        """Initialize the SQL editor."""
        self.query_engine = query_engine
        self.db_connection = db_connection
        self._init_session_state()
        
    def _init_session_state(self):
        """Initialize session state variables."""
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        if 'history_index' not in st.session_state:
            st.session_state.history_index = -1
        if 'favorite_queries' not in st.session_state:
            st.session_state.favorite_queries = []
        if 'editor_theme' not in st.session_state:
            st.session_state.editor_theme = 'monokai'
        if 'editor_font_size' not in st.session_state:
            st.session_state.editor_font_size = 14
        if 'show_line_numbers' not in st.session_state:
            st.session_state.show_line_numbers = True
        if 'schema_expanded' not in st.session_state:
            st.session_state.schema_expanded = True
        if 'fullscreen_mode' not in st.session_state:
            st.session_state.fullscreen_mode = False
            
    def render(self):
        """Render the complete SQL editor interface."""
        # Apply fullscreen mode if active
        if st.session_state.fullscreen_mode:
            self._render_fullscreen()
        else:
            self._render_normal()
            
    def _render_normal(self):
        """Render normal layout with resizable panes."""
        # Create main layout columns with responsive design
        if st.session_state.schema_expanded:
            col1, col2, col3 = st.columns([1.5, 4.5, 2], gap="small")
        else:
            col1, col2, col3 = st.columns([0.5, 5, 2], gap="small")
            
        # Schema Viewer (Left Sidebar)
        with col1:
            self._render_schema_viewer()
            
        # Main Editor Area (Center)
        with col2:
            self._render_editor_area()
            
        # Query History & Tools (Right Sidebar)
        with col3:
            self._render_tools_sidebar()
            
    def _render_fullscreen(self):
        """Render fullscreen editor mode."""
        # Exit fullscreen button
        if st.button("🔲 Exit Fullscreen", key="exit_fullscreen"):
            st.session_state.fullscreen_mode = False
            st.rerun()
            
        # Full width editor
        self._render_editor_area(fullscreen=True)
        
    def _render_schema_viewer(self):
        """Render the collapsible schema viewer."""
        st.markdown("### 📊 Schema")
        
        # Toggle button for expanding/collapsing
        if st.button("◀" if st.session_state.schema_expanded else "▶", 
                     key="toggle_schema",
                     help="Toggle schema viewer"):
            st.session_state.schema_expanded = not st.session_state.schema_expanded
            st.rerun()
            
        if st.session_state.schema_expanded:
            # Search box for schema
            schema_search = st.text_input("🔍 Search tables/columns", 
                                         key="schema_search",
                                         placeholder="Type to filter...")
            
            # Get tables from connection
            if self.db_connection and hasattr(st.session_state, 'registered_tables'):
                for table in st.session_state.registered_tables:
                    table_name = table['name']
                    
                    # Filter based on search
                    if schema_search and schema_search.lower() not in table_name.lower():
                        continue
                        
                    with st.expander(f"📋 {table_name}", expanded=False):
                        try:
                            table_info = self.db_connection.get_table_info(table_name)
                            
                            # Table stats on hover
                            st.caption(f"Rows: {table['rows']:,} | Cols: {table['columns']}")
                            
                            # Column details with type indicators
                            for col in table_info['columns']:
                                col_icon = self._get_type_icon(col['type'])
                                col_display = f"{col_icon} {col['name']}"
                                
                                # Make column draggable (simulated with copy button)
                                col_btn = st.button(
                                    col_display,
                                    key=f"col_{table_name}_{col['name']}",
                                    help=f"Type: {col['type']}",
                                    use_container_width=True
                                )
                                if col_btn:
                                    self._insert_to_editor(f"{table_name}.{col['name']}")
                                    
                        except Exception as e:
                            st.error(f"Error loading schema: {e}")
                            
            # Expand/Collapse all buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Expand All", key="expand_all", use_container_width=True):
                    pass  # Streamlit doesn't support programmatic expander control
            with col2:
                if st.button("➖ Collapse All", key="collapse_all", use_container_width=True):
                    pass
                    
    def _render_editor_area(self, fullscreen=False):
        """Render the main SQL editor area."""
        # Toolbar
        self._render_toolbar()
        
        # SQL Editor with syntax highlighting if available
        editor_height = 500 if fullscreen else 300
        current_sql = st.session_state.get('editor_sql', '')
        
        if HAS_ACE:
            try:
                # Use streamlit-ace for syntax highlighting
                sql_code = st_ace.st_ace(
                    value=current_sql,
                    language='sql',
                    theme=st.session_state.editor_theme,
                    key='sql_editor_ace',
                    font_size=st.session_state.editor_font_size,
                    show_gutter=st.session_state.show_line_numbers,
                    show_print_margin=True,
                    wrap=False,
                    auto_update=False,
                    annotations=None,
                    height=editor_height
                )
                st.session_state.editor_sql = sql_code
                
            except Exception as e:
                # Fallback to standard text area if ACE editor fails
                logger.warning(f"ACE editor failed, falling back to text area: {e}")
                sql_code = st.text_area(
                    "SQL Query",
                    value=current_sql,
                    height=editor_height,
                    key="sql_editor_fallback",
                    placeholder="Enter your SQL query here..."
                )
                st.session_state.editor_sql = sql_code
        else:
            # Use standard text area if ACE is not available
            sql_code = st.text_area(
                "SQL Query",
                value=current_sql,
                height=editor_height,
                key="sql_editor_standard",
                placeholder="Enter your SQL query here...\n\nTip: Install streamlit-ace for syntax highlighting"
            )
            st.session_state.editor_sql = sql_code
            
        # Status bar
        self._render_status_bar()
        
        # Keyboard shortcuts handler
        self._setup_keyboard_shortcuts()
        
        return sql_code
        
    def _render_toolbar(self):
        """Render the editor toolbar."""
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            if st.button("▶️ Execute", key="execute_btn", 
                        help="Ctrl/Cmd + Enter", 
                        type="primary",
                        use_container_width=True):
                self._execute_query()
                
        with col2:
            if st.button("💾 Save", key="save_btn", 
                        help="Ctrl/Cmd + S",
                        use_container_width=True):
                self._save_query()
                
        with col3:
            if st.button("📋 Format", key="format_btn", 
                        help="Ctrl/Cmd + Shift + F",
                        use_container_width=True):
                self._format_query()
                
        with col4:
            if st.button("📑 Copy", key="copy_btn",
                        use_container_width=True):
                self._copy_to_clipboard()
                
        with col5:
            if st.button("🕐 History", key="history_btn",
                        use_container_width=True):
                self._show_history()
                
        with col6:
            if st.button("⛶ Fullscreen", key="fullscreen_btn",
                        use_container_width=True):
                st.session_state.fullscreen_mode = True
                st.rerun()
                
    def _render_status_bar(self):
        """Render the status bar below editor."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Cursor position (simulated)
            st.caption("Line 1, Col 1")
            
        with col2:
            # Last query execution time
            if hasattr(st.session_state, 'execution_time'):
                st.caption(f"Last query: {st.session_state.execution_time:.3f}s")
            else:
                st.caption("No queries executed")
                
        with col3:
            # Row count from last result
            if hasattr(st.session_state, 'query_result') and st.session_state.query_result is not None:
                st.caption(f"Rows: {len(st.session_state.query_result):,}")
            else:
                st.caption("No results")
                
        with col4:
            # Editor theme selector
            theme = st.selectbox(
                "Theme",
                ["monokai", "github", "tomorrow", "twilight", "solarized_dark", "solarized_light"],
                key="theme_selector",
                label_visibility="collapsed"
            )
            st.session_state.editor_theme = theme
            
    def _render_tools_sidebar(self):
        """Render the right sidebar with history and tools."""
        tab1, tab2, tab3 = st.tabs(["📜 History", "⭐ Favorites", "⚙️ Settings"])
        
        with tab1:
            self._render_query_history()
            
        with tab2:
            self._render_favorite_queries()
            
        with tab3:
            self._render_editor_settings()
            
    def _render_query_history(self):
        """Render query history with search and filter."""
        st.markdown("#### Query History")
        
        # Search in history
        history_search = st.text_input("Search history", 
                                       placeholder="Filter queries...",
                                       key="history_search")
        
        # Display history (newest first)
        if st.session_state.query_history:
            for i, item in enumerate(reversed(st.session_state.query_history[-20:])):
                # Filter based on search
                if history_search and history_search.lower() not in item['query'].lower():
                    continue
                    
                with st.expander(f"🕐 {item['timestamp']}", expanded=False):
                    st.code(item['query'], language='sql')
                    st.caption(f"Execution time: {item.get('execution_time', 'N/A')}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📋", key=f"use_history_{i}", 
                                   help="Use this query"):
                            st.session_state.editor_sql = item['query']
                            st.rerun()
                    with col2:
                        if st.button("⭐", key=f"fav_history_{i}",
                                   help="Add to favorites"):
                            self._add_to_favorites(item['query'])
                    with col3:
                        if st.button("🗑️", key=f"del_history_{i}",
                                   help="Remove from history"):
                            self._remove_from_history(i)
        else:
            st.info("No query history yet")
            
        # Export/Import history
        if st.button("💾 Export History", key="export_history"):
            self._export_history()
            
    def _render_favorite_queries(self):
        """Render favorite queries section."""
        st.markdown("#### Favorite Queries")
        
        # Add current query to favorites
        if st.button("⭐ Add Current Query", key="add_current_fav",
                    use_container_width=True):
            if hasattr(st.session_state, 'editor_sql') and st.session_state.editor_sql:
                self._add_to_favorites(st.session_state.editor_sql)
                
        # Display favorites
        if st.session_state.favorite_queries:
            for i, fav in enumerate(st.session_state.favorite_queries):
                with st.expander(f"⭐ {fav.get('name', f'Query {i+1}')}", expanded=False):
                    st.code(fav['query'], language='sql')
                    
                    # Name input for favorite
                    new_name = st.text_input("Name", 
                                            value=fav.get('name', ''),
                                            key=f"fav_name_{i}")
                    if new_name != fav.get('name', ''):
                        st.session_state.favorite_queries[i]['name'] = new_name
                        
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Use", key=f"use_fav_{i}",
                                   use_container_width=True):
                            st.session_state.editor_sql = fav['query']
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Remove", key=f"del_fav_{i}",
                                   use_container_width=True):
                            st.session_state.favorite_queries.pop(i)
                            st.rerun()
        else:
            st.info("No favorite queries saved")
            
    def _render_editor_settings(self):
        """Render editor settings."""
        st.markdown("#### Editor Settings")
        
        # Font size
        font_size = st.slider("Font Size", 10, 24, 
                             st.session_state.editor_font_size,
                             key="font_size_slider")
        st.session_state.editor_font_size = font_size
        
        # Show line numbers
        show_lines = st.checkbox("Show Line Numbers",
                                 value=st.session_state.show_line_numbers,
                                 key="show_lines_check")
        st.session_state.show_line_numbers = show_lines
        
        # Auto-format on paste
        st.checkbox("Auto-format on paste", key="auto_format_paste")
        
        # Keyboard shortcuts reference
        st.markdown("#### Keyboard Shortcuts")
        shortcuts = [
            ("Execute Query", "Ctrl/Cmd + Enter"),
            ("Save Query", "Ctrl/Cmd + S"),
            ("Format Query", "Ctrl/Cmd + Shift + F"),
            ("Comment/Uncomment", "Ctrl/Cmd + /"),
            ("Duplicate Line", "Ctrl/Cmd + D"),
            ("Find", "Ctrl/Cmd + F"),
            ("Find & Replace", "Ctrl/Cmd + H"),
            ("Undo", "Ctrl/Cmd + Z"),
            ("Redo", "Ctrl/Cmd + Y"),
            ("Refresh Schema", "F5")
        ]
        
        for shortcut, keys in shortcuts:
            st.caption(f"**{shortcut}**: {keys}")
            
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts handling."""
        # Note: Keyboard shortcuts will be handled via JavaScript in the frontend
        # This is a placeholder for future implementation
        pass
            
    def _execute_query(self):
        """Execute the current SQL query."""
        if self.query_engine and hasattr(st.session_state, 'editor_sql'):
            sql = st.session_state.editor_sql
            if sql and sql.strip():
                try:
                    start_time = time.time()
                    result = self.query_engine.execute_query(sql)
                    execution_time = time.time() - start_time
                    
                    # Store results
                    st.session_state.query_result = result
                    st.session_state.execution_time = execution_time
                    
                    # Add to history
                    self._add_to_history(sql, execution_time)
                    
                    st.success(f"✅ Query executed in {execution_time:.3f}s")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Query failed: {e}")
                    
    def _save_query(self):
        """Save current query to favorites."""
        if hasattr(st.session_state, 'editor_sql') and st.session_state.editor_sql:
            self._add_to_favorites(st.session_state.editor_sql)
            st.success("✅ Query saved to favorites")
            
    def _format_query(self):
        """Format the SQL query."""
        if hasattr(st.session_state, 'editor_sql') and st.session_state.editor_sql:
            formatted = self._format_sql(st.session_state.editor_sql)
            st.session_state.editor_sql = formatted
            st.rerun()
            
    def _format_sql(self, sql: str) -> str:
        """Format SQL query with proper indentation and capitalization."""
        if HAS_SQLPARSE:
            # Use sqlparse for professional formatting
            return sqlparse.format(
                sql,
                reindent=True,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=False,
                indent_width=4,
                wrap_after=80
            )
        else:
            # Basic SQL formatting fallback
            # Capitalize keywords
            for keyword in SQL_KEYWORDS | DUCKDB_KEYWORDS:
                sql = re.sub(r'\b' + keyword + r'\b', keyword, sql, flags=re.IGNORECASE)
                
            # Add newlines before major clauses
            clauses = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT']
            for clause in clauses:
                sql = re.sub(r'\s+' + clause + r'\s+', f'\n{clause} ', sql, flags=re.IGNORECASE)
                
            # Indent sub-clauses
            lines = sql.split('\n')
            formatted_lines = []
            indent_level = 0
            
            for line in lines:
                line = line.strip()
                if line.upper().startswith(('SELECT', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT')):
                    formatted_lines.append(line)
                    indent_level = 1
                elif line.upper().startswith(('AND', 'OR')):
                    formatted_lines.append('    ' + line)
                else:
                    formatted_lines.append('    ' * indent_level + line if indent_level > 0 else line)
                    
            return '\n'.join(formatted_lines)
        
    def _copy_to_clipboard(self):
        """Copy SQL to clipboard."""
        if hasattr(st.session_state, 'editor_sql') and st.session_state.editor_sql:
            # Streamlit doesn't have native clipboard support
            # Show the SQL for manual copying
            st.code(st.session_state.editor_sql, language='sql')
            st.info("📋 SQL displayed above - use Ctrl/Cmd+C to copy")
            
    def _show_history(self):
        """Navigate through query history."""
        if st.session_state.query_history:
            # Move to previous query in history
            if st.session_state.history_index > 0:
                st.session_state.history_index -= 1
            else:
                st.session_state.history_index = len(st.session_state.query_history) - 1
                
            query = st.session_state.query_history[st.session_state.history_index]['query']
            st.session_state.editor_sql = query
            st.rerun()
            
    def _refresh_schema(self):
        """Refresh schema information."""
        st.info("🔄 Refreshing schema...")
        st.rerun()
        
    def _insert_to_editor(self, text: str):
        """Insert text into the editor at cursor position."""
        current_sql = st.session_state.get('editor_sql', '')
        st.session_state.editor_sql = current_sql + ' ' + text if current_sql else text
        st.rerun()
        
    def _add_to_history(self, query: str, execution_time: float = None):
        """Add query to history."""
        history_item = {
            'query': query,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'execution_time': f"{execution_time:.3f}s" if execution_time else None
        }
        st.session_state.query_history.append(history_item)
        
        # Limit history size
        if len(st.session_state.query_history) > 100:
            st.session_state.query_history = st.session_state.query_history[-100:]
            
    def _remove_from_history(self, index: int):
        """Remove item from history."""
        if 0 <= index < len(st.session_state.query_history):
            st.session_state.query_history.pop(index)
            st.rerun()
            
    def _add_to_favorites(self, query: str):
        """Add query to favorites."""
        favorite = {
            'query': query,
            'name': f"Query {len(st.session_state.favorite_queries) + 1}",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state.favorite_queries.append(favorite)
        
    def _export_history(self):
        """Export query history to JSON."""
        if st.session_state.query_history:
            history_json = json.dumps(st.session_state.query_history, indent=2)
            st.download_button(
                "💾 Download History",
                history_json,
                "query_history.json",
                "application/json"
            )
            
    def _get_type_icon(self, data_type: str) -> str:
        """Get icon for data type."""
        type_icons = {
            'INTEGER': '🔢',
            'BIGINT': '🔢',
            'DOUBLE': '🔢',
            'DECIMAL': '🔢',
            'VARCHAR': '📝',
            'TEXT': '📝',
            'DATE': '📅',
            'TIMESTAMP': '⏰',
            'BOOLEAN': '✓',
            'ARRAY': '📚',
            'JSON': '{}',
        }
        
        for key, icon in type_icons.items():
            if key in data_type.upper():
                return icon
        return '📊'