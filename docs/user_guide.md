# Redis Shell User Guide

Redis Shell is an enhanced interactive command-line interface for Redis that goes beyond the standard `redis-cli`. It provides a rich set of features including multi-connection management, data import/export, cluster management, and an extensible plugin architecture.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Built-in Extensions](#built-in-extensions)
- [Configuration](#configuration)
- [Tips and Best Practices](#tips-and-best-practices)

## Installation

### For End Users

#### Using PEX (Recommended)

Create a standalone executable using PEX:

```bash
# Install PEX in a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install pex

# Create the executable
pex . -D . -e redis_shell.__main__:main -o redis-shell.pex --venv --strip-pex-env --no-compile --no-wheel --compress

# Run it
./redis-shell.pex
```

#### Including User Extensions

To include your custom extensions in the executable:

```bash
pex . -D . -D $HOME/.config/redis-shell/extensions -r $HOME/.config/redis-shell/extensions/*/requirements.txt -e redis_shell.__main__:main -o redis-shell.pex --venv --strip-pex-env --no-compile --no-wheel --compress
```

### For Developers

If you want to contribute or modify the code:

```bash
# Clone the repository
git clone <repository-url>
cd redis-shell

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Run directly
redis-shell
```

## Quick Start

### Basic Connection

```bash
# Connect to local Redis (default: localhost:6379)
redis-shell

# Connect to remote Redis
redis-shell --host redis.example.com --port 6379 --password mypassword

# Connect with SSL
redis-shell --host secure-redis.com --port 6380 --ssl --ssl-cert-reqs required
```

### First Commands

Once connected, you can use Redis Shell like the standard Redis CLI, but with enhanced features:

```bash
# Standard Redis commands work as expected
localhost:6379> SET mykey "Hello World"
OK

localhost:6379> GET mykey
"Hello World"

# Use shell commands (starting with /)
localhost:6379> /help
Available commands:
  /clear - Clear screen
  /exit - Exit shell
  /help - Show help message
  /history - Show command history

# Use built-in extensions
localhost:6379> /data export --pattern "user:*"
Exporting keys matching pattern 'user:*'...
Export completed: redis-export-20240118-143022-localhost-6379.txt
```

## Basic Usage

### Interactive Shell Features

#### Command History
- Use **Up/Down arrows** to navigate command history
- Use `/history` to view all previous commands
- Use `/history <number>` to re-run a specific command
- Use `/history clear` to clear the history

#### Autocompletion
- Press **Tab** to see available commands and options
- Works for Redis commands, shell commands, and extension commands
- Context-aware completion for file paths, connection IDs, etc.

#### Screen Management
- Use `/clear` to clear the screen
- Use **Ctrl+C** to cancel current input
- Use `/exit` or **Ctrl+D** to exit the shell

### Command Types

Redis Shell supports three types of commands:

1. **Redis Commands**: Standard Redis commands (GET, SET, HGET, etc.)
2. **Shell Commands**: Built-in shell utilities (starting with `/`)
3. **Extension Commands**: Commands provided by extensions (e.g., `/data export`)

### Environment Variables

Set these environment variables to configure default connection settings:

```bash
export REDIS_HOST=redis.example.com
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_USERNAME=myuser
export REDIS_PASSWORD=mypassword
export REDIS_SHELL_LOG_LEVEL=info
```

## Advanced Features

### Multi-Connection Management

Redis Shell can manage multiple Redis connections simultaneously:

```bash
# Create additional connections
localhost:6379> /connection create --host redis2.example.com --port 6379
Connection created with ID: 2

localhost:6379> /connection create --host redis-cluster.example.com --port 7000
Connection created with ID: 3

# List all connections
localhost:6379> /connection list
Connections:
* 1: localhost:6379 (db: 0)
  2: redis2.example.com:6379 (db: 0)
  3: redis-cluster.example.com:7000 (db: 0)

# Switch between connections
localhost:6379> /connection use 2
Switched to connection 2
redis2.example.com:6379> 

# Remove a connection
redis2.example.com:6379> /connection destroy 3
Connection 3 destroyed
```

### Data Import/Export

#### Exporting Data

```bash
# Export all keys
localhost:6379> /data export

# Export keys matching a pattern
localhost:6379> /data export --pattern "user:*"

# Export to a specific folder
localhost:6379> /data export --folder /tmp/backups

# Force using KEYS command (faster but blocks Redis)
localhost:6379> /data export --force-keys

# Check export status
localhost:6379> /data status
```

#### Importing Data

```bash
# Import from a file
localhost:6379> /data import --file redis-export-20240118-143022-localhost-6379.txt

# The import process will show progress and handle different data types
```

### SSL/TLS Connections

Redis Shell supports secure connections:

```bash
# Basic SSL connection
redis-shell --host secure-redis.com --port 6380 --ssl

# SSL with custom certificates
redis-shell --host secure-redis.com --port 6380 --ssl \
  --ssl-ca-certs /path/to/ca.crt \
  --ssl-certfile /path/to/client.crt \
  --ssl-keyfile /path/to/client.key

# SSL with different certificate requirements
redis-shell --host secure-redis.com --port 6380 --ssl --ssl-cert-reqs optional
```

## Built-in Extensions

Redis Shell comes with several powerful built-in extensions:

### Data Extension (`/data`)
- **Export**: Export Redis data with pattern matching
- **Import**: Import data from exported files
- **Status**: Monitor export/import operations

### Connection Extension (`/connection`)
- **Create**: Create new Redis connections
- **List**: List all available connections
- **Use**: Switch between connections
- **Destroy**: Remove connections

### Cluster Extension (`/cluster`)
- **Deploy**: Deploy a local Redis cluster for testing
- **Info**: Get cluster information
- **Start/Stop**: Control cluster lifecycle
- **Remove**: Clean up cluster resources

### Sentinel Extension (`/sentinel`)
- **Deploy**: Deploy a Redis Sentinel setup
- **Info**: Get Sentinel information
- **Start/Stop**: Control Sentinel lifecycle
- **Remove**: Clean up Sentinel resources

### Config Extension (`/config`)
- **Get**: Retrieve configuration values
- **Set**: Modify configuration values
- **Save**: Persist configuration changes

## Configuration

### Configuration File Locations

Redis Shell looks for configuration files in this order:

1. Path specified by `REDIS_SHELL_CONFIG` environment variable
2. `~/.redis-shell`
3. `~/.config/redis-shell/config.json`
4. `/etc/redis-shell/config.json`

### Configuration Structure

```json
{
  "general": {
    "history_size": 100,
    "log_level": "info",
    "log_file": null,
    "state_file": "~/.redis-shell"
  },
  "redis": {
    "default_host": "127.0.0.1",
    "default_port": 6379,
    "default_db": 0,
    "default_username": "default",
    "default_password": "",
    "timeout": 5,
    "decode_responses": false,
    "ssl": false
  },
  "extensions": {
    "extension_dir": "~/.config/redis-shell/extensions"
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

## Tips and Best Practices

### Performance Tips

1. **Use SCAN instead of KEYS**: The data export extension uses SCAN by default, which is safer for production
2. **Pattern Matching**: Use specific patterns when exporting to reduce data transfer
3. **Connection Pooling**: Reuse connections instead of creating new ones frequently

### Security Best Practices

1. **Use SSL/TLS**: Always use encrypted connections in production
2. **Environment Variables**: Store sensitive information like passwords in environment variables
3. **Certificate Validation**: Use proper certificate validation in production environments

### Workflow Tips

1. **Command History**: Use `/history` to review and rerun complex commands
2. **Tab Completion**: Leverage autocompletion to discover available options
3. **Multiple Connections**: Use connection management for working with multiple Redis instances
4. **Configuration**: Set up a configuration file for frequently used settings

### Troubleshooting

1. **Connection Issues**: Check network connectivity and Redis server status
2. **SSL Problems**: Verify certificate paths and permissions
3. **Extension Errors**: Check extension directory permissions and file structure
4. **Performance**: Monitor Redis server resources during large operations

For more detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).
