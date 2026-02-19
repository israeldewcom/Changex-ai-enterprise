"""
Caching utilities with Redis.
"""
from functools import wraps
from typing import Optional, Any, Callable
from flask import current_app, request
from app.extensions import cache
import hashlib
import json

def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function name and arguments."""
    key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    key = ":".join(key_parts)
    return hashlib.md5(key.encode()).hexdigest()

def cached(timeout: int = 300, key_prefix: str = '', query_string: bool = False):
    """
    Cache decorator with optional query string inclusion.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Build cache key
            if query_string:
                # Include request query string in cache key
                qs = request.query_string.decode()
                key_suffix = hashlib.md5(qs.encode()).hexdigest()
            else:
                key_suffix = cache_key(*args, **kwargs)
            cache_key_full = f"{key_prefix}:{f.__name__}:{key_suffix}"
            
            # Try cache
            result = cache.get(cache_key_full)
            if result is None:
                result = f(*args, **kwargs)
                cache.set(cache_key_full, result, timeout=timeout)
            return result
        return wrapper
    return decorator

def invalidate_cache(pattern: str):
    """Invalidate all cache keys matching pattern."""
    # Note: Redis doesn't support pattern deletion directly, but we can scan
    import redis
    from app.extensions import cache
    if isinstance(cache.cache, redis.Redis):
        keys = cache.cache.keys(pattern)
        if keys:
            cache.cache.delete(*keys)
