# Getting Started with Redis Shell

This tutorial will walk you through installing and using Redis Shell for the first time. By the end of this guide, you'll be comfortable with the basic features and ready to explore advanced functionality.

## Prerequisites

- Python 3.8 or higher
- A Redis server (local or remote)
- Basic familiarity with command-line interfaces

## Step 1: Installation

### Option A: Quick Installation (Recommended)

1. **Create a virtual environment:**
   ```bash
   python -m venv redis-shell-env
   source redis-shell-env/bin/activate  # On Windows: redis-shell-env\Scripts\activate
   ```

2. **Install uv (fast Python package manager):**
   ```bash
   pip install uv
   ```

3. **Clone and install Redis Shell:**
   ```bash
   git clone <repository-url>
   cd redis-shell
   uv pip install -e .
   ```

### Option B: Standalone Executable

1. **Create a PEX executable:**
   ```bash
   uv pip install pex
   pex . -D . -e redis_shell.__main__:main -o redis-shell.pex --venv --strip-pex-env --no-compile --no-wheel --compress
   ```

2. **Make it executable and run:**
   ```bash
   chmod +x redis-shell.pex
   ./redis-shell.pex
   ```

## Step 2: Start Redis Server

If you don't have Redis running, start it:

```bash
# Using Docker (recommended for testing)
docker run -d --name redis-test -p 6379:6379 redis:latest

# Or install Redis locally
# On macOS: brew install redis && brew services start redis
# On Ubuntu: sudo apt install redis-server && sudo systemctl start redis
```

## Step 3: First Connection

1. **Start Redis Shell:**
   ```bash
   redis-shell
   ```

2. **You should see a welcome message:**
   ```
   Welcome to Redis Shell v0.1.0
   Connected to Redis. Type '/help' for available commands.
   Commands starting with '/' are shell commands, all other commands are passed directly to Redis.
   localhost:6379>
   ```

3. **Test the connection:**
   ```bash
   localhost:6379> PING
   PONG
   ```

Congratulations! You're now connected to Redis through Redis Shell.

## Step 4: Basic Redis Commands

Let's try some basic Redis operations:

### String Operations
```bash
# Set a key-value pair
localhost:6379> SET greeting "Hello, Redis Shell!"
OK

# Get the value
localhost:6379> GET greeting
"Hello, Redis Shell!"

# Set with expiration (10 seconds)
localhost:6379> SETEX temp_key 10 "This will expire"
OK

# Check if key exists
localhost:6379> EXISTS greeting
(integer) 1
```

### Hash Operations
```bash
# Create a hash for user data
localhost:6379> HSET user:1001 name "Alice" email "alice@example.com" age 30
(integer) 3

# Get a specific field
localhost:6379> HGET user:1001 name
"Alice"

# Get all fields and values
localhost:6379> HGETALL user:1001
1) "name"
2) "Alice"
3) "email"
4) "alice@example.com"
5) "age"
6) "30"
```

### List Operations
```bash
# Create a list
localhost:6379> LPUSH tasks "Write documentation" "Review code" "Deploy app"
(integer) 3

# View the list
localhost:6379> LRANGE tasks 0 -1
1) "Deploy app"
2) "Review code"
3) "Write documentation"

# Pop an item
localhost:6379> LPOP tasks
"Deploy app"
```

## Step 5: Shell Commands

Redis Shell provides built-in shell commands that start with `/`:

### View Command History
```bash
localhost:6379> /history
Command history:
  1: PING
  2: SET greeting "Hello, Redis Shell!"
  3: GET greeting
  4: HSET user:1001 name "Alice" email "alice@example.com" age 30
  5: HGETALL user:1001
```

### Re-run a Command from History
```bash
localhost:6379> /history 3
Running command: GET greeting
Executed: GET greeting
"Hello, Redis Shell!"
```

### Get Help
```bash
localhost:6379> /help
Available commands:
  /clear - Clear screen
  /exit - Exit shell
  /help - Show help message
  /history - Show command history

Extension commands:
  /connection - Connection management commands
  /data - Data import/export commands
  /cluster - Cluster management commands
  /sentinel - Sentinel management commands
  /config - Configuration management commands
```

### Clear Screen
```bash
localhost:6379> /clear
```

## Step 6: Using Extensions

Redis Shell's power comes from its extensions. Let's explore some built-in ones:

### Data Export/Import

1. **Export your data:**
   ```bash
   localhost:6379> /data export
   Scanning keys...
   Found 3 keys to export
   Exporting keys...
   Export completed: redis-export-20240118-143022-localhost-6379.txt
   ```

2. **Export specific patterns:**
   ```bash
   localhost:6379> /data export --pattern "user:*"
   Scanning keys matching pattern 'user:*'...
   Found 1 keys to export
   Export completed: redis-export-20240118-143045-localhost-6379.txt
   ```

3. **Import data (after creating some test data):**
   ```bash
   localhost:6379> /data import --file redis-export-20240118-143022-localhost-6379.txt
   Importing data from redis-export-20240118-143022-localhost-6379.txt...
   Import completed: 3 keys imported
   ```

### Connection Management

1. **Create a second connection (if you have another Redis instance):**
   ```bash
   localhost:6379> /connection create --host localhost --port 6380 --db 1
   Connection created with ID: 2
   ```

2. **List all connections:**
   ```bash
   localhost:6379> /connection list
   Connections:
   * 1: localhost:6379 (db: 0)
     2: localhost:6380 (db: 1)
   ```

3. **Switch connections:**
   ```bash
   localhost:6379> /connection use 2
   Switched to connection 2
   localhost:6380>
   ```

### Configuration Management

1. **View current configuration:**
   ```bash
   localhost:6379> /config get --all
   [general]
   history_size = 100
   log_level = info
   
   [redis]
   default_host = 127.0.0.1
   default_port = 6379
   ...
   ```

2. **Change a setting:**
   ```bash
   localhost:6379> /config set general history_size 200
   Configuration updated: general.history_size = 200
   ```

3. **Save configuration:**
   ```bash
   localhost:6379> /config save
   Configuration saved to ~/.redis-shell
   ```

## Step 7: Advanced Features

### Tab Completion

Redis Shell provides intelligent tab completion:

1. **Try typing `/data ` and press Tab:**
   ```bash
   localhost:6379> /data [TAB]
   export  import  status
   ```

2. **Try typing `/data export --` and press Tab:**
   ```bash
   localhost:6379> /data export --[TAB]
   --cancel      --folder      --force-keys  --pattern
   ```

### Command Line Execution

You can execute single commands without entering interactive mode:

```bash
# Execute a Redis command
redis-shell -x "GET greeting"

# Execute a shell command
redis-shell -x "/data export --pattern 'user:*'"
```

### Using Different Connection Options

```bash
# Connect to a remote Redis with authentication
redis-shell --host redis.example.com --port 6379 --password mypassword

# Connect using SSL
redis-shell --host secure-redis.com --port 6380 --ssl

# Connect to a specific database
redis-shell --host localhost --port 6379 --db 2
```

## Step 8: What's Next?

Now that you're familiar with the basics, here are some next steps:

1. **Explore Built-in Extensions**: Try the cluster and sentinel extensions if you have those setups
2. **Create Custom Extensions**: Learn how to create your own extensions (see [Extension Development Guide](extension_development.md))
3. **Configure Your Environment**: Set up a configuration file for your preferred settings
4. **Read the User Guide**: Check out the [User Guide](user_guide.md) for comprehensive documentation

## Common First-Time Issues

### Connection Refused
```bash
Error: Connection refused
```
**Solution**: Make sure Redis server is running on the specified host and port.

### Permission Denied
```bash
Error: Permission denied when creating config file
```
**Solution**: Check that you have write permissions to your home directory.

### Command Not Found
```bash
redis-shell: command not found
```
**Solution**: Make sure you've activated your virtual environment or the executable is in your PATH.

## Getting Help

- Use `/help` in the shell for available commands
- Check the [User Guide](user_guide.md) for detailed documentation
- See [Troubleshooting Guide](troubleshooting.md) for common issues
- Review [API Reference](api_reference.md) for extension development

Welcome to Redis Shell! You're now ready to explore its powerful features.
