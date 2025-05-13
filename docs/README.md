# Redis Shell

Redis Shell is an interactive command-line interface for Redis that provides a rich set of features beyond the standard Redis CLI.

## Features

- Interactive shell with command history and autocompletion
- Support for Redis Cluster and Redis Sentinel
- Extensible architecture with pluggable extensions
- Built-in extensions for data import/export, connection management, and more
- Comprehensive error handling and logging
- Configuration system with support for environment variables

## Installation

```bash
pip install redis-shell
```

## Quick Start

```bash
# Connect to a local Redis instance
redis-shell

# Connect to a remote Redis instance
redis-shell --host redis.example.com --port 6379 --db 0 --password secret
```

## Usage

### Basic Commands

- `/help` - Show help message
- `/clear` - Clear screen
- `/exit` - Exit the shell
- `/history` - Show command history
  - `/history clear` - Clear command history
  - `/history <number>` - Run a specific command from history

### Connection Management

- `/connection create` - Create a new connection
  - `--host HOST` - Redis host (default: localhost)
  - `--port PORT` - Redis port (default: 6379)
  - `--db DB` - Redis database number (default: 0)
  - `--password PASSWORD` - Redis password
- `/connection list` - List all connections
- `/connection use <id>` - Use a connection
- `/connection destroy <id>` - Destroy a connection

### Data Management

- `/data export` - Export Redis data to a file
  - `--pattern PATTERN` - Pattern to match keys (default: *)
  - `--folder FOLDER` - Folder to save the export file (default: current directory)
  - `--cancel` - Cancel a running export operation
  - `--force-keys` - Force using KEYS command instead of SCAN
- `/data import` - Import Redis data from a file
  - `--file FILE` - File to import

### Cluster Management

- `/cluster deploy` - Deploy a local Redis cluster
  - `--nodes NODES` - Number of nodes (default: 6)
  - `--replicas REPLICAS` - Number of replicas (default: 1)
  - `--start-port START_PORT` - Starting port (default: 30001)
- `/cluster destroy` - Destroy the local Redis cluster
- `/cluster info` - Show information about the local Redis cluster

### Sentinel Management

- `/sentinel deploy` - Deploy a local Redis Sentinel
  - `--sentinels SENTINELS` - Number of sentinels (default: 3)
  - `--replicas REPLICAS` - Number of replicas (default: 2)
  - `--start-port START_PORT` - Starting port (default: 40001)
- `/sentinel destroy` - Destroy the local Redis Sentinel
- `/sentinel info` - Show information about the local Redis Sentinel

## Configuration

Redis Shell can be configured using a configuration file or environment variables.

### Configuration File

The configuration file is located at `~/.redis-shell/config.json` by default. You can specify a different location using the `REDIS_SHELL_CONFIG` environment variable.

Example configuration file:

```json
{
  "general": {
    "history_size": 100,
    "log_level": "info",
    "log_file": null,
    "state_file": "~/.redis-shell/state.json"
  },
  "redis": {
    "default_host": "localhost",
    "default_port": 6379,
    "default_db": 0,
    "default_password": null,
    "timeout": 5,
    "decode_responses": false,
    "ssl": false,
    "ssl_ca_certs": null
  },
  "extensions": {
    "enabled": ["data", "connection", "cluster", "sentinel"],
    "extension_dir": "~/.redis-shell/extensions"
  },
  "ui": {
    "prompt_style": "green",
    "error_style": "red",
    "warning_style": "yellow",
    "success_style": "green",
    "info_style": "blue"
  }
}
```

### Environment Variables

- `REDIS_HOST` - Redis host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_DB` - Redis database number (default: 0)
- `REDIS_PASSWORD` - Redis password
- `REDIS_SHELL_CONFIG` - Path to the configuration file
- `REDIS_SHELL_LOG_LEVEL` - Log level (debug, info, warning, error, critical)
- `REDIS_SHELL_LOG_FILE` - Path to the log file

## Extensions

Redis Shell has an extensible architecture that allows you to create custom extensions. Extensions are loaded from the `~/.redis-shell/extensions` directory by default.

### Creating an Extension

An extension consists of a directory with the following files:

- `extension.json` - Extension definition
- `commands.py` - Extension commands

Example extension definition:

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
          "default": "world"
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

Example commands implementation:

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
