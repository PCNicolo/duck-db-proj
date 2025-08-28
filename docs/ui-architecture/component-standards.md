# Component Standards

## Component Template

```python
"""
Component: [Component Name]
Purpose: [Brief description of what this component does]
Usage: [How to use this component in the app]
"""

import streamlit as st
from typing import Optional, Dict, Any, List
import logging

# Configure logging for this component
logger = logging.getLogger(__name__)


class ComponentNameError(Exception):
    """Custom exception for this component."""
    pass


def render_component_name(
    key: str,
    initial_state: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Optional[Any]:
    """
    Render the [Component Name] component.
    
    Args:
        key: Unique key for this component instance
        initial_state: Initial state values for the component
        config: Configuration options for the component
        **kwargs: Additional arguments passed to Streamlit components
    
    Returns:
        Component output value or None
    
    Raises:
        ComponentNameError: If component encounters an error
    """
    # Initialize component state if not exists
    if f"{key}_state" not in st.session_state:
        st.session_state[f"{key}_state"] = initial_state or {}
    
    # Apply default configuration
    config = config or {}
    default_config = {
        "title": "Component Title",
        "show_border": True,
        "expanded": True
    }
    config = {**default_config, **config}
    
    # Component container with consistent styling
    with st.container():
        if config.get("show_border"):
            st.markdown("---")
        
        # Component header
        if config.get("title"):
            st.subheader(config["title"])
        
        # Component implementation
        try:
            # Example: Create a form or input section
            with st.form(key=f"{key}_form"):
                # Add your component UI elements here
                user_input = st.text_input(
                    "Input Label",
                    key=f"{key}_input",
                    placeholder="Enter value..."
                )
                
                submitted = st.form_submit_button("Submit")
                
                if submitted and user_input:
                    # Process input and update state
                    st.session_state[f"{key}_state"]["last_input"] = user_input
                    st.success(f"Processed: {user_input}")
                    return user_input
        
        except Exception as e:
            logger.error(f"Error in {key}: {str(e)}")
            st.error(f"Component error: {str(e)}")
            raise ComponentNameError(f"Failed to render component: {str(e)}")
    
    return None


# Helper functions for this component
def validate_input(value: str) -> bool:
    """Validate component input."""
    return bool(value and len(value) > 0)


def format_output(data: Any) -> str:
    """Format component output for display."""
    return str(data)


# Component-specific styling
def apply_component_styles():
    """Apply custom CSS styles for this component."""
    st.markdown("""
    <style>
    /* Component-specific styles */
    .component-container {
        padding: 1rem;
        border-radius: 0.5rem;
        background: var(--background-color);
    }
    </style>
    """, unsafe_allow_html=True)
```

## Naming Conventions

### File Naming
- **Components**: `snake_case.py` (e.g., `chat_interface.py`, `sql_editor.py`)
- **Pages**: `[number]_[emoji]_[Name].py` (e.g., `1_📊_Analytics.py`)
- **Services**: `[domain]_service.py` (e.g., `llm_service.py`, `duckdb_service.py`)
- **Utils**: `[function]_[type].py` (e.g., `session_state.py`, `validators.py`)
- **Config**: `[scope]_config.py` (e.g., `app_config.py`, `llm_config.py`)

### Python Naming
- **Classes**: `PascalCase` (e.g., `ChatInterface`, `SQLEditor`)
- **Functions**: `snake_case` (e.g., `render_chat_interface`, `process_query`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_MODEL`)
- **Private methods**: `_leading_underscore` (e.g., `_validate_input`)
- **Session state keys**: `component_key_property` (e.g., `chat_history`, `sql_editor_content`)

### Streamlit-Specific
- **Widget keys**: `{component}_{widget}_{identifier}` (e.g., `chat_input_main`, `sql_editor_query_1`)
- **Form keys**: `{component}_form` (e.g., `upload_form`, `query_form`)
- **Container keys**: `{component}_container` (e.g., `results_container`)
- **Placeholder keys**: `{component}_placeholder` (e.g., `status_placeholder`)

### Component Organization
- Each component should be self-contained with its own state management
- Components should expose a single `render_` function as the main entry point
- Helper functions should be prefixed with component context
- Error handling should use component-specific exception classes
- Logging should use component-specific logger instances
