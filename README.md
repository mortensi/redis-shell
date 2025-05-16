# Redis Shell

An enhanced Redis CLI shell built with Python, providing a unified interface for both Redis commands and extension commands.

## Installation

### For Users
Simply install the package using pip:
```bash
pip install redis-shell
```

Or with uv (recommended):
```bash
uv pip install redis-shell
```

### For Developers
If you want to contribute or modify the code:

1. Clone this repository
2. Create a virtual environment and install the package:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

## Building

You can build the executable using `npx`

```
uv pip install pex

pex . \
>   -D . \
>   -e redis_shell.cli:main \
>   -o redis-shell.pex \
>   --compile \
>   --venv
```

and launch it as `./redis-shell.pex`

## Usage

Start the Redis shell:
```bash
redis-shell [OPTIONS]
```

Options:
- `-h, --host TEXT`: Redis host (default: localhost)
- `-p, --port INTEGER`: Redis port (default: 6379)
- `-d, --db INTEGER`: Redis database number (default: 0)

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
redis> SET mykey "Hello World"
OK
redis> GET mykey
"Hello World"

# Hash operations
redis> HSET user:1 name "John" age "30"
(integer) 2
redis> HGETALL user:1
1) "name"
2) "John"
3) "age"
4) "30"

# View command history
redis> /history
Command history:
  1: SET mykey "Hello World"
  2: GET mykey
  3: HSET user:1 name "John" age "30"
  4: HGETALL user:1

# Run a command from history by its number
redis> /history 2
Running command: GET mykey
Executed: GET mykey
"Hello World"
```

### Extension Commands

The shell provides several extension commands for advanced functionality:

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
