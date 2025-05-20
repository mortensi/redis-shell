# Redis Shell

An enhanced Redis CLI shell built with Python, providing a unified interface for both Redis commands and extension commands.

## Installation for Users

You can build and use the executable using `npx`. From a virtual environment:

```
uv pip install pex

pex . -D . -e redis_shell.__main__:main -o redis-shell.pex --venv --strip-pex-env --no-compile --no-wheel --compres
```

and launch it as `./redis-shell.pex`


## Installation for Developers

If you want to contribute or modify the code:

1. Clone this repository
2. Create a virtual environment and install the package:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Now you can run it as `redis-shell`


## Usage

Start the Redis Shell:

```bash
redis-shell [OPTIONS]
```

### Connection Options
- `-h, --host TEXT`: Redis host (default: 127.0.0.1)
- `-p, --port INTEGER`: Redis port (default: 6379)
- `-n, --db INTEGER`: Redis database number (default: 0)
- `-u, --username TEXT`: Redis username (default: default)
- `-a, --password TEXT`: Redis password

### SSL/TLS Options
- `--ssl`: Enable SSL/TLS connection
- `--ssl-ca-certs TEXT`: Path to CA certificate file
- `--ssl-ca-path TEXT`: Path to CA certificates directory
- `--ssl-keyfile TEXT`: Path to private key file
- `--ssl-certfile TEXT`: Path to certificate file
- `--ssl-cert-reqs [none|optional|required]`: Certificate requirements (default: required)

### Configuration and Logging Options
- `-c, --config-file TEXT`: Path to configuration file
- `-l, --log-level TEXT`: Log level (debug, info, warning, error, critical)
- `-f, --log-file TEXT`: Path to log file

### Other Options
- `-x, --command TEXT`: Execute a command and exit
- `-v, --version`: Show version and exit
- `--help`: Show help message and exit

### Environment Variables
- `REDIS_HOST`: Redis host (default: 127.0.0.1)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_USERNAME`: Redis username (default: default)
- `REDIS_PASSWORD`: Redis password
- `REDIS_SHELL_CONFIG`: Path to configuration file
- `REDIS_SHELL_LOG_LEVEL`: Log level (debug, info, warning, error, critical)
- `REDIS_SHELL_LOG_FILE`: Path to log file

### Configuration File Locations
Redis Shell looks for configuration files in the following locations (in order):

1. Path specified by `REDIS_SHELL_CONFIG` environment variable
2. `~/.redis-shell`
3. `~/.config/redis-shell/config.json`
4. `/etc/redis-shell/config.json`

If no configuration file is found, a default one is created at `~/.redis-shell`.

### Shell Commands

The shell provides command autocompletion and several utility commands:

#### Autocompletion
Press `Tab` to show available commands and their descriptions. The shell provides:
- Shell command completion (commands starting with `/`)
- Extension command completion (like `/cluster`, `/data`, `/connection`, etc.)

#### Commands

- `/clear`: Clear the screen
- `/help`: Show help message
- `/exit`: Exit the shell
- `/history`: Show command history
  - Use `/history clear` to clear history
  - Use `/history <number>` to run a specific command from history

### Examples

```bash
# Start the shell
redis-shell

# Direct Redis commands
localhost:6379> SET mykey "Hello World"
OK
localhost:6379> GET mykey
"Hello World"

# Hash operations
localhost:6379> HSET user:1 name "John" age "30"
(integer) 2
redis> HGETALL user:1
1) "name"
2) "John"
3) "age"
4) "30"

# View command history
localhost:6379> /history
Command history:
  1: SET mykey "Hello World"
  2: GET mykey
  3: HSET user:1 name "John" age "30"
  4: HGETALL user:1

# Run a command from history by its number
localhost:6379> /history 2
Running command: GET mykey
Executed: GET mykey
"Hello World"
```

### Extensions

Redis Shell has an extensible architecture that allows you to create and use custom extensions. Extensions are loaded from two locations:

1. **Built-in Extensions**: Located in the package's `redis_shell/extensions` directory
2. **User Extensions**: Located in `~/.config/redis-shell/extensions` directory

The shell provides several built-in extension commands for advanced functionality:

#### Cluster Management

```bash
# Deploy a cluster with default settings (3 masters, 3 replicas, starting at port 30000)
redis> /cluster deploy

# Get cluster information
redis> /cluster info

# Stop and clean up the cluster
redis> /cluster remove
```

#### Data Import/Export

```bash
# Export all keys to a file
redis> /data export

# Export keys matching a pattern
redis> /data export --pattern "user:*"

# Import data from a file
redis> /data import --file redis-export-20230101-123456-localhost-6379.txt

# Check export/import status
redis> /data status
```

#### Connection Management

```bash
# Create a new connection
redis> /connection create --host redis.example.com --port 6379

# List all connections
redis> /connection list

# Switch to a different connection
redis> /connection use 2

# Remove a connection
redis> /connection destroy 2
```

#### Sentinel Management

```bash
# Deploy a Redis Sentinel setup
redis> /sentinel deploy

# Get Sentinel information
redis> /sentinel info

# Remove the Sentinel setup
redis> /sentinel remove
```

#### Creating Custom Extensions

You can create your own extensions to add custom functionality to Redis Shell. Extensions should be placed in the `~/.config/redis-shell/extensions` directory.

Each extension requires:
1. A directory with the extension name (e.g., `myextension`)
2. An `extension.json` file defining the extension
3. A `commands.py` file implementing the extension's commands

Example `extension.json`:
```json
{
    "name": "myextension",
    "version": "1.0.0",
    "description": "My custom extension for Redis Shell",
    "namespace": "/myext",
    "commands": [
        {
            "name": "hello",
            "description": "Say hello",
            "usage": "/myext hello [name]",
            "options": []
        }
    ],
    "author": "Your Name"
}
```

Example `commands.py`:
```python
class MyextensionCommands:
    def __init__(self, cli=None):
        self._cli = cli

    def handle_command(self, cmd: str, args: list) -> str:
        """Handle extension commands."""
        if cmd == "hello":
            name = args[0] if args else "World"
            return f"Hello, {name}!"
        return None
```

After creating your extension, restart Redis Shell to load it.
