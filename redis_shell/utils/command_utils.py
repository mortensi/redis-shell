"""
Command utilities for redis-shell.

This module contains utilities for command parsing, argument handling, and command execution.
"""

import argparse
import shlex
from typing import Dict, Any, Optional, List, Tuple, Union, Callable


class CommandParser:
    """Parser for shell commands."""
    
    @staticmethod
    def parse_command_line(command_line: str) -> Tuple[str, List[str]]:
        """
        Parse a command line into command and arguments.
        
        Args:
            command_line: The command line to parse
            
        Returns:
            Tuple containing:
                - command: The command
                - args: List of arguments
        """
        parts = shlex.split(command_line)
        if not parts:
            return "", []
            
        return parts[0], parts[1:]
    
    @staticmethod
    def create_argument_parser(
        description: str,
        options: List[Dict[str, Any]]
    ) -> argparse.ArgumentParser:
        """
        Create an argument parser for a command.
        
        Args:
            description: Command description
            options: List of option definitions
            
        Returns:
            Argument parser
        """
        parser = argparse.ArgumentParser(description=description)
        
        for option in options:
            option_args = {
                'help': option.get('description', '')
            }
            
            # Handle different option types
            if option.get('is_flag', False):
                option_args['action'] = 'store_true'
            elif 'default' in option:
                option_args['default'] = option['default']
                
            if 'type' in option:
                option_type = option['type']
                if option_type == 'int':
                    option_args['type'] = int
                elif option_type == 'float':
                    option_args['type'] = float
                elif option_type == 'str':
                    option_args['type'] = str
                    
            if option.get('required', False):
                option_args['required'] = True
                
            parser.add_argument(option['name'], **option_args)
            
        return parser


class CommandExecutor:
    """Executor for shell commands."""
    
    @staticmethod
    def execute_command(
        command: str,
        args: List[str],
        command_handlers: Dict[str, Callable]
    ) -> Optional[str]:
        """
        Execute a command with the given arguments.
        
        Args:
            command: The command to execute
            args: List of arguments
            command_handlers: Dictionary of command handlers
            
        Returns:
            Command result or None
        """
        if command in command_handlers:
            return command_handlers[command](args)
        return None


class CommandFormatter:
    """Formatter for command output."""
    
    @staticmethod
    def format_table(
        headers: List[str],
        rows: List[List[str]],
        padding: int = 2
    ) -> str:
        """
        Format a table for display.
        
        Args:
            headers: List of column headers
            rows: List of rows (each row is a list of column values)
            padding: Padding between columns
            
        Returns:
            Formatted table string
        """
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Format headers
        header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        separator = "-" * len(header_line)
        
        # Format rows
        formatted_rows = []
        for row in rows:
            formatted_row = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
            formatted_rows.append(formatted_row)
            
        # Combine everything
        return "\n".join([header_line, separator] + formatted_rows)
    
    @staticmethod
    def format_key_value(data: Dict[str, Any], indent: int = 0) -> str:
        """
        Format a dictionary as key-value pairs.
        
        Args:
            data: Dictionary to format
            indent: Indentation level
            
        Returns:
            Formatted string
        """
        result = []
        indent_str = " " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(f"{indent_str}{key}:")
                result.append(CommandFormatter.format_key_value(value, indent + 2))
            elif isinstance(value, list):
                result.append(f"{indent_str}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        result.append(CommandFormatter.format_key_value(item, indent + 2))
                    else:
                        result.append(f"{indent_str}  - {item}")
            else:
                result.append(f"{indent_str}{key}: {value}")
                
        return "\n".join(result)
