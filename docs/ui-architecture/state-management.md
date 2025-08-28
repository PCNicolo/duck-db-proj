# State Management

## Store Structure

```
session_state/
├── chat/                      # Chat-related state
│   ├── history               # List of chat messages
│   ├── current_query         # Current user query
│   └── llm_context           # LLM conversation context
├── data/                      # Data-related state
│   ├── uploaded_files        # List of uploaded file paths
│   ├── registered_tables     # DuckDB table registry
│   ├── schemas              # Cached table schemas
│   └── query_cache          # Query result cache
├── ui/                        # UI-related state
│   ├── active_tab           # Current active tab/page
│   ├── sql_editor_content   # SQL editor text content
│   ├── selected_table       # Currently selected table
│   └── visualization_config # Visualization settings
├── auth/                      # Authentication state
│   ├── user_id              # Current user identifier
│   ├── session_token        # Session authentication token
│   └── permissions          # User permissions
└── config/                    # Runtime configuration
    ├── llm_settings         # LM-Studio settings
    ├── db_connection        # DuckDB connection object
    └── app_settings         # Application preferences
```

## State Management Template

```python
"""
State Management Module
Handles all session state operations for the application
"""

import streamlit as st
from typing import Any, Optional, Dict, List, Callable
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class StateManager:
    """Centralized state management for Streamlit application."""
    
    # State schema definition
    STATE_SCHEMA = {
        "chat": {
            "history": list,
            "current_query": str,
            "llm_context": dict
        },
        "data": {
            "uploaded_files": list,
            "registered_tables": dict,
            "schemas": dict,
            "query_cache": dict
        },
        "ui": {
            "active_tab": str,
            "sql_editor_content": str,
            "selected_table": str,
            "visualization_config": dict
        },
        "auth": {
            "user_id": str,
            "session_token": str,
            "permissions": list
        },
        "config": {
            "llm_settings": dict,
            "db_connection": object,
            "app_settings": dict
        }
    }
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize session state with default values."""
        if "initialized" not in st.session_state:
            # Set up initial state structure
            for category, schema in cls.STATE_SCHEMA.items():
                if category not in st.session_state:
                    st.session_state[category] = {}
                
                for key, type_hint in schema.items():
                    state_key = f"{category}.{key}"
                    if state_key not in st.session_state:
                        # Initialize with appropriate empty value
                        if type_hint == list:
                            st.session_state[state_key] = []
                        elif type_hint == dict:
                            st.session_state[state_key] = {}
                        elif type_hint == str:
                            st.session_state[state_key] = ""
                        else:
                            st.session_state[state_key] = None
            
            st.session_state.initialized = True
            logger.info("Session state initialized")
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get value from session state.
        
        Args:
            key: Dot-notation key (e.g., 'chat.history')
            default: Default value if key doesn't exist
        
        Returns:
            State value or default
        """
        return st.session_state.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        Set value in session state.
        
        Args:
            key: Dot-notation key (e.g., 'chat.history')
            value: Value to store
        """
        st.session_state[key] = value
        logger.debug(f"State updated: {key}")
    
    @staticmethod
    def append(key: str, value: Any) -> None:
        """
        Append value to a list in session state.
        
        Args:
            key: Dot-notation key for a list
            value: Value to append
        """
        if key not in st.session_state:
            st.session_state[key] = []
        
        if not isinstance(st.session_state[key], list):
            raise ValueError(f"State key {key} is not a list")
        
        st.session_state[key].append(value)
        logger.debug(f"Appended to {key}")
    
    @staticmethod
    def update_dict(key: str, updates: Dict[str, Any]) -> None:
        """
        Update a dictionary in session state.
        
        Args:
            key: Dot-notation key for a dict
            updates: Dictionary of updates to merge
        """
        if key not in st.session_state:
            st.session_state[key] = {}
        
        if not isinstance(st.session_state[key], dict):
            raise ValueError(f"State key {key} is not a dict")
        
        st.session_state[key].update(updates)
        logger.debug(f"Updated dict {key}")
    
    @staticmethod
    def clear(key: str) -> None:
        """Clear a specific state key."""
        if key in st.session_state:
            if isinstance(st.session_state[key], list):
                st.session_state[key] = []
            elif isinstance(st.session_state[key], dict):
                st.session_state[key] = {}
            elif isinstance(st.session_state[key], str):
                st.session_state[key] = ""
            else:
                st.session_state[key] = None
            logger.debug(f"Cleared {key}")
    
    @staticmethod
    def delete(key: str) -> None:
        """Remove a key from session state."""
        if key in st.session_state:
            del st.session_state[key]
            logger.debug(f"Deleted {key}")
    
    @classmethod
    def reset_category(cls, category: str) -> None:
        """Reset all state in a category to defaults."""
        if category in cls.STATE_SCHEMA:
            for key in cls.STATE_SCHEMA[category].keys():
                cls.clear(f"{category}.{key}")
            logger.info(f"Reset category: {category}")
    
    @classmethod
    def export_state(cls) -> Dict[str, Any]:
        """Export current state for debugging or persistence."""
        state_export = {}
        for key in st.session_state:
            if key != "initialized" and not key.startswith("_"):
                # Skip internal and private keys
                value = st.session_state[key]
                # Convert non-serializable objects to strings
                if hasattr(value, "__dict__"):
                    value = str(value)
                state_export[key] = value
        return state_export
    
    @classmethod
    def import_state(cls, state_data: Dict[str, Any]) -> None:
        """Import state from exported data."""
        for key, value in state_data.items():
            st.session_state[key] = value
        logger.info("State imported")


# Convenience functions for common operations

def add_chat_message(role: str, content: str) -> None:
    """Add a message to chat history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    StateManager.append("chat.history", message)


def cache_query_result(query: str, result: Any) -> None:
    """Cache a query result."""
    cache_entry = {
        "query": query,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    StateManager.update_dict("data.query_cache", {query: cache_entry})


def get_cached_result(query: str) -> Optional[Any]:
    """Get cached query result if exists."""
    cache = StateManager.get("data.query_cache", {})
    if query in cache:
        return cache[query].get("result")
    return None


def register_table(table_name: str, file_path: str, schema: Dict) -> None:
    """Register a new table in the system."""
    table_info = {
        "file_path": file_path,
        "registered_at": datetime.now().isoformat(),
        "row_count": schema.get("row_count", 0)
    }
    StateManager.update_dict("data.registered_tables", {table_name: table_info})
    StateManager.update_dict("data.schemas", {table_name: schema})


# State persistence helpers

def save_state_to_file(filepath: str) -> None:
    """Save current state to a JSON file."""
    state_data = StateManager.export_state()
    with open(filepath, 'w') as f:
        json.dump(state_data, f, indent=2, default=str)
    logger.info(f"State saved to {filepath}")


def load_state_from_file(filepath: str) -> None:
    """Load state from a JSON file."""
    with open(filepath, 'r') as f:
        state_data = json.load(f)
    StateManager.import_state(state_data)
    logger.info(f"State loaded from {filepath}")
```
