"""
Plugin manager for redis-shell.

This module contains the plugin manager for redis-shell.
"""

import os
import json
import logging
import importlib.util
import sys
import shutil
import tempfile
import zipfile
import requests
from typing import Dict, Any, Optional, List, Union, Callable
from .utils.logging_utils import ExtensionError
from .extensions.base import load_extension
from .config import config

logger = logging.getLogger(__name__)


class PluginManager:
    """Plugin manager for redis-shell."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the plugin manager."""
        if getattr(self, '_initialized', False):
            return
            
        self.plugins = {}
        self.plugin_dir = self._get_plugin_dir()
        self._initialized = True
        
    def _get_plugin_dir(self) -> str:
        """
        Get the plugin directory.
        
        Returns:
            Plugin directory path
        """
        # Get the plugin directory from the configuration
        plugin_dir = config.get('extensions', 'extension_dir')
        if plugin_dir:
            return os.path.expanduser(plugin_dir)
            
        # Use the default plugin directory
        return os.path.expanduser('~/.redis-shell/extensions')
        
    def load_plugins(self) -> None:
        """Load all plugins."""
        # Create the plugin directory if it doesn't exist
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            
        # Get all subdirectories in the plugin directory
        for item in os.listdir(self.plugin_dir):
            item_path = os.path.join(self.plugin_dir, item)
            if os.path.isdir(item_path):
                try:
                    # Load the plugin
                    plugin = self.load_plugin(item_path)
                    self.plugins[plugin['name']] = plugin
                    logger.info(f"Loaded plugin: {plugin['name']}")
                except Exception as e:
                    logger.error(f"Error loading plugin {item}: {str(e)}")
                    
    def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """
        Load a plugin from the given path.
        
        Args:
            plugin_path: Path to the plugin directory
            
        Returns:
            Plugin information
        """
        return load_extension(plugin_path)
        
    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin information or None if not found
        """
        return self.plugins.get(name)
        
    def get_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all plugins.
        
        Returns:
            Dictionary of plugin names to plugin information
        """
        return self.plugins.copy()
        
    def install_plugin(self, source: str) -> Dict[str, Any]:
        """
        Install a plugin from the given source.
        
        Args:
            source: Plugin source (URL, file path, or plugin name)
            
        Returns:
            Installed plugin information
        """
        # Check if the source is a URL
        if source.startswith('http://') or source.startswith('https://'):
            return self._install_from_url(source)
            
        # Check if the source is a file path
        if os.path.isfile(source):
            return self._install_from_file(source)
            
        # Check if the source is a plugin name
        return self._install_from_name(source)
        
    def _install_from_url(self, url: str) -> Dict[str, Any]:
        """
        Install a plugin from a URL.
        
        Args:
            url: Plugin URL
            
        Returns:
            Installed plugin information
        """
        # Download the plugin
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # Write the response content to the temporary file
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                    
            # Install the plugin from the temporary file
            try:
                plugin = self._install_from_file(temp_file.name)
                return plugin
            finally:
                # Remove the temporary file
                os.unlink(temp_file.name)
        except Exception as e:
            raise ExtensionError(f"Error downloading plugin from {url}: {str(e)}")
            
    def _install_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Install a plugin from a file.
        
        Args:
            file_path: Plugin file path
            
        Returns:
            Installed plugin information
        """
        # Check if the file is a ZIP file
        if not zipfile.is_zipfile(file_path):
            raise ExtensionError(f"Invalid plugin file: {file_path} (not a ZIP file)")
            
        # Extract the plugin
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Get the plugin name from the extension.json file
                if 'extension.json' not in zip_file.namelist():
                    raise ExtensionError(f"Invalid plugin file: {file_path} (extension.json not found)")
                    
                # Read the extension.json file
                with zip_file.open('extension.json') as f:
                    extension_json = json.load(f)
                    
                # Get the plugin name
                if 'name' not in extension_json:
                    raise ExtensionError(f"Invalid plugin file: {file_path} (name not specified in extension.json)")
                    
                plugin_name = extension_json['name']
                plugin_dir = os.path.join(self.plugin_dir, plugin_name)
                
                # Check if the plugin already exists
                if os.path.exists(plugin_dir):
                    # Remove the existing plugin
                    shutil.rmtree(plugin_dir)
                    
                # Create the plugin directory
                os.makedirs(plugin_dir)
                
                # Extract the plugin files
                zip_file.extractall(plugin_dir)
                
            # Load the plugin
            plugin = self.load_plugin(plugin_dir)
            self.plugins[plugin['name']] = plugin
            return plugin
        except Exception as e:
            raise ExtensionError(f"Error extracting plugin from {file_path}: {str(e)}")
            
    def _install_from_name(self, name: str) -> Dict[str, Any]:
        """
        Install a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Installed plugin information
        """
        # TODO: Implement plugin repository
        raise ExtensionError(f"Plugin repository not implemented yet")
        
    def uninstall_plugin(self, name: str) -> None:
        """
        Uninstall a plugin.
        
        Args:
            name: Plugin name
        """
        # Check if the plugin exists
        if name not in self.plugins:
            raise ExtensionError(f"Plugin not found: {name}")
            
        # Get the plugin directory
        plugin_dir = os.path.join(self.plugin_dir, name)
        if not os.path.exists(plugin_dir):
            raise ExtensionError(f"Plugin directory not found: {plugin_dir}")
            
        # Remove the plugin directory
        shutil.rmtree(plugin_dir)
        
        # Remove the plugin from the plugins dictionary
        del self.plugins[name]
        
    def update_plugin(self, name: str) -> Dict[str, Any]:
        """
        Update a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            Updated plugin information
        """
        # Check if the plugin exists
        if name not in self.plugins:
            raise ExtensionError(f"Plugin not found: {name}")
            
        # TODO: Implement plugin repository
        raise ExtensionError(f"Plugin repository not implemented yet")


# Create a global plugin manager instance
plugin_manager = PluginManager()
