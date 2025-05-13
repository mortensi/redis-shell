"""
Tests for the utility modules.

This module contains tests for the utility modules.
"""

import pytest
import os
import tempfile
from redis_shell.utils.file_utils import PathHandler
from redis_shell.utils.command_utils import CommandParser, CommandFormatter
from redis_shell.utils.completion_utils import CompletionRegistry, FileCompletionProvider, RedisKeyPatternProvider


def test_path_handler_parse_path():
    """Test parsing a path."""
    # Test absolute path
    base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path('/tmp/test')
    assert base_dir == '/tmp'
    assert prefix == 'test'
    assert is_absolute is True
    assert path_prefix == '/tmp/'
    
    # Test relative path
    base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path('tmp/test')
    assert os.path.basename(base_dir) == 'tmp'
    assert prefix == 'test'
    assert is_absolute is False
    assert path_prefix == 'tmp/'
    
    # Test simple path
    base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path('test')
    assert os.path.exists(base_dir)
    assert prefix == 'test'
    assert is_absolute is False
    assert path_prefix == ''


def test_path_handler_get_directory_completions():
    """Test getting directory completions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test directories
        os.makedirs(os.path.join(temp_dir, 'dir1'))
        os.makedirs(os.path.join(temp_dir, 'dir2'))
        os.makedirs(os.path.join(temp_dir, 'dir3'))
        
        # Test getting completions for the temp directory
        completions = PathHandler.get_directory_completions(temp_dir)
        assert len(completions) == 3
        assert f"{temp_dir}/dir1/" in completions
        assert f"{temp_dir}/dir2/" in completions
        assert f"{temp_dir}/dir3/" in completions
        
        # Test getting completions for a partial path
        completions = PathHandler.get_directory_completions(os.path.join(temp_dir, 'dir'))
        assert len(completions) == 3
        assert f"{temp_dir}/dir1/" in completions
        assert f"{temp_dir}/dir2/" in completions
        assert f"{temp_dir}/dir3/" in completions


def test_path_handler_get_file_completions():
    """Test getting file completions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        with open(os.path.join(temp_dir, 'file1.txt'), 'w') as f:
            f.write('test')
        with open(os.path.join(temp_dir, 'file2.txt'), 'w') as f:
            f.write('test')
        with open(os.path.join(temp_dir, 'file3.dat'), 'w') as f:
            f.write('test')
        
        # Test getting completions for the temp directory
        completions = PathHandler.get_file_completions(temp_dir, '*.txt')
        assert len(completions) == 2
        assert f"{temp_dir}/file1.txt" in completions
        assert f"{temp_dir}/file2.txt" in completions
        assert f"{temp_dir}/file3.dat" not in completions
        
        # Test getting completions for a partial path
        completions = PathHandler.get_file_completions(os.path.join(temp_dir, 'file'), '*.txt')
        assert len(completions) == 2
        assert f"{temp_dir}/file1.txt" in completions
        assert f"{temp_dir}/file2.txt" in completions
        assert f"{temp_dir}/file3.dat" not in completions


def test_command_parser_parse_command_line():
    """Test parsing a command line."""
    # Test simple command
    command, args = CommandParser.parse_command_line('command arg1 arg2')
    assert command == 'command'
    assert args == ['arg1', 'arg2']
    
    # Test command with quotes
    command, args = CommandParser.parse_command_line('command "arg with spaces" arg2')
    assert command == 'command'
    assert args == ['arg with spaces', 'arg2']
    
    # Test empty command
    command, args = CommandParser.parse_command_line('')
    assert command == ''
    assert args == []


def test_command_formatter_format_table():
    """Test formatting a table."""
    # Test simple table
    headers = ['Column 1', 'Column 2', 'Column 3']
    rows = [
        ['Value 1', 'Value 2', 'Value 3'],
        ['Value 4', 'Value 5', 'Value 6'],
        ['Value 7', 'Value 8', 'Value 9']
    ]
    
    table = CommandFormatter.format_table(headers, rows)
    assert 'Column 1' in table
    assert 'Column 2' in table
    assert 'Column 3' in table
    assert 'Value 1' in table
    assert 'Value 2' in table
    assert 'Value 3' in table
    assert 'Value 4' in table
    assert 'Value 5' in table
    assert 'Value 6' in table
    assert 'Value 7' in table
    assert 'Value 8' in table
    assert 'Value 9' in table


def test_completion_registry():
    """Test the completion registry."""
    # Create a registry
    registry = CompletionRegistry()
    
    # Register some providers
    registry.register('file', FileCompletionProvider())
    registry.register('key_pattern', RedisKeyPatternProvider())
    
    # Test getting a provider
    provider = registry.get_provider('file')
    assert provider is not None
    assert isinstance(provider, FileCompletionProvider)
    
    # Test getting completions
    completions = registry.get_completions('key_pattern', '')
    assert completions == ['*']
    
    # Test getting completions for a non-existent provider
    completions = registry.get_completions('non_existent', '')
    assert completions == []
