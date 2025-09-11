"""Advanced multi-level schema caching system."""

import json
import logging
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .performance_utils import (
    CacheStats,
    PerformanceMetrics,
    calculate_content_hash,
    timer_decorator,
)
from .schema_extractor import TableSchema

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    
    key: str
    data: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0
    size_bytes: int = 0
    ttl: Optional[int] = None
    
    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Check if cache entry has expired."""
        if self.ttl is None:
            return False
        
        current_time = current_time or time.time()
        return (current_time - self.timestamp) > self.ttl
    
    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_access = time.time()


class MultiLevelCache:
    """Multi-level caching system with LRU eviction."""
    
    def __init__(
        self,
        max_memory_mb: int = 100,
        cache_dir: Optional[Path] = None,
        default_ttl: int = 3600
    ):
        """
        Initialize multi-level cache.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            cache_dir: Directory for disk cache
            default_ttl: Default TTL in seconds
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache_dir = cache_dir or Path.home() / ".duckdb_llm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        
        # Different cache levels
        self.l1_cache: Dict[str, CacheEntry] = {}  # Hot cache (most frequently accessed)
        self.l2_cache: Dict[str, CacheEntry] = {}  # Warm cache
        self.l3_disk_index: Dict[str, str] = {}    # Disk cache index
        
        self.stats = CacheStats()
        self.metrics = PerformanceMetrics()
        
        # Cache configuration
        self.l1_max_items = 50
        self.l2_max_items = 200
        self.promotion_threshold = 3  # Accesses before promotion
        
        self._load_disk_index()
    
    def _load_disk_index(self):
        """Load disk cache index."""
        index_file = self.cache_dir / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    self.l3_disk_index = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load disk cache index: {e}")
                self.l3_disk_index = {}
    
    def _save_disk_index(self):
        """Save disk cache index."""
        index_file = self.cache_dir / "cache_index.json"
        try:
            with open(index_file, 'w') as f:
                json.dump(self.l3_disk_index, f)
        except Exception as e:
            logger.warning(f"Could not save disk cache index: {e}")
    
    @timer_decorator
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache with multi-level lookup.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None
        """
        self.metrics.start_operation("cache_get")
        
        # Check L1 (hot cache)
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not entry.is_expired():
                entry.touch()
                self.stats.record_hit()
                self.metrics.end_operation("cache_get", {"level": "L1"})
                return entry.data
            else:
                del self.l1_cache[key]
        
        # Check L2 (warm cache)
        if key in self.l2_cache:
            entry = self.l2_cache[key]
            if not entry.is_expired():
                entry.touch()
                self.stats.record_hit()
                
                # Promote to L1 if frequently accessed
                if entry.access_count >= self.promotion_threshold:
                    self._promote_to_l1(key, entry)
                
                self.metrics.end_operation("cache_get", {"level": "L2"})
                return entry.data
            else:
                del self.l2_cache[key]
        
        # Check L3 (disk cache)
        if key in self.l3_disk_index:
            data = self._load_from_disk(key)
            if data is not None:
                self.stats.record_hit()
                # Promote to L2
                self._add_to_l2(key, data)
                self.metrics.end_operation("cache_get", {"level": "L3"})
                return data
        
        self.stats.record_miss()
        self.metrics.end_operation("cache_get", {"level": "miss"})
        return None
    
    @timer_decorator
    def set(
        self,
        key: str,
        data: Any,
        ttl: Optional[int] = None,
        cache_level: int = 2
    ) -> None:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds
            cache_level: Initial cache level (1=hot, 2=warm, 3=disk)
        """
        self.metrics.start_operation("cache_set")
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(data))
        except Exception:
            size_bytes = 1000  # Default size if serialization fails
        
        entry = CacheEntry(
            key=key,
            data=data,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl,
            size_bytes=size_bytes
        )
        
        if cache_level == 1:
            self._add_to_l1(key, entry)
        elif cache_level == 2:
            self._add_to_l2(key, entry)
        else:
            self._save_to_disk(key, data)
        
        self.stats.record_addition(size_bytes)
        self.metrics.end_operation("cache_set", {"level": f"L{cache_level}"})
    
    def _add_to_l1(self, key: str, entry: CacheEntry):
        """Add entry to L1 cache with eviction if needed."""
        if len(self.l1_cache) >= self.l1_max_items:
            self._evict_lru_from_l1()
        
        self.l1_cache[key] = entry
    
    def _add_to_l2(self, key: str, data: Any):
        """Add entry to L2 cache."""
        if len(self.l2_cache) >= self.l2_max_items:
            self._evict_lru_from_l2()
        
        entry = CacheEntry(
            key=key,
            data=data,
            timestamp=time.time(),
            ttl=self.default_ttl
        )
        self.l2_cache[key] = entry
    
    def _promote_to_l1(self, key: str, entry: CacheEntry):
        """Promote entry from L2 to L1."""
        # Remove from L2
        if key in self.l2_cache:
            del self.l2_cache[key]
        
        # Add to L1
        self._add_to_l1(key, entry)
    
    def _evict_lru_from_l1(self):
        """Evict least recently used item from L1."""
        if not self.l1_cache:
            return
        
        # Find LRU item
        lru_key = min(
            self.l1_cache.keys(),
            key=lambda k: self.l1_cache[k].last_access
        )
        
        # Move to L2
        entry = self.l1_cache[lru_key]
        del self.l1_cache[lru_key]
        self._add_to_l2(lru_key, entry.data)
        
        self.stats.record_eviction(entry.size_bytes)
    
    def _evict_lru_from_l2(self):
        """Evict least recently used item from L2."""
        if not self.l2_cache:
            return
        
        # Find LRU item
        lru_key = min(
            self.l2_cache.keys(),
            key=lambda k: self.l2_cache[k].last_access
        )
        
        # Move to disk
        entry = self.l2_cache[lru_key]
        del self.l2_cache[lru_key]
        self._save_to_disk(lru_key, entry.data)
        
        self.stats.record_eviction(entry.size_bytes)
    
    def _save_to_disk(self, key: str, data: Any):
        """Save data to disk cache."""
        file_path = self.cache_dir / f"{key}.pkl"
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            self.l3_disk_index[key] = str(file_path)
            self._save_disk_index()
        except Exception as e:
            logger.warning(f"Could not save to disk cache: {e}")
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """Load data from disk cache."""
        if key not in self.l3_disk_index:
            return None
        
        file_path = Path(self.l3_disk_index[key])
        if not file_path.exists():
            del self.l3_disk_index[key]
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Could not load from disk cache: {e}")
            return None
    
    def clear(self, level: Optional[int] = None):
        """Clear cache at specified level or all levels."""
        if level == 1 or level is None:
            self.l1_cache.clear()
        if level == 2 or level is None:
            self.l2_cache.clear()
        if level == 3 or level is None:
            # Clear disk cache
            for file_path in self.l3_disk_index.values():
                try:
                    Path(file_path).unlink()
                except Exception:
                    pass
            self.l3_disk_index.clear()
            self._save_disk_index()
        
        if level is None:
            self.stats.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "l1_items": len(self.l1_cache),
            "l2_items": len(self.l2_cache),
            "l3_items": len(self.l3_disk_index),
            "stats": self.stats.get_stats(),
            "metrics": self.metrics.get_summary()
        }


class SchemaCache:
    """Schema-specific caching with intelligent invalidation."""
    
    def __init__(
        self,
        cache: Optional[MultiLevelCache] = None,
        ttl: int = 3600
    ):
        """
        Initialize schema cache.
        
        Args:
            cache: Multi-level cache instance
            ttl: Time to live for schema cache
        """
        self.cache = cache or MultiLevelCache()
        self.ttl = ttl
        self.schema_checksums: Dict[str, str] = {}
        self.table_dependencies: Dict[str, Set[str]] = {}
    
    def get_schema(self, key: str) -> Optional[Dict[str, TableSchema]]:
        """Get cached schema."""
        return self.cache.get(f"schema:{key}")
    
    def set_schema(
        self,
        key: str,
        schema: Dict[str, TableSchema],
        checksum: Optional[str] = None
    ):
        """Cache schema with checksum."""
        self.cache.set(f"schema:{key}", schema, ttl=self.ttl)
        
        if checksum:
            self.schema_checksums[key] = checksum
    
    def get_table(self, table_name: str) -> Optional[TableSchema]:
        """Get cached table schema."""
        return self.cache.get(f"table:{table_name}")
    
    def set_table(
        self,
        table_name: str,
        table_schema: TableSchema,
        dependencies: Optional[Set[str]] = None
    ):
        """Cache individual table schema."""
        self.cache.set(f"table:{table_name}", table_schema, ttl=self.ttl)
        
        if dependencies:
            self.table_dependencies[table_name] = dependencies
    
    def invalidate_table(self, table_name: str):
        """Invalidate table and dependent caches."""
        # Clear table cache
        self.cache.l1_cache.pop(f"table:{table_name}", None)
        self.cache.l2_cache.pop(f"table:{table_name}", None)
        
        # Clear dependent tables
        for dep_table, deps in self.table_dependencies.items():
            if table_name in deps:
                self.invalidate_table(dep_table)
    
    def get_query_pattern(self, pattern_hash: str) -> Optional[str]:
        """Get cached query pattern."""
        return self.cache.get(f"pattern:{pattern_hash}")
    
    def set_query_pattern(self, pattern_hash: str, sql: str):
        """Cache successful query pattern."""
        self.cache.set(f"pattern:{pattern_hash}", sql, ttl=self.ttl * 2)
    
    def warm_cache(self, schema: Dict[str, TableSchema]):
        """Pre-populate cache with schema."""
        # Cache full schema
        schema_key = calculate_content_hash(list(schema.keys()))
        self.set_schema(schema_key, schema)
        
        # Cache individual tables
        for table_name, table_schema in schema.items():
            self.set_table(table_name, table_schema)
        
        logger.info(f"Warmed cache with {len(schema)} tables")