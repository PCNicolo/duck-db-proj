"""Performance utilities for LLM context management."""

import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def timer_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    
    return wrapper


class PerformanceMetrics:
    """Collect and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self._start_times: Dict[str, float] = {}
    
    def start_operation(self, operation: str) -> None:
        """Start timing an operation."""
        self._start_times[operation] = time.perf_counter()
    
    def end_operation(self, operation: str, metadata: Optional[Dict] = None) -> float:
        """End timing an operation and record metrics."""
        if operation not in self._start_times:
            logger.warning(f"Operation {operation} was not started")
            return 0.0
        
        elapsed = time.perf_counter() - self._start_times[operation]
        
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "metadata": []
            }
        
        stats = self.metrics[operation]
        stats["count"] += 1
        stats["total_time"] += elapsed
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], elapsed)
        stats["max_time"] = max(stats["max_time"], elapsed)
        
        if metadata:
            stats["metadata"].append({
                "time": elapsed,
                **metadata
            })
        
        del self._start_times[operation]
        return elapsed
    
    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary."""
        summary = {}
        for operation, stats in self.metrics.items():
            summary[operation] = {
                "count": stats["count"],
                "avg_time": f"{stats['avg_time']:.3f}s",
                "min_time": f"{stats['min_time']:.3f}s",
                "max_time": f"{stats['max_time']:.3f}s",
                "total_time": f"{stats['total_time']:.3f}s"
            }
        return summary
    
    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self._start_times.clear()


def calculate_content_hash(content: Any) -> str:
    """Calculate a hash for content to use as cache key."""
    if isinstance(content, dict):
        content_str = json.dumps(content, sort_keys=True)
    elif isinstance(content, (list, tuple)):
        content_str = json.dumps(list(content), sort_keys=True)
    else:
        content_str = str(content)
    
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]


def estimate_tokens_accurate(text: str, model_type: str = "llama") -> int:
    """
    More accurate token estimation based on model type.
    
    Args:
        text: Text to estimate tokens for
        model_type: Type of model (llama, gpt, etc.)
    
    Returns:
        Estimated token count
    """
    # Model-specific ratios based on empirical data
    token_ratios = {
        "llama": 3.5,  # characters per token for Llama models
        "gpt": 4.0,     # characters per token for GPT models
        "default": 3.75  # average
    }
    
    ratio = token_ratios.get(model_type, token_ratios["default"])
    
    # Account for special tokens and formatting
    # Add overhead for structure
    base_tokens = len(text) / ratio
    
    # Account for SQL-specific patterns
    sql_keywords = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY"]
    keyword_overhead = sum(1 for keyword in sql_keywords if keyword in text.upper()) * 2
    
    # Account for punctuation and special characters
    special_chars = sum(1 for char in text if char in "()[]{},.;:'\"")
    special_overhead = special_chars * 0.3
    
    return int(base_tokens + keyword_overhead + special_overhead)


class TokenBudgetManager:
    """Manage token budgets for different components."""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.allocations = {
            "system_prompt": 0.15,  # 15% for system prompt
            "query": 0.05,          # 5% for user query
            "schema": 0.60,         # 60% for schema context
            "examples": 0.10,       # 10% for examples
            "buffer": 0.10          # 10% safety buffer
        }
    
    def get_budget(self, component: str) -> int:
        """Get token budget for a component."""
        if component not in self.allocations:
            logger.warning(f"Unknown component: {component}")
            return 100
        
        return int(self.max_tokens * self.allocations[component])
    
    def adjust_budget(self, used_tokens: Dict[str, int]) -> Dict[str, int]:
        """Dynamically adjust budgets based on usage."""
        total_used = sum(used_tokens.values())
        remaining = self.max_tokens - total_used
        
        adjusted = {}
        for component, allocation in self.allocations.items():
            if component not in used_tokens:
                # Redistribute remaining tokens
                adjusted[component] = int(remaining * allocation)
            else:
                adjusted[component] = used_tokens[component]
        
        return adjusted


def batch_operations(items: list, batch_size: int = 10) -> list:
    """Split items into batches for processing."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


class CacheStats:
    """Track cache statistics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_size = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
    
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
    
    def record_eviction(self, size: int = 1):
        """Record cache eviction."""
        self.evictions += 1
        self.total_size -= size
    
    def record_addition(self, size: int = 1):
        """Record addition to cache."""
        self.total_size += size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.2%}",
            "evictions": self.evictions,
            "total_size": self.total_size
        }
    
    def reset(self):
        """Reset statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_size = 0