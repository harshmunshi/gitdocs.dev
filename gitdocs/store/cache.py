"""Local caching with TTL support."""

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from diskcache import Cache as DiskCache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Cache:
    """
    Local cache with TTL support using diskcache.

    Provides caching for API responses to reduce load and improve performance.
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl: int = 300,
        enabled: bool = True,
        max_size: int = 100 * 1024 * 1024,  # 100MB default
    ) -> None:
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Default TTL in seconds
            enabled: Whether caching is enabled
            max_size: Maximum cache size in bytes
        """
        self.cache_dir = cache_dir
        self.default_ttl = ttl
        self.enabled = enabled

        if enabled:
            self._cache = DiskCache(
                str(cache_dir),
                size_limit=max_size,
            )
        else:
            self._cache = None

    def _make_key(self, namespace: str, key: str) -> str:
        """Create a cache key with namespace."""
        return f"{namespace}:{key}"

    def get(
        self,
        namespace: str,
        key: str,
        default: T | None = None,
    ) -> T | None:
        """
        Get a value from cache.

        Args:
            namespace: Cache namespace (e.g., 'jira', 'confluence')
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        if not self.enabled or not self._cache:
            return default

        cache_key = self._make_key(namespace, key)

        try:
            value = self._cache.get(cache_key, default)
            if value is not default:
                logger.debug(f"Cache hit: {cache_key}")
            return value
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return default

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Set a value in cache.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
        """
        if not self.enabled or not self._cache:
            return

        cache_key = self._make_key(namespace, key)
        expire = ttl if ttl is not None else self.default_ttl

        try:
            self._cache.set(cache_key, value, expire=expire)
            logger.debug(f"Cache set: {cache_key} (ttl={expire}s)")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def delete(self, namespace: str, key: str) -> None:
        """Delete a specific key from cache."""
        if not self.enabled or not self._cache:
            return

        cache_key = self._make_key(namespace, key)

        try:
            self._cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of keys cleared
        """
        if not self.enabled or not self._cache:
            return 0

        prefix = f"{namespace}:"
        count = 0

        try:
            for key in list(self._cache):
                if isinstance(key, str) and key.startswith(prefix):
                    self._cache.delete(key)
                    count += 1
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

        return count

    def clear_all(self) -> None:
        """Clear entire cache."""
        if self._cache:
            try:
                self._cache.clear()
            except Exception as e:
                logger.warning(f"Cache clear error: {e}")

    def cached(
        self,
        namespace: str,
        key_func: Callable[..., str],
        ttl: int | None = None,
    ) -> Callable:
        """
        Decorator for caching function results.

        Args:
            namespace: Cache namespace
            key_func: Function to generate cache key from arguments
            ttl: TTL in seconds

        Returns:
            Decorated function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                key = key_func(*args, **kwargs)

                # Try to get from cache
                cached_value = self.get(namespace, key)
                if cached_value is not None:
                    return cached_value

                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(namespace, key, result, ttl)
                return result

            return wrapper

        return decorator

    def close(self) -> None:
        """Close cache connection."""
        if self._cache:
            try:
                self._cache.close()
            except Exception:
                pass

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self._cache:
            return {"enabled": False}

        try:
            return {
                "enabled": True,
                "directory": str(self.cache_dir),
                "size": self._cache.volume(),
                "count": len(self._cache),
            }
        except Exception:
            return {"enabled": True, "error": "Could not get stats"}


def cache_key_for_jql(jql: str, max_results: int) -> str:
    """Generate cache key for JQL query."""
    content = f"{jql}:{max_results}"
    return hashlib.md5(content.encode()).hexdigest()


def cache_key_for_issue(issue_key: str) -> str:
    """Generate cache key for issue."""
    return issue_key.upper()


def cache_key_for_page(page_id: str) -> str:
    """Generate cache key for Confluence page."""
    return page_id
