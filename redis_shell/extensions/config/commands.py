"""
Configuration management commands for Redis Shell.

This module provides commands for managing the Redis Shell configuration.
"""

from typing import Optional, Dict, Any, List
import json
import argparse
from ...config import config

class ConfigCommands:
    def __init__(self, cli=None):
        self._cli = cli

    def handle_command(self, cmd: str, args: list) -> Optional[str]:
        """Handle configuration commands."""
        if cmd == "get":
            return self._get(args)
        elif cmd == "set":
            return self._set(args)
        elif cmd == "save":
            return self._save(args)
        return None

    def _get(self, args: list) -> str:
        """Get a configuration value."""
        parser = argparse.ArgumentParser(description='Get configuration value')
        parser.add_argument('--all', action='store_true', help='Get all configuration values')
        parser.add_argument('section', nargs='?', help='Configuration section')
        parser.add_argument('key', nargs='?', help='Configuration key')
        
        try:
            parsed_args = parser.parse_args(args)
        except SystemExit:
            # Catch the SystemExit that argparse raises when --help is used
            return "Usage: /config get [--all] [section] [key]"
        
        # Get all configuration
        if parsed_args.all:
            return self._format_config(config.get_all())
        
        # Get a specific section
        if parsed_args.section and not parsed_args.key:
            section_config = config.get_section(parsed_args.section)
            if not section_config:
                return f"Section '{parsed_args.section}' not found in configuration"
            return self._format_config({parsed_args.section: section_config})
        
        # Get a specific key in a section
        if parsed_args.section and parsed_args.key:
            value = config.get(parsed_args.section, parsed_args.key)
            if value is None:
                return f"Key '{parsed_args.key}' not found in section '{parsed_args.section}'"
            return f"{parsed_args.section}.{parsed_args.key} = {self._format_value(value)}"
        
        # No arguments provided, show usage
        return "Usage: /config get [--all] [section] [key]"

    def _set(self, args: list) -> str:
        """Set a configuration value."""
        parser = argparse.ArgumentParser(description='Set configuration value')
        parser.add_argument('section', help='Configuration section')
        parser.add_argument('key', help='Configuration key')
        parser.add_argument('value', help='Configuration value')
        
        try:
            parsed_args = parser.parse_args(args)
        except SystemExit:
            # Catch the SystemExit that argparse raises when --help is used
            return "Usage: /config set <section> <key> <value>"
        
        # Parse the value (try to convert to appropriate type)
        value = self._parse_value(parsed_args.value)
        
        # Set the configuration value
        config.set(parsed_args.section, parsed_args.key, value)
        
        return f"Configuration value set: {parsed_args.section}.{parsed_args.key} = {self._format_value(value)}"

    def _save(self, args: list) -> str:
        """Save configuration to disk."""
        try:
            config.save_config()
            return f"Configuration saved to {config.config_file}"
        except Exception as e:
            return f"Error saving configuration: {str(e)}"

    def _format_config(self, config_dict: Dict[str, Any]) -> str:
        """Format configuration dictionary as a string."""
        return json.dumps(config_dict, indent=2)

    def _format_value(self, value: Any) -> str:
        """Format a configuration value as a string."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return str(value)

    def _parse_value(self, value_str: str) -> Any:
        """Parse a string value into an appropriate type."""
        # Try to parse as JSON
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            pass
        
        # Try to parse as boolean
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        
        # Try to parse as integer
        try:
            return int(value_str)
        except ValueError:
            pass
        
        # Try to parse as float
        try:
            return float(value_str)
        except ValueError:
            pass
        
        # Return as string
        return value_str
