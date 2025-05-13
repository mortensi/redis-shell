# Extension Development Guide

This guide explains how to develop extensions for Redis Shell.

## Extension Structure

An extension consists of a directory with the following files:

- `extension.json` - Extension definition
- `commands.py` - Extension commands

The extension directory should be placed in the `~/.redis-shell/extensions` directory or the directory specified in the configuration file.

## Extension Definition

The `extension.json` file defines the extension's metadata, commands, and completions.

```json
{
  "name": "myextension",
  "description": "My custom extension",
  "commands_class": "MyExtensionCommands",
  "commands": [
    {
      "name": "hello",
      "description": "Say hello",
      "usage": "/myextension hello [--name NAME]",
      "options": [
        {
          "name": "--name",
          "description": "Name to greet",
          "required": false,
          "default": "world",
          "completion": "names"
        }
      ]
    }
  ],
  "completions": {
    "names": {
      "type": "function",
      "function": "get_names"
    }
  }
}
```

### Extension Definition Fields

- `name` - Extension name (required)
- `description` - Extension description (required)
- `commands_class` - Name of the commands class in the `commands.py` file (default: `Commands`)
- `commands` - List of commands (required)
  - `name` - Command name (required)
  - `description` - Command description (required)
  - `usage` - Command usage (required)
  - `options` - List of command options
    - `name` - Option name (required)
    - `description` - Option description (required)
    - `required` - Whether the option is required (default: false)
    - `default` - Default value for the option
    - `completion` - Name of the completion function for the option
- `completions` - Dictionary of completion functions
  - `type` - Completion type (function, list, or dict)
  - `function` - Name of the completion function in the `commands.py` file
  - `values` - List of completion values (for list type)
  - `items` - Dictionary of completion values (for dict type)

## Extension Commands

The `commands.py` file implements the extension's commands and completion functions.

```python
class MyExtensionCommands:
    def __init__(self, cli=None):
        self.cli = cli

    def handle_command(self, cmd, args):
        if cmd == "hello":
            return self._hello(args)
        return None

    def _hello(self, args):
        import argparse
        parser = argparse.ArgumentParser(description='Say hello')
        parser.add_argument('--name', type=str, default='world', help='Name to greet')
        parsed_args = parser.parse_args(args)
        return f"Hello, {parsed_args.name}!"

    def get_names(self, incomplete=""):
        names = ["world", "friend", "Redis"]
        return [n for n in names if incomplete == "" or n.startswith(incomplete)]
```

### Extension Commands Class

The extension commands class should implement the following methods:

- `__init__(self, cli=None)` - Initialize the extension commands
- `handle_command(self, cmd, args)` - Handle a command
  - `cmd` - Command name
  - `args` - Command arguments
  - Returns the command result or `None` if the command is not handled
- Completion functions - Implement completion functions for command options
  - `incomplete` - Incomplete text to complete
  - Returns a list of completion items

## Using the Extension Base Class

Redis Shell provides a base `Extension` class that you can inherit from to simplify extension development.

```python
from redis_shell.extensions.base import Extension

class MyExtension(Extension):
    def __init__(self, name, cli=None):
        super().__init__(name, cli)

    def initialize(self):
        # Initialize the extension
        pass

    def shutdown(self):
        # Shutdown the extension
        pass

    def handle_command(self, cmd, args):
        if cmd == "hello":
            return self._hello(args)
        return None

    def _hello(self, args):
        import argparse
        parser = argparse.ArgumentParser(description='Say hello')
        parser.add_argument('--name', type=str, default='world', help='Name to greet')
        parsed_args = parser.parse_args(args)
        return f"Hello, {parsed_args.name}!"

    def get_completions(self, text):
        # Return completions for the given text
        return []

    def get_names(self, incomplete=""):
        names = ["world", "friend", "Redis"]
        return [n for n in names if incomplete == "" or n.startswith(incomplete)]
```

## Using the Redis Connection

Extensions can access the Redis connection through the CLI instance passed to the constructor.

```python
def __init__(self, cli=None):
    self.cli = cli
    self.redis = cli.redis if cli else None

def _get_keys(self, args):
    if not self.redis:
        return "No Redis connection available"
    
    import argparse
    parser = argparse.ArgumentParser(description='Get keys')
    parser.add_argument('--pattern', type=str, default='*', help='Pattern to match keys')
    parsed_args = parser.parse_args(args)
    
    keys = self.redis.keys(parsed_args.pattern)
    return "\n".join([key.decode('utf-8') for key in keys])
```

## Using the Connection Manager

Extensions can also access the connection manager to get the current Redis connection or create a new one.

```python
def __init__(self, cli=None):
    self.cli = cli
    self.connection_manager = cli.connection_manager if cli else None

def _get_connection_info(self, args):
    if not self.connection_manager:
        return "No connection manager available"
    
    connections = self.connection_manager.get_connections()
    current_id = self.connection_manager.get_current_connection_id()
    
    result = "Connections:\n"
    for conn_id, conn in connections.items():
        if conn_id == current_id:
            result += f"* {conn_id}: {conn['host']}:{conn['port']} (db: {conn['db']})\n"
        else:
            result += f"  {conn_id}: {conn['host']}:{conn['port']} (db: {conn['db']})\n"
    
    return result
```

## Using the State Manager

Extensions can access the state manager to store and retrieve state information.

```python
def __init__(self, cli=None):
    self.cli = cli
    self.state_manager = cli.state_manager if cli else None

def _save_state(self, args):
    if not self.state_manager:
        return "No state manager available"
    
    import argparse
    parser = argparse.ArgumentParser(description='Save state')
    parser.add_argument('--key', type=str, required=True, help='State key')
    parser.add_argument('--value', type=str, required=True, help='State value')
    parsed_args = parser.parse_args(args)
    
    self.state_manager.set_state(parsed_args.key, parsed_args.value)
    return f"State saved: {parsed_args.key}={parsed_args.value}"

def _get_state(self, args):
    if not self.state_manager:
        return "No state manager available"
    
    import argparse
    parser = argparse.ArgumentParser(description='Get state')
    parser.add_argument('--key', type=str, required=True, help='State key')
    parsed_args = parser.parse_args(args)
    
    value = self.state_manager.get_state(parsed_args.key)
    if value is None:
        return f"State not found: {parsed_args.key}"
    return f"State: {parsed_args.key}={value}"
```

## Using the Utilities

Extensions can use the utility modules provided by Redis Shell.

```python
from redis_shell.utils.file_utils import PathHandler
from redis_shell.utils.command_utils import CommandParser, CommandFormatter
from redis_shell.utils.completion_utils import completion_registry

def get_export_files(self, incomplete=""):
    return PathHandler.get_file_completions(incomplete, "redis-export-*.txt")

def _format_table(self, args):
    headers = ["Name", "Value"]
    rows = [
        ["key1", "value1"],
        ["key2", "value2"],
        ["key3", "value3"]
    ]
    return CommandFormatter.format_table(headers, rows)
```

## Testing Extensions

Redis Shell provides a testing framework for extensions.

```python
import pytest
from redis_shell.extensions.base import load_extension

def test_extension():
    # Load the extension
    extension = load_extension("/path/to/extension")
    
    # Check the extension metadata
    assert extension['name'] == "myextension"
    assert "hello" in [cmd['name'] for cmd in extension['definition']['commands']]
    
    # Test the extension commands
    result = extension['commands'].handle_command("hello", ["--name", "test"])
    assert result == "Hello, test!"
    
    # Test the extension completions
    completions = extension['commands'].get_names("fr")
    assert "friend" in completions
```

## Debugging Extensions

Redis Shell provides logging utilities for debugging extensions.

```python
import logging
from redis_shell.utils.logging_utils import setup_logging

# Set up logging
logger = logging.getLogger(__name__)

def _hello(self, args):
    logger.debug(f"Hello command called with args: {args}")
    
    import argparse
    parser = argparse.ArgumentParser(description='Say hello')
    parser.add_argument('--name', type=str, default='world', help='Name to greet')
    
    try:
        parsed_args = parser.parse_args(args)
        logger.debug(f"Parsed args: {parsed_args}")
        return f"Hello, {parsed_args.name}!"
    except Exception as e:
        logger.error(f"Error parsing args: {str(e)}")
        return f"Error: {str(e)}"
```
