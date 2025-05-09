# Redis Shell

An enhanced Redis CLI shell built with Python, providing both a structured command mode and a direct RESP mode for Redis operations.

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

The shell supports two modes, command autocompletion, and several utility commands:

#### Autocompletion
Press `Tab` to show available commands and their descriptions. The shell provides:
- Shell command completion (always available)
- Redis command completion (in shell mode)
- Cluster command completion (in shell mode)

#### Commands

- `/shell`: Switch to shell mode (default) - Commands are validated before execution
- `/resp`: Switch to RESP mode - Direct Redis protocol mode, like redis-cli
- `/clear`: Clear the screen
- `/help`: Show help message
- `/exit`: Exit the shell

### Examples

```bash
# Start the shell
redis-shell

# In shell mode (default)
redis> SET mykey "Hello World"
OK
redis> GET mykey
"Hello World"

# Switch to RESP mode
redis> /resp
Switched to RESP mode. Use Redis commands directly.
[RESP] redis> HSET user:1 name "John" age "30"
(integer) 2
[RESP] redis> HGETALL user:1
1) "name"
2) "John"
3) "age"
4) "30"

# Switch back to shell mode
[RESP] redis> /shell
Switched to shell mode.
```

### Cluster Management

In shell mode, you can deploy and manage Redis clusters:

```bash
# Deploy a cluster with default settings (3 masters, 3 replicas, starting at port 30000)
redis> deployCluster

# Deploy a custom cluster (5 masters, 5 replicas, starting at port 40000)
redis> deployCluster 40000 1 5

# Get cluster information
redis> clusterInfo

# Stop and clean up the cluster
redis> stopCluster
```

Cluster deployment parameters:
- `basePort`: Starting port number (default: 30000)
- `replicas`: Number of replicas per master (default: 1)
- `nodesPerReplica`: Number of master nodes (default: 3)

The total number of nodes will be `nodesPerReplica * (replicas + 1)`.
