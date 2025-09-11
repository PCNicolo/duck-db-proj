"""Configuration settings for LLM context enhancement."""

import os

# Environment variables for configuration
ENV_PREFIX = "DUCKDB_LLM_"


class LLMSettings:
    """Settings for LLM context and prompt engineering."""

    def __init__(self):
        """Initialize settings from environment or defaults."""
        # Schema extraction settings
        self.sample_rows = int(os.getenv(f"{ENV_PREFIX}SAMPLE_ROWS", "3"))
        self.max_tables_in_context = int(os.getenv(f"{ENV_PREFIX}MAX_TABLES", "10"))
        self.context_detail_level = os.getenv(f"{ENV_PREFIX}CONTEXT_LEVEL", "standard")
        self.include_sample_data = (
            os.getenv(f"{ENV_PREFIX}INCLUDE_SAMPLES", "true").lower() == "true"
        )

        # Cache settings
        self.cache_enabled = (
            os.getenv(f"{ENV_PREFIX}CACHE_ENABLED", "true").lower() == "true"
        )
        self.cache_ttl_seconds = int(os.getenv(f"{ENV_PREFIX}CACHE_TTL", "3600"))
        self.warm_cache_on_startup = (
            os.getenv(f"{ENV_PREFIX}WARM_CACHE", "true").lower() == "true"
        )

        # Context window management
        self.max_context_tokens = int(
            os.getenv(f"{ENV_PREFIX}MAX_CONTEXT_TOKENS", "4000")
        )
        self.token_estimate_ratio = float(os.getenv(f"{ENV_PREFIX}TOKEN_RATIO", "1.5"))

        # Query validation
        self.validate_generated_sql = (
            os.getenv(f"{ENV_PREFIX}VALIDATE_SQL", "true").lower() == "true"
        )
        self.suggest_improvements = (
            os.getenv(f"{ENV_PREFIX}SUGGEST_IMPROVEMENTS", "true").lower() == "true"
        )
        self.auto_add_limit = (
            os.getenv(f"{ENV_PREFIX}AUTO_ADD_LIMIT", "true").lower() == "true"
        )
        self.default_limit = int(os.getenv(f"{ENV_PREFIX}DEFAULT_LIMIT", "100"))

        # Debug settings
        self.debug_mode = os.getenv(f"{ENV_PREFIX}DEBUG", "false").lower() == "true"
        self.log_prompts = (
            os.getenv(f"{ENV_PREFIX}LOG_PROMPTS", "false").lower() == "true"
        )
        self.log_query_execution = (
            os.getenv(f"{ENV_PREFIX}LOG_QUERIES", "true").lower() == "true"
        )

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "sample_rows": self.sample_rows,
            "max_tables_in_context": self.max_tables_in_context,
            "context_detail_level": self.context_detail_level,
            "include_sample_data": self.include_sample_data,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "warm_cache_on_startup": self.warm_cache_on_startup,
            "max_context_tokens": self.max_context_tokens,
            "token_estimate_ratio": self.token_estimate_ratio,
            "validate_generated_sql": self.validate_generated_sql,
            "suggest_improvements": self.suggest_improvements,
            "auto_add_limit": self.auto_add_limit,
            "default_limit": self.default_limit,
            "debug_mode": self.debug_mode,
            "log_prompts": self.log_prompts,
            "log_query_execution": self.log_query_execution,
        }

    def update_from_dict(self, config: dict):
        """Update settings from dictionary."""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate settings."""
        errors = []

        # Validate context level
        valid_levels = ["minimal", "standard", "comprehensive"]
        if self.context_detail_level not in valid_levels:
            errors.append(
                f"Invalid context_detail_level: {self.context_detail_level}. Must be one of {valid_levels}"
            )

        # Validate numeric ranges
        if self.sample_rows < 0 or self.sample_rows > 100:
            errors.append(
                f"sample_rows must be between 0 and 100, got {self.sample_rows}"
            )

        if self.max_tables_in_context < 1 or self.max_tables_in_context > 100:
            errors.append(
                f"max_tables_in_context must be between 1 and 100, got {self.max_tables_in_context}"
            )

        if self.max_context_tokens < 100 or self.max_context_tokens > 100000:
            errors.append(
                f"max_context_tokens must be between 100 and 100000, got {self.max_context_tokens}"
            )

        if self.cache_ttl_seconds < 0:
            errors.append(
                f"cache_ttl_seconds must be non-negative, got {self.cache_ttl_seconds}"
            )

        if self.default_limit < 1 or self.default_limit > 10000:
            errors.append(
                f"default_limit must be between 1 and 10000, got {self.default_limit}"
            )

        return len(errors) == 0, errors


# Global settings instance
settings = LLMSettings()
