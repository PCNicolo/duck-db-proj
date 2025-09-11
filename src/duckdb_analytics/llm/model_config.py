"""
Advanced LLM Model Configuration System.

This module provides a flexible configuration system for different LLM models
and usage scenarios, with support for dynamic parameter adjustment.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported LLM providers."""
    LM_STUDIO = "lm_studio"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class GenerationMode(Enum):
    """SQL generation modes."""
    FAST = "fast"           # Quick responses, minimal thinking
    BALANCED = "balanced"   # Balance between speed and quality
    THOROUGH = "thorough"   # Comprehensive analysis
    CREATIVE = "creative"   # More creative/complex queries
    PRECISE = "precise"     # High precision, low temperature


@dataclass
class ModelProfile:
    """Configuration profile for a specific model."""
    
    # Model identification
    name: str
    provider: ModelProvider
    model_id: str
    
    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2000
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Timeout and performance
    request_timeout: float = 10.0
    feedback_timeout: float = 3.0
    stream_chunk_delay: float = 0.1  # Delay between streamed chunks
    
    # Context management
    max_context_tokens: int = 4000
    context_compression_ratio: float = 0.7  # Target compression when context is too large
    
    # Thinking pad configuration
    thinking_depth: str = "standard"  # minimal, standard, comprehensive
    show_confidence: bool = True
    show_alternatives: bool = False
    show_optimization_notes: bool = True
    
    # Advanced features
    use_few_shot: bool = True
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    use_chain_of_thought: bool = True
    use_self_reflection: bool = False
    
    # Caching
    cache_ttl: int = 3600  # Cache time-to-live in seconds
    cache_similar_queries: bool = True
    similarity_threshold: float = 0.85
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelProfile':
        """Create profile from dictionary."""
        # Handle enum conversion
        if isinstance(data.get('provider'), str):
            data['provider'] = ModelProvider(data['provider'])
        return cls(**data)


class ModelConfigManager:
    """Manages model configurations and profiles."""
    
    # Default profiles for different modes
    DEFAULT_PROFILES = {
        GenerationMode.FAST: {
            "temperature": 0.1,
            "max_tokens": 1000,
            "thinking_depth": "minimal",
            "request_timeout": 5.0,
            "use_chain_of_thought": False,
            "show_alternatives": False
        },
        GenerationMode.BALANCED: {
            "temperature": 0.3,
            "max_tokens": 2000,
            "thinking_depth": "standard",
            "request_timeout": 10.0,
            "use_chain_of_thought": True,
            "show_alternatives": False
        },
        GenerationMode.THOROUGH: {
            "temperature": 0.4,
            "max_tokens": 3000,
            "thinking_depth": "comprehensive",
            "request_timeout": 20.0,
            "use_chain_of_thought": True,
            "show_alternatives": True,
            "use_self_reflection": True
        },
        GenerationMode.CREATIVE: {
            "temperature": 0.7,
            "max_tokens": 2500,
            "thinking_depth": "comprehensive",
            "request_timeout": 15.0,
            "top_p": 0.9,
            "frequency_penalty": 0.2
        },
        GenerationMode.PRECISE: {
            "temperature": 0.0,
            "max_tokens": 2000,
            "thinking_depth": "standard",
            "request_timeout": 10.0,
            "top_p": 1.0,
            "use_chain_of_thought": True
        }
    }
    
    # Model-specific optimizations
    MODEL_OPTIMIZATIONS = {
        "llama": {
            "context_compression_ratio": 0.8,
            "stream_chunk_delay": 0.08,
            "max_context_tokens": 4096
        },
        "mistral": {
            "context_compression_ratio": 0.75,
            "stream_chunk_delay": 0.1,
            "max_context_tokens": 8192
        },
        "gpt": {
            "context_compression_ratio": 0.9,
            "stream_chunk_delay": 0.05,
            "max_context_tokens": 8192
        }
    }
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory for storing configuration files
        """
        self.config_dir = config_dir or Path.home() / ".duckdb_analytics" / "llm_configs"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles: Dict[str, ModelProfile] = {}
        self.active_profile: Optional[str] = None
        
        # Load saved configurations
        self._load_configurations()
        
        # Initialize with default profiles if none exist
        if not self.profiles:
            self._initialize_default_profiles()
    
    def _initialize_default_profiles(self):
        """Initialize default model profiles."""
        # LM Studio default profile
        self.profiles["lm_studio_default"] = ModelProfile(
            name="LM Studio Default",
            provider=ModelProvider.LM_STUDIO,
            model_id="meta-llama-3.1-8b-instruct",
            **self.DEFAULT_PROFILES[GenerationMode.BALANCED]
        )
        
        # Add few-shot examples for better SQL generation
        self.profiles["lm_studio_default"].few_shot_examples = [
            {
                "query": "show me all customers",
                "sql": "SELECT * FROM customers LIMIT 100;"
            },
            {
                "query": "total sales by month",
                "sql": "SELECT DATE_TRUNC('month', sale_date) as month, SUM(amount) as total_sales FROM sales GROUP BY month ORDER BY month;"
            },
            {
                "query": "top 5 products by revenue",
                "sql": "SELECT product_name, SUM(quantity * price) as revenue FROM order_items GROUP BY product_name ORDER BY revenue DESC LIMIT 5;"
            }
        ]
        
        # Save default profiles
        self.save_profile("lm_studio_default")
    
    def create_profile(
        self,
        name: str,
        provider: ModelProvider,
        model_id: str,
        mode: GenerationMode = GenerationMode.BALANCED,
        **kwargs
    ) -> ModelProfile:
        """
        Create a new model profile.
        
        Args:
            name: Profile name
            provider: Model provider
            model_id: Model identifier
            mode: Generation mode for base settings
            **kwargs: Additional profile parameters
            
        Returns:
            Created ModelProfile
        """
        # Start with mode defaults
        base_config = self.DEFAULT_PROFILES.get(mode, {}).copy()
        
        # Apply model-specific optimizations
        for model_key, optimizations in self.MODEL_OPTIMIZATIONS.items():
            if model_key.lower() in model_id.lower():
                base_config.update(optimizations)
                break
        
        # Apply custom parameters
        base_config.update(kwargs)
        
        # Create profile
        profile = ModelProfile(
            name=name,
            provider=provider,
            model_id=model_id,
            **base_config
        )
        
        self.profiles[name] = profile
        return profile
    
    def get_profile(self, name: str) -> Optional[ModelProfile]:
        """Get a specific profile."""
        return self.profiles.get(name)
    
    def get_active_profile(self) -> Optional[ModelProfile]:
        """Get the currently active profile."""
        if self.active_profile:
            return self.profiles.get(self.active_profile)
        # Return default if no active profile
        return self.profiles.get("lm_studio_default")
    
    def set_active_profile(self, name: str) -> bool:
        """Set the active profile."""
        if name in self.profiles:
            self.active_profile = name
            logger.info(f"Active profile set to: {name}")
            return True
        logger.warning(f"Profile not found: {name}")
        return False
    
    def update_profile(self, name: str, **kwargs) -> bool:
        """
        Update an existing profile.
        
        Args:
            name: Profile name
            **kwargs: Parameters to update
            
        Returns:
            True if successful
        """
        if name not in self.profiles:
            logger.warning(f"Profile not found: {name}")
            return False
        
        profile = self.profiles[name]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
            else:
                logger.warning(f"Unknown profile attribute: {key}")
        
        self.save_profile(name)
        return True
    
    def optimize_for_latency(self, profile_name: str) -> bool:
        """
        Optimize a profile for minimum latency.
        
        Args:
            profile_name: Profile to optimize
            
        Returns:
            True if successful
        """
        if profile_name not in self.profiles:
            return False
        
        profile = self.profiles[profile_name]
        
        # Latency optimizations
        profile.temperature = 0.1
        profile.max_tokens = min(profile.max_tokens, 1000)
        profile.thinking_depth = "minimal"
        profile.request_timeout = 5.0
        profile.feedback_timeout = 1.0
        profile.stream_chunk_delay = 0.05
        profile.use_chain_of_thought = False
        profile.use_self_reflection = False
        profile.show_alternatives = False
        
        self.save_profile(profile_name)
        logger.info(f"Profile '{profile_name}' optimized for latency")
        return True
    
    def optimize_for_quality(self, profile_name: str) -> bool:
        """
        Optimize a profile for maximum quality.
        
        Args:
            profile_name: Profile to optimize
            
        Returns:
            True if successful
        """
        if profile_name not in self.profiles:
            return False
        
        profile = self.profiles[profile_name]
        
        # Quality optimizations
        profile.temperature = 0.3
        profile.max_tokens = 3000
        profile.thinking_depth = "comprehensive"
        profile.request_timeout = 30.0
        profile.feedback_timeout = 5.0
        profile.use_chain_of_thought = True
        profile.use_self_reflection = True
        profile.show_alternatives = True
        profile.show_optimization_notes = True
        
        self.save_profile(profile_name)
        logger.info(f"Profile '{profile_name}' optimized for quality")
        return True
    
    def save_profile(self, name: str) -> bool:
        """Save a profile to disk."""
        if name not in self.profiles:
            return False
        
        profile = self.profiles[name]
        profile_path = self.config_dir / f"{name}.json"
        
        try:
            profile_dict = profile.to_dict()
            # Convert enums to strings for JSON serialization
            if isinstance(profile_dict.get('provider'), ModelProvider):
                profile_dict['provider'] = profile_dict['provider'].value
            
            with open(profile_path, 'w') as f:
                json.dump(profile_dict, f, indent=2)
            
            logger.info(f"Profile saved: {profile_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            return False
    
    def load_profile(self, name: str) -> Optional[ModelProfile]:
        """Load a profile from disk."""
        profile_path = self.config_dir / f"{name}.json"
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r') as f:
                profile_dict = json.load(f)
            
            profile = ModelProfile.from_dict(profile_dict)
            self.profiles[name] = profile
            return profile
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            return None
    
    def _load_configurations(self):
        """Load all saved configurations."""
        for profile_path in self.config_dir.glob("*.json"):
            name = profile_path.stem
            self.load_profile(name)
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        return list(self.profiles.keys())
    
    def export_profile(self, name: str, export_path: Path) -> bool:
        """Export a profile to a file."""
        if name not in self.profiles:
            return False
        
        profile = self.profiles[name]
        
        try:
            with open(export_path, 'w') as f:
                if export_path.suffix == '.yaml':
                    yaml.dump(profile.to_dict(), f, default_flow_style=False)
                else:
                    json.dump(profile.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return False
    
    def import_profile(self, import_path: Path, name: Optional[str] = None) -> Optional[str]:
        """Import a profile from a file."""
        try:
            with open(import_path, 'r') as f:
                if import_path.suffix == '.yaml':
                    profile_dict = yaml.safe_load(f)
                else:
                    profile_dict = json.load(f)
            
            profile = ModelProfile.from_dict(profile_dict)
            
            # Use provided name or generate from file
            profile_name = name or import_path.stem
            profile.name = profile_name
            
            self.profiles[profile_name] = profile
            self.save_profile(profile_name)
            
            return profile_name
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None


class AdaptiveModelSelector:
    """
    Selects the best model/profile based on query characteristics.
    """
    
    def __init__(self, config_manager: ModelConfigManager):
        self.config_manager = config_manager
        
        # Query patterns to mode mapping
        self.pattern_modes = {
            "simple_select": GenerationMode.FAST,
            "complex_join": GenerationMode.THOROUGH,
            "aggregation": GenerationMode.BALANCED,
            "time_series": GenerationMode.THOROUGH,
            "creative": GenerationMode.CREATIVE
        }
    
    def select_profile(self, query: str, schema_complexity: int) -> ModelProfile:
        """
        Select the best profile for a given query.
        
        Args:
            query: Natural language query
            schema_complexity: Number of tables in schema
            
        Returns:
            Selected ModelProfile
        """
        # Analyze query characteristics
        query_lower = query.lower()
        
        # Determine query type
        if any(word in query_lower for word in ["all", "everything", "show me", "list"]):
            mode = GenerationMode.FAST
        elif any(word in query_lower for word in ["join", "combine", "relate", "together"]):
            mode = GenerationMode.THOROUGH
        elif any(word in query_lower for word in ["trend", "over time", "by month", "by year"]):
            mode = GenerationMode.THOROUGH
        elif any(word in query_lower for word in ["creative", "interesting", "insights"]):
            mode = GenerationMode.CREATIVE
        elif any(word in query_lower for word in ["exact", "precise", "specific"]):
            mode = GenerationMode.PRECISE
        else:
            mode = GenerationMode.BALANCED
        
        # Adjust based on schema complexity
        if schema_complexity > 20 and mode == GenerationMode.FAST:
            mode = GenerationMode.BALANCED
        elif schema_complexity > 50:
            mode = GenerationMode.THOROUGH
        
        # Find profile with matching mode
        for name, profile in self.config_manager.profiles.items():
            if profile.thinking_depth == self._mode_to_depth(mode):
                return profile
        
        # Fallback to active profile
        return self.config_manager.get_active_profile()
    
    def _mode_to_depth(self, mode: GenerationMode) -> str:
        """Convert generation mode to thinking depth."""
        mode_depth_map = {
            GenerationMode.FAST: "minimal",
            GenerationMode.BALANCED: "standard",
            GenerationMode.THOROUGH: "comprehensive",
            GenerationMode.CREATIVE: "comprehensive",
            GenerationMode.PRECISE: "standard"
        }
        return mode_depth_map.get(mode, "standard")