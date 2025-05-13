"""
Performance utilities for redis-shell.

This module contains utilities for performance optimization.
"""

import time
import functools
import logging
import threading
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Cache:
    """Simple in-memory cache."""
    
    def __init__(self, max_size: int = 100, ttl: int = 60):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of items in the cache
            ttl: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if time.time() < item['expires']:
                    return item['value']
                else:
                    # Remove expired item
                    del self.cache[key]
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (overrides the default)
        """
        with self.lock:
            # Remove oldest items if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['expires'])
                del self.cache[oldest_key]
                
            # Add new item
            self.cache[key] = {
                'value': value,
                'expires': time.time() + (ttl or self.ttl)
            }
            
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            
    def remove(self, key: str) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]


# Global cache instance
cache = Cache()


def cached(ttl: Optional[int] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (overrides the default)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create a cache key from the function name and arguments
            key = f"{func.__module__}.{func.__name__}:{hash(str(args))}-{hash(str(kwargs))}"
            
            # Check if the result is in the cache
            result = cache.get(key)
            if result is not None:
                return cast(T, result)
                
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
            
        return wrapper
    return decorator


class ProgressTracker:
    """Tracks progress of long-running operations."""
    
    def __init__(self, total: int, description: str = "Progress"):
        """
        Initialize the progress tracker.
        
        Args:
            total: Total number of items
            description: Progress description
        """
        self.total = total
        self.description = description
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 0.5  # Update every 0.5 seconds
        
    def update(self, increment: int = 1) -> None:
        """
        Update the progress.
        
        Args:
            increment: Increment amount
        """
        self.current += increment
        
        # Only update the display if enough time has passed
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            self._display_progress()
            
    def _display_progress(self) -> None:
        """Display the progress."""
        if self.total <= 0:
            return
            
        # Calculate progress percentage
        percentage = min(100, int(self.current * 100 / self.total))
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        
        # Calculate estimated time remaining
        if self.current > 0:
            items_per_second = self.current / elapsed
            if items_per_second > 0:
                eta = (self.total - self.current) / items_per_second
            else:
                eta = 0
        else:
            eta = 0
            
        # Format elapsed and ETA times
        elapsed_str = self._format_time(elapsed)
        eta_str = self._format_time(eta)
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * self.current / self.total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Print progress
        print(f"\r{self.description}: [{bar}] {percentage}% ({self.current}/{self.total}) - Elapsed: {elapsed_str}, ETA: {eta_str}", end='')
        
        # Print newline if complete
        if self.current >= self.total:
            print()
            
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = seconds % 60
            return f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            seconds = seconds % 60
            return f"{hours}h {minutes}m {seconds:.1f}s"


class LazyLoader:
    """Lazy loader for modules and classes."""
    
    def __init__(self, import_path: str):
        """
        Initialize the lazy loader.
        
        Args:
            import_path: Import path (e.g., 'redis_shell.extensions.data.commands.DataCommands')
        """
        self.import_path = import_path
        self._module = None
        self._obj = None
        
    def _load(self) -> Any:
        """
        Load the module or class.
        
        Returns:
            Loaded module or class
        """
        if self._obj is not None:
            return self._obj
            
        # Split the import path into module path and object name
        parts = self.import_path.split('.')
        module_path = '.'.join(parts[:-1])
        obj_name = parts[-1]
        
        # Import the module
        try:
            module = __import__(module_path, fromlist=[obj_name])
            self._module = module
            
            # Get the object
            if hasattr(module, obj_name):
                self._obj = getattr(module, obj_name)
                return self._obj
            else:
                raise ImportError(f"Cannot import name '{obj_name}' from '{module_path}'")
        except ImportError as e:
            logger.error(f"Error importing {self.import_path}: {str(e)}")
            raise
            
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Call the loaded object.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of calling the loaded object
        """
        obj = self._load()
        return obj(*args, **kwargs)
