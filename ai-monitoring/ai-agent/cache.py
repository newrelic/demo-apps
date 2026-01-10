"""
Simple TTL cache for tool results.

Reduces redundant tool calls by caching recent results with
time-to-live expiration.
"""

import time
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Time-to-live cache for string results.

    Automatically expires entries after ttl_seconds.
    """

    def __init__(self, name: str, ttl_seconds: int):
        """
        Initialize TTL cache.

        Args:
            name: Cache name for logging
            ttl_seconds: Time-to-live in seconds
        """
        self.name = name
        self.ttl = ttl_seconds
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.hits = 0
        self.misses = 0
        logger.info(f"[CACHE] Initialized {name} cache (TTL={ttl_seconds}s)")

    def get(self, key: str) -> Optional[str]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key in self.cache:
            result, timestamp = self.cache[key]
            age = time.time() - timestamp

            if age < self.ttl:
                self.hits += 1
                logger.info(f"[CACHE] {self.name} HIT: key={key}, age={age:.1f}s")
                return result
            else:
                # Expired - remove from cache
                del self.cache[key]
                logger.info(f"[CACHE] {self.name} EXPIRED: key={key}, age={age:.1f}s")

        self.misses += 1
        logger.info(f"[CACHE] {self.name} MISS: key={key}")
        return None

    def set(self, key: str, value: str):
        """
        Store value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = (value, time.time())
        logger.info(f"[CACHE] {self.name} SET: key={key}, size={len(value)} bytes")

    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
        logger.info(f"[CACHE] {self.name} cleared")

    def stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, size, hit_rate
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self.cache),
            "hit_rate_percent": round(hit_rate, 1),
        }


# Global caches for MCP tools
system_health_cache = TTLCache(name="system_health", ttl_seconds=60)
database_status_cache = TTLCache(name="database_status", ttl_seconds=90)


def get_cache_stats() -> Dict[str, Dict[str, int]]:
    """
    Get statistics for all caches.

    Returns:
        Dictionary with stats for each cache
    """
    return {
        "system_health": system_health_cache.stats(),
        "database_status": database_status_cache.stats(),
    }
