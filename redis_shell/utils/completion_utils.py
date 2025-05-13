"""
Completion utilities for redis-shell.

This module contains utilities for command completion and autocompletion.
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
import os


class CompletionProvider:
    """Base class for completion providers."""

    def get_completions(self, text: str) -> List[str]:
        """
        Get completions for the given text.

        Args:
            text: The text to complete

        Returns:
            List of completion strings
        """
        raise NotImplementedError("Subclasses must implement get_completions")


class FileCompletionProvider(CompletionProvider):
    """Provides file path completions."""

    def __init__(self, file_pattern: Optional[str] = None, file_prefix: Optional[str] = None):
        """
        Initialize the file completion provider.

        Args:
            file_pattern: Optional glob pattern to match files against
            file_prefix: Optional prefix that files must start with
        """
        from redis_shell.utils.file_utils import PathHandler
        self.path_handler = PathHandler
        self.file_pattern = file_pattern
        self.file_prefix = file_prefix

    def get_completions(self, text: str) -> List[str]:
        """
        Get file path completions.

        Args:
            text: The text to complete

        Returns:
            List of file path completions
        """
        return self.path_handler.get_path_completions(text, self.file_pattern, self.file_prefix)


class RedisKeyPatternProvider(CompletionProvider):
    """Provides Redis key pattern completions."""

    def get_completions(self, text: str) -> List[str]:
        """
        Get Redis key pattern completions.

        Args:
            text: The text to complete

        Returns:
            List of key pattern completions
        """
        # Only suggest "*" as a default pattern if no input is provided
        if text == "":
            return ["*"]
        return [text]


class RedisHostProvider(CompletionProvider):
    """Provides Redis host completions."""

    def __init__(self, connection_manager=None):
        """
        Initialize the Redis host provider.

        Args:
            connection_manager: Optional connection manager instance
        """
        self.connection_manager = connection_manager

    def get_completions(self, text: str) -> List[str]:
        """
        Get Redis host completions.

        Args:
            text: The text to complete

        Returns:
            List of host completions
        """
        # Common Redis hosts
        hosts = [
            "localhost",
            "127.0.0.1",
            "redis-server",
            "redis.local"
        ]

        # Add hosts from existing connections if connection manager is available
        if self.connection_manager:
            for conn in self.connection_manager.get_connections().values():
                if conn['host'] not in hosts:
                    hosts.append(conn['host'])

        # Try to resolve the local hostname
        try:
            import socket
            local_hostname = socket.gethostname()
            if local_hostname not in hosts:
                hosts.append(local_hostname)
        except Exception:
            pass

        # Filter hosts based on the incomplete text
        return [h for h in hosts if text == "" or h.startswith(text)]


class ConnectionIdProvider(CompletionProvider):
    """Provides connection ID completions."""

    def __init__(self, connection_manager=None):
        """
        Initialize the connection ID provider.

        Args:
            connection_manager: Optional connection manager instance
        """
        self.connection_manager = connection_manager

    def get_completions(self, text: str) -> List[str]:
        """
        Get connection ID completions.

        Args:
            text: The text to complete

        Returns:
            List of connection ID completions
        """
        if not self.connection_manager:
            return []

        # Get all connection IDs
        connection_ids = list(self.connection_manager.get_connections().keys())

        # Filter connection IDs based on the incomplete text
        return [c for c in connection_ids if text == "" or c.startswith(text)]


class CompletionRegistry:
    """Registry for completion providers."""

    _instance = None

    def __new__(cls):
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super(CompletionRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the completion registry."""
        if getattr(self, '_initialized', False):
            return

        self.providers: Dict[str, CompletionProvider] = {}
        self._initialized = True

    def register(self, name: str, provider: CompletionProvider):
        """
        Register a completion provider.

        Args:
            name: The name of the provider
            provider: The completion provider
        """
        self.providers[name] = provider

    def get_provider(self, name: str) -> Optional[CompletionProvider]:
        """
        Get a completion provider by name.

        Args:
            name: The name of the provider

        Returns:
            The completion provider, or None if not found
        """
        return self.providers.get(name)

    def get_completions(self, name: str, text: str) -> List[str]:
        """
        Get completions from a provider.

        Args:
            name: The name of the provider
            text: The text to complete

        Returns:
            List of completions
        """
        provider = self.get_provider(name)
        if provider:
            return provider.get_completions(text)
        return []


# Create a global registry instance
completion_registry = CompletionRegistry()

# Register built-in providers
completion_registry.register("file", FileCompletionProvider())
completion_registry.register("redis_export_files", FileCompletionProvider("*.txt", "redis-export-"))
completion_registry.register("key_patterns", RedisKeyPatternProvider())
