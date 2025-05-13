# API Reference

This document provides a reference for the Redis Shell API.

## Table of Contents

- [Connection Manager](#connection-manager)
- [State Manager](#state-manager)
- [Extension Manager](#extension-manager)
- [Configuration](#configuration)
- [Utilities](#utilities)
  - [File Utilities](#file-utilities)
  - [Command Utilities](#command-utilities)
  - [Completion Utilities](#completion-utilities)
  - [Logging Utilities](#logging-utilities)
  - [Redis Utilities](#redis-utilities)

## Connection Manager

The `ConnectionManager` class manages Redis connections.

### Methods

#### `__init__(self)`

Initialize the connection manager.

#### `add_connection(self, connection_id, connection_info)`

Add a connection.

- `connection_id` - Connection ID
- `connection_info` - Connection information
  - `host` - Redis host
  - `port` - Redis port
  - `db` - Redis database number
  - `password` - Redis password

#### `get_connection(self, connection_id)`

Get a connection by ID.

- `connection_id` - Connection ID

Returns the connection information or `None` if not found.

#### `get_connections(self)`

Get all connections.

Returns a dictionary of connection IDs to connection information.

#### `remove_connection(self, connection_id)`

Remove a connection.

- `connection_id` - Connection ID

#### `set_current_connection_id(self, connection_id)`

Set the current connection ID.

- `connection_id` - Connection ID

Raises `ValueError` if the connection ID does not exist.

#### `get_current_connection_id(self)`

Get the current connection ID.

Returns the current connection ID or `None` if not set.

#### `get_connection_parameters(self)`

Get the current connection parameters.

Returns a tuple of `(host, port, db, password)`.

Raises `ValueError` if no current connection is set.

#### `get_redis_client(self)`

Get a Redis client for the current connection.

Returns a Redis client or `None` if no current connection is set.

#### `is_cluster_connection(self)`

Check if the current connection is a cluster connection.

Returns `True` if the current connection is a cluster connection, `False` otherwise.

## State Manager

The `StateManager` class manages application state.

### Methods

#### `__init__(self)`

Initialize the state manager.

#### `get_state(self, key, default=None)`

Get a state value.

- `key` - State key
- `default` - Default value if the key does not exist

Returns the state value or the default value if the key does not exist.

#### `set_state(self, key, value)`

Set a state value.

- `key` - State key
- `value` - State value

#### `get_command_history(self)`

Get the command history.

Returns a list of command strings.

#### `add_command_to_history(self, command)`

Add a command to the history.

- `command` - Command string

#### `clear_command_history(self)`

Clear the command history.

## Extension Manager

The `ExtensionManager` class manages extensions.

### Methods

#### `__init__(self, cli=None)`

Initialize the extension manager.

- `cli` - CLI instance

#### `load_extensions(self)`

Load all extensions.

#### `load_extension(self, extension_path)`

Load an extension from the given path.

- `extension_path` - Path to the extension directory

Returns the extension information.

#### `get_extension(self, namespace)`

Get an extension by namespace.

- `namespace` - Extension namespace

Returns the extension information or `None` if not found.

#### `handle_command(self, namespace, args)`

Handle a command.

- `namespace` - Extension namespace
- `args` - Command arguments

Returns the command result or `None` if the command is not handled.

#### `get_completions(self, text)`

Get completions for the given text.

- `text` - Text to complete

Returns a list of `(completion, description)` tuples.

## Configuration

The `Config` class manages application configuration.

### Methods

#### `__init__(self)`

Initialize the configuration manager.

#### `get(self, section, key, default=None)`

Get a configuration value.

- `section` - Configuration section
- `key` - Configuration key
- `default` - Default value if not found

Returns the configuration value or the default value if not found.

#### `set(self, section, key, value)`

Set a configuration value.

- `section` - Configuration section
- `key` - Configuration key
- `value` - Configuration value

#### `get_section(self, section)`

Get a configuration section.

- `section` - Configuration section

Returns the configuration section as a dictionary.

#### `get_all(self)`

Get the entire configuration.

Returns the entire configuration as a dictionary.

#### `save_config(self)`

Save the configuration to file.

## Utilities

### File Utilities

The `PathHandler` class provides utilities for file path operations.

#### `parse_path(incomplete)`

Parse an incomplete path into components.

- `incomplete` - The incomplete path string

Returns a tuple of `(base_dir, prefix, is_absolute, path_prefix)`.

#### `get_directory_completions(incomplete)`

Get directory completions for an incomplete path.

- `incomplete` - The incomplete path string

Returns a list of directory completions.

#### `get_file_completions(incomplete, pattern)`

Get file completions for an incomplete path matching a pattern.

- `incomplete` - The incomplete path string
- `pattern` - The glob pattern to match files against

Returns a list of file completions.

#### `get_path_completions(incomplete, file_pattern=None)`

Get completions for an incomplete path, including both directories and files.

- `incomplete` - The incomplete path string
- `file_pattern` - Optional glob pattern to match files against

Returns a list of path completions.

### Command Utilities

The `CommandParser` class provides utilities for command parsing.

#### `parse_command_line(command_line)`

Parse a command line into command and arguments.

- `command_line` - The command line to parse

Returns a tuple of `(command, args)`.

#### `create_argument_parser(description, options)`

Create an argument parser for a command.

- `description` - Command description
- `options` - List of option definitions

Returns an argument parser.

The `CommandFormatter` class provides utilities for formatting command output.

#### `format_table(headers, rows, padding=2)`

Format a table for display.

- `headers` - List of column headers
- `rows` - List of rows (each row is a list of column values)
- `padding` - Padding between columns

Returns a formatted table string.

#### `format_key_value(data, indent=0)`

Format a dictionary as key-value pairs.

- `data` - Dictionary to format
- `indent` - Indentation level

Returns a formatted string.

### Completion Utilities

The `CompletionRegistry` class manages completion providers.

#### `register(name, provider)`

Register a completion provider.

- `name` - The name of the provider
- `provider` - The completion provider

#### `get_provider(name)`

Get a completion provider by name.

- `name` - The name of the provider

Returns the completion provider, or `None` if not found.

#### `get_completions(name, text)`

Get completions from a provider.

- `name` - The name of the provider
- `text` - The text to complete

Returns a list of completions.

### Logging Utilities

The `setup_logging` function sets up logging for redis-shell.

#### `setup_logging(level='info', log_file=None, log_format=None)`

Set up logging for redis-shell.

- `level` - Log level (debug, info, warning, error, critical)
- `log_file` - Optional log file path
- `log_format` - Optional log format string

Returns a logger instance.

### Redis Utilities

The `RedisConnectionHelper` class provides utilities for Redis connection operations.

#### `create_redis_client(host='localhost', port=6379, db=0, password=None, decode_responses=False, ssl=False, ssl_ca_certs=None)`

Create a standard Redis client.

- `host` - Redis host
- `port` - Redis port
- `db` - Redis database number
- `password` - Redis password
- `decode_responses` - Whether to decode responses
- `ssl` - Whether to use SSL
- `ssl_ca_certs` - Path to CA certificates file

Returns a Redis client.

#### `is_cluster(client)`

Check if a Redis client is connected to a cluster.

- `client` - Redis client

Returns a tuple of `(is_cluster, nodes)`.

#### `create_cluster_client(nodes, password=None, decode_responses=False, ssl=False, ssl_ca_certs=None)`

Create a Redis cluster client.

- `nodes` - List of cluster nodes
- `password` - Redis password
- `decode_responses` - Whether to decode responses
- `ssl` - Whether to use SSL
- `ssl_ca_certs` - Path to CA certificates file

Returns a Redis cluster client.

#### `get_redis_info(client)`

Get Redis server information.

- `client` - Redis client

Returns a dictionary of Redis server information.

#### `format_redis_value(value)`

Format a Redis value for display.

- `value` - Redis value

Returns a formatted value string.
