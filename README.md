# Redis Shell

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

> Disclaimer, this is a personal project and not affiliated with Redis. No guarantees are provided.

An enhanced Redis CLI shell built with Python that goes beyond the standard `redis-cli`. Redis Shell provides a rich interactive experience with multi-connection management, data import/export, cluster management, and an extensible plugin architecture.

## ✨ Key Features

- 🚀 **Enhanced Interactive Shell** - Command history, autocompletion, and intuitive interface
- 🔗 **Multi-Connection Management** - Work with multiple Redis instances simultaneously
- 📊 **Data Import/Export** - Backup, migrate, and share Redis datasets with pattern matching
- 🏗️ **Cluster & Sentinel Support** - Deploy and manage Redis clusters and high-availability setups
- 🔧 **Extensible Architecture** - Create custom extensions for specialized functionality
- 🔒 **SSL/TLS Support** - Secure connections with certificate management
- ⚙️ **Flexible Configuration** - Environment variables, config files, and runtime settings

## 📚 Documentation

- **[Getting Started](docs/getting_started.md)** - Step-by-step tutorial for new users
- **[User Guide](docs/user_guide.md)** - Comprehensive usage documentation
- **[Built-in Extensions](docs/built_in_extensions.md)** - Reference for all built-in extensions
- **[Configuration](docs/configuration.md)** - Complete configuration reference
- **[Extension Development](docs/extension_development.md)** - Guide for creating custom extensions
- **[Architecture](docs/architecture.md)** - Technical architecture overview
- **[API Reference](docs/api_reference.md)** - API documentation for developers
- **[Troubleshooting](docs/troubleshooting.md)** - Solutions for common issues

## 🚀 Quick Start

### Installation

#### For End Users (Recommended)

Create a standalone executable using PEX:

```bash
# Install PEX in a virtual environment
uv venv && source .venv/bin/activate
uv pip install pex

# Create the executable
pex . -D . -e redis_shell.__main__:main -o redis-shell.pex --venv --strip-pex-env --no-compile --no-wheel --compress

# Run it
./redis-shell.pex
```

#### For Developers

```bash
# Clone and install in development mode
git clone <repository-url>
cd redis-shell
uv venv && source .venv/bin/activate
uv pip install -e .

# Run directly
redis-shell
```

### First Connection

```bash
# Connect to local Redis
redis-shell

# Connect to remote Redis with authentication
redis-shell --host redis.example.com --port 6379 --password mypassword

# Connect with SSL
redis-shell --host secure-redis.com --port 6380 --ssl
```


## 💡 Usage Examples

### Basic Redis Operations

```bash
# Start Redis Shell
redis-shell

# Standard Redis commands work as expected
localhost:6379> SET greeting "Hello, Redis Shell!"
OK
localhost:6379> GET greeting
"Hello, Redis Shell!"

# Hash operations
localhost:6379> HSET user:1001 name "Alice" email "alice@example.com"
(integer) 2
localhost:6379> HGETALL user:1001
1) "name"
2) "Alice"
3) "email"
4) "alice@example.com"
```

### Shell Commands

```bash
# View command history
localhost:6379> /history
Command history:
  1: SET greeting "Hello, Redis Shell!"
  2: GET greeting
  3: HSET user:1001 name "Alice" email "alice@example.com"

# Re-run a command from history
localhost:6379> /history 2
Running command: GET greeting
"Hello, Redis Shell!"

# Get help
localhost:6379> /help
Available commands:
  /clear - Clear screen
  /exit - Exit shell
  /help - Show help message
  /history - Show command history
```

### Multi-Connection Management

```bash
# Create additional connections
localhost:6379> /connection create --host redis2.example.com --port 6379
Connection created with ID: 2

# List all connections
localhost:6379> /connection list
Connections:
* 1: localhost:6379 (db: 0) [Current]
  2: redis2.example.com:6379 (db: 0)

# Switch between connections
localhost:6379> /connection use 2
Switched to connection 2
redis2.example.com:6379>
```

### Data Import/Export

```bash
# Export all data
localhost:6379> /data export
Export completed: redis-export-20240118-143022-localhost-6379.txt

# Export with pattern matching
localhost:6379> /data export --pattern "user:*"
Export completed: redis-export-20240118-143045-localhost-6379.txt

# Import data
localhost:6379> /data import --file redis-export-20240118-143022-localhost-6379.txt
Import completed: 1,234 keys imported
```

### Cluster Management

```bash
# Deploy a local Redis cluster for testing
localhost:6379> /cluster deploy
Deploying Redis cluster...
Cluster deployed successfully!

# Get cluster information
localhost:6379> /cluster info
Redis Cluster Information:
Status: Running
Nodes: 6 (3 masters, 3 replicas)

# Clean up
localhost:6379> /cluster remove
Cluster removed successfully!
```

## 🔧 Command Line Options

### Connection Options
```bash
redis-shell --host redis.example.com --port 6379 --db 1 --password secret
```

### SSL/TLS Options
```bash
redis-shell --ssl --ssl-ca-certs /path/to/ca.crt --ssl-cert-reqs required
```

### Other Options
```bash
redis-shell --log-level debug --config-file /path/to/config.json
redis-shell --command "GET mykey"  # Execute single command and exit
```

## 🌍 Environment Variables

Set these environment variables for default connection settings:

```bash
export REDIS_HOST=redis.example.com
export REDIS_PORT=6379
export REDIS_PASSWORD=mypassword
export REDIS_SHELL_LOG_LEVEL=debug
export REDIS_SHELL_CONFIG=/path/to/config.json
```

For a complete list of options, see the [Configuration Guide](docs/configuration.md).

## 🔌 Built-in Extensions

Redis Shell comes with powerful built-in extensions:

### 📊 Data Extension (`/data`)
- **Export/Import**: Backup and restore Redis data with pattern matching
- **Status Monitoring**: Track progress of long-running operations
- **Format Support**: Handle different Redis data types automatically

### 🔗 Connection Extension (`/connection`)
- **Multi-Connection**: Manage multiple Redis instances simultaneously
- **SSL Support**: Secure connections with certificate management
- **Connection Switching**: Seamlessly switch between different Redis servers

### 🏗️ Cluster Extension (`/cluster`)
- **Local Deployment**: Deploy Redis clusters for development and testing
- **Cluster Management**: Start, stop, and monitor cluster status
- **Node Information**: Detailed cluster topology and slot distribution

### 🛡️ Sentinel Extension (`/sentinel`)
- **High Availability**: Deploy Redis Sentinel for failover testing
- **Monitoring**: Track master-replica relationships
- **Failover Testing**: Test high availability scenarios locally

### ⚙️ Config Extension (`/config`)
- **Runtime Configuration**: Modify settings without restarting
- **Persistent Settings**: Save configuration changes to disk
- **Environment Management**: Different configs for different environments

For detailed documentation on each extension, see the [Built-in Extensions Guide](docs/built_in_extensions.md).

## 🛠️ Creating Custom Extensions

Redis Shell's extensible architecture allows you to create custom extensions for specialized functionality.

### Quick Example

1. **Create extension directory:**
   ```bash
   mkdir -p ~/.config/redis-shell/extensions/myext
   ```

2. **Create `extension.json`:**
   ```json
   {
     "name": "myext",
     "version": "1.0.0",
     "description": "My custom extension",
     "namespace": "/myext",
     "commands": [
       {
         "name": "hello",
         "description": "Say hello",
         "usage": "/myext hello [name]"
       }
     ]
   }
   ```

3. **Create `commands.py`:**
   ```python
   class MyextCommands:
       def __init__(self, cli=None):
           self.cli = cli

       def handle_command(self, cmd, args):
           if cmd == "hello":
               name = args[0] if args else "World"
               return f"Hello, {name}!"
           return None
   ```

4. **Restart Redis Shell to load the extension**

For comprehensive extension development documentation, see the [Extension Development Guide](docs/extension_development.md).

## 🏗️ Architecture

Redis Shell is built with a modular architecture that promotes extensibility and maintainability:

- **Core Engine**: Handles command processing, connection management, and user interaction
- **Extension System**: Plugin architecture for adding custom functionality
- **State Management**: Persistent storage for configuration and history
- **Connection Manager**: Multi-connection support with cluster detection
- **UI Layer**: Interactive shell with autocompletion and history

For detailed architecture information, see the [Architecture Guide](docs/architecture.md).

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `python -m pytest`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/redis-shell.git
cd redis-shell

# Set up development environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
python -m pytest

# Run with development settings
redis-shell --log-level debug
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Python](https://python.org/) and [redis-py](https://github.com/redis/redis-py)
- Interactive features powered by [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
- Inspired by the Redis community and the need for better Redis tooling

## 📞 Support

- **Documentation**: Check our comprehensive [documentation](docs/)
- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/yourusername/redis-shell/issues)
- **Discussions**: Join the conversation in [GitHub Discussions](https://github.com/yourusername/redis-shell/discussions)

---

**Redis Shell** - Making Redis interaction more powerful and enjoyable! 🚀
