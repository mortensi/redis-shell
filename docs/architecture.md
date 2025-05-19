# Architecture

## Core Components

1. `main.py`: Entry point that processes command-line arguments and initializes the CLI.
2. `RedisCLI`: Main class that handles user input, command processing, and interactive shell functionality.
3. `StateManager` (Singleton): Manages persistent state across sessions, including command history and extension-specific state.
4. `ConnectionManager (Singleton)`: Manages Redis connections, detects cluster configurations, and provides Redis clients to other components.
5. `ExtensionManager`: Loads and manages extensions from built-in, system, and user directories.

## Extensions System
Redis-Shell has a modular extension system with:

1. Built-in Extensions:
    - `/connection`: Manages Redis connections
    - `/data`: Handles data import/export
    - `/cluster`: Manages Redis clusters
    - `/config`: Manages configuration
    - `/sentinel`: Manages Redis Sentinel
2. External Extensions: Can be loaded from system and user extension directories.
3. Extension Structure:
    - `extension.json`: Defines metadata, commands, and completions
    - `commands.py`: Implements command functionality
    - Each extension has a Commands class that handles its specific commands

## Command Flow
1. User enters a command in the interactive shell
2. RedisCLI parses the command
3. If it's a shell command (starts with `/`), it's handled by `handle_shell_command`
4. If it's an extension command, it's passed to the appropriate extension via `ExtensionManager`

## State Management
The StateManager ensures persistent state across sessions by:

1. Storing state in a JSON file (default: `~/.redis-shell`)
2. Providing methods for extensions to store and retrieve their state
3. Maintaining command history

## Connection Management
The ConnectionManager:

1. Maintains a registry of Redis connections
2. Automatically detects Redis clusters
3. Creates appropriate Redis clients (standard or cluster)
4. Provides connection information to extensions

This architecture allows for a modular, extensible CLI that can be easily enhanced with new functionality through the extension system.

```
+---------------------------------------------+
|                redis-shell                  |
+---------------------------------------------+
                     |
                     v
+---------------------------------------------+
|                  __main__                   |
|  (Entry point with command-line arguments)  |
+---------------------------------------------+
                     |
                     v
+---------------------------------------------+
|                 RedisCLI                    |
| (Main CLI class that handles user input)    |
+---------------------------------------------+
          |           |           |
          v           v           v
+----------------+  +----------------+  +----------------+
| StateManager   |  | ConnectionMgr  |  | ExtensionMgr   |
| (Singleton)    |  | (Singleton)    |  | (Loads/manages |
| (Manages state |  | (Manages Redis |  |  extensions)   |
|  persistence)  |  |  connections)  |  |                |
+----------------+  +----------------+  +----------------+
          ^                 ^                   |
          |                 |                   |
          +-----------------+                   |
                 |                              |
                 |          +-------------------+
                 |          |
                 v          v
    +----------------------------------+
    |           Extensions             |
    |  +----------------------------+  |
    |  | Built-in Extensions        |  |
    |  | +-----------------------+  |  |
    |  | | /connection           |  |  |
    |  | | (Connection manager)  |  |  |
    |  | +-----------------------+  |  |
    |  | +-----------------------+  |  |
    |  | | /data                 |  |  |
    |  | | (Data import/export)  |  |  |
    |  | +-----------------------+  |  |
    |  | +-----------------------+  |  |
    |  | | /cluster              |  |  |
    |  | | (Cluster management)  |  |  |
    |  | +-----------------------+  |  |
    |  | +-----------------------+  |  |
    |  | | /config               |  |  |
    |  | | (Config management)   |  |  |
    |  | +-----------------------+  |  |
    |  | +-----------------------+  |  |
    |  | | /sentinel             |  |  |
    |  | | (Sentinel management) |  |  |
    |  | +-----------------------+  |  |
    |  +----------------------------+  |
    |                                  |
    |  +----------------------------+  |
    |  | External Extensions        |  |
    |  | (Loaded from system and    |  |
    |  |  user extension dirs)      |  |
    |  +----------------------------+  |
    +----------------------------------+
                 |
                 v
    +----------------------------------+
    |           Redis Client           |
    | (Connects to Redis instances)    |
    +----------------------------------+
                 |
                 v
    +----------------------------------+
    |           Redis Server           |
    | (Local or remote Redis instance) |
    +----------------------------------+
```

