"""
Simplified chat interface for natural language to SQL conversion.
"""

import streamlit as st
from typing import Optional

class ChatInterface:
    """Manages the chat interface for SQL generation."""
    
    def __init__(self, sql_generator):
        self.sql_generator = sql_generator
    
    def render(self):
        """Render the chat interface."""
        st.markdown("### 💬 Chat Helper")
        
        # Check LM Studio availability
        if not self.sql_generator.is_available():
            st.warning("⚠️ LM Studio is not connected. Please ensure it's running on localhost:1234")
            return None
        
        # Natural language input
        user_query = st.text_area(
            "Describe what you want to query:",
            placeholder="Examples:\n• Show me total sales by month\n• Which products have the highest revenue?\n• List top 10 customers by order count",
            height=120,
            key="chat_input"
        )
        
        # Buttons
        col1, col2 = st.columns(2)
        
        with col1:
            generate_btn = st.button(
                "Generate SQL →",
                type="primary",
                use_container_width=True,
                help="Convert your description to SQL"
            )
        
        with col2:
            clear_btn = st.button(
                "Clear",
                use_container_width=True,
                help="Clear the input"
            )
        
        # Handle button clicks
        if generate_btn and user_query:
            return self.generate_sql(user_query)
        
        if clear_btn:
            st.session_state.chat_input = ""
            return ""
        
        return None
    
    def generate_sql(self, prompt: str) -> Optional[str]:
        """Generate SQL from natural language."""
        try:
            with st.spinner("🤔 Thinking..."):
                sql = self.sql_generator.generate_sql(prompt)
                
                if sql:
                    st.success("✅ SQL generated successfully!")
                    return sql
                else:
                    st.error("Could not generate SQL. Please try rephrasing your request.")
                    return None
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None
    
    def show_explanation(self, sql: str):
        """Show explanation for the generated SQL."""
        if sql:
            st.markdown("---")
            st.markdown("💡 **What this query does:**")
            
            # Simple explanation based on SQL keywords
            explanations = []
            
            if "SELECT" in sql.upper():
                if "COUNT" in sql.upper():
                    explanations.append("• Counts the number of records")
                if "SUM" in sql.upper():
                    explanations.append("• Calculates totals")
                if "AVG" in sql.upper():
                    explanations.append("• Computes averages")
                if "GROUP BY" in sql.upper():
                    explanations.append("• Groups results by categories")
                if "ORDER BY" in sql.upper():
                    explanations.append("• Sorts the results")
                if "WHERE" in sql.upper():
                    explanations.append("• Filters the data")
                if "JOIN" in sql.upper():
                    explanations.append("• Combines data from multiple tables")
            
            if explanations:
                for exp in explanations:
                    st.write(exp)
            else:
                st.write("This query retrieves data from your tables.")