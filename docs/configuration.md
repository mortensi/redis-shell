# Configuration Reference

Redis Shell provides extensive configuration options to customize its behavior. This document covers all available configuration options, their default values, and usage examples.

## Table of Contents

- [Configuration File Locations](#configuration-file-locations)
- [Configuration File Format](#configuration-file-format)
- [Configuration Sections](#configuration-sections)
- [Environment Variables](#environment-variables)
- [Command Line Options](#command-line-options)
- [Runtime Configuration](#runtime-configuration)
- [Examples](#examples)

## Configuration File Locations

Redis Shell searches for configuration files in the following order:

1. **Environment Variable**: Path specified by `REDIS_SHELL_CONFIG`
2. **User Home**: `~/.redis-shell` (legacy format)
3. **XDG Config**: `~/.config/redis-shell/config.json`
4. **System Wide**: `/etc/redis-shell/config.json`

If no configuration file is found, Redis Shell creates a default one at `~/.redis-shell`.

### Creating Configuration Directory

```bash
# Create the configuration directory
mkdir -p ~/.config/redis-shell

# Redis Shell will create the config file on first run
redis-shell
```

## Configuration File Format

Redis Shell supports JSON format for configuration files:

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
    "ssl": false,
    "ssl_ca_certs": null,
    "ssl_ca_path": null,
    "ssl_keyfile": null,
    "ssl_certfile": null,
    "ssl_cert_reqs": "required"
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

## Configuration Sections

### General Section

Controls general application behavior.

#### `history_size`
- **Type**: Integer
- **Default**: `100`
- **Description**: Maximum number of commands to keep in history
- **Example**: 
  ```json
  "history_size": 200
  ```

#### `log_level`
- **Type**: String
- **Default**: `"info"`
- **Valid Values**: `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`
- **Description**: Logging verbosity level
- **Example**:
  ```json
  "log_level": "debug"
  ```

#### `log_file`
- **Type**: String or null
- **Default**: `null`
- **Description**: Path to log file. If null, logs to console only
- **Example**:
  ```json
  "log_file": "~/.config/redis-shell/redis-shell.log"
  ```

#### `state_file`
- **Type**: String
- **Default**: `"~/.redis-shell"`
- **Description**: Path to state file for persistent data
- **Example**:
  ```json
  "state_file": "~/.config/redis-shell/state.json"
  ```

### Redis Section

Controls Redis connection defaults.

#### `default_host`
- **Type**: String
- **Default**: `"127.0.0.1"`
- **Description**: Default Redis host for new connections
- **Example**:
  ```json
  "default_host": "redis.example.com"
  ```

#### `default_port`
- **Type**: Integer
- **Default**: `6379`
- **Description**: Default Redis port for new connections
- **Example**:
  ```json
  "default_port": 6380
  ```

#### `default_db`
- **Type**: Integer
- **Default**: `0`
- **Description**: Default Redis database number
- **Example**:
  ```json
  "default_db": 1
  ```

#### `default_username`
- **Type**: String
- **Default**: `"default"`
- **Description**: Default Redis username for authentication
- **Example**:
  ```json
  "default_username": "myuser"
  ```

#### `default_password`
- **Type**: String
- **Default**: `""`
- **Description**: Default Redis password for authentication
- **Example**:
  ```json
  "default_password": "mypassword"
  ```

#### `timeout`
- **Type**: Integer
- **Default**: `5`
- **Description**: Connection timeout in seconds
- **Example**:
  ```json
  "timeout": 10
  ```

#### `decode_responses`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Whether to decode Redis responses to strings
- **Example**:
  ```json
  "decode_responses": true
  ```

#### SSL/TLS Configuration

#### `ssl`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable SSL/TLS connections by default
- **Example**:
  ```json
  "ssl": true
  ```

#### `ssl_ca_certs`
- **Type**: String or null
- **Default**: `null`
- **Description**: Path to CA certificate file
- **Example**:
  ```json
  "ssl_ca_certs": "/etc/ssl/certs/ca-certificates.crt"
  ```

#### `ssl_ca_path`
- **Type**: String or null
- **Default**: `null`
- **Description**: Path to directory containing CA certificates
- **Example**:
  ```json
  "ssl_ca_path": "/etc/ssl/certs/"
  ```

#### `ssl_keyfile`
- **Type**: String or null
- **Default**: `null`
- **Description**: Path to private key file
- **Example**:
  ```json
  "ssl_keyfile": "~/.config/redis-shell/client.key"
  ```

#### `ssl_certfile`
- **Type**: String or null
- **Default**: `null`
- **Description**: Path to certificate file
- **Example**:
  ```json
  "ssl_certfile": "~/.config/redis-shell/client.crt"
  ```

#### `ssl_cert_reqs`
- **Type**: String
- **Default**: `"required"`
- **Valid Values**: `"none"`, `"optional"`, `"required"`
- **Description**: Certificate verification requirements
- **Example**:
  ```json
  "ssl_cert_reqs": "optional"
  ```

### Extensions Section

Controls extension loading and behavior.

#### `extension_dir`
- **Type**: String
- **Default**: `"~/.config/redis-shell/extensions"`
- **Description**: Directory containing user extensions
- **Example**:
  ```json
  "extension_dir": "/opt/redis-shell/extensions"
  ```

### UI Section

Controls user interface appearance.

#### `prompt_style`
- **Type**: String
- **Default**: `"green"`
- **Valid Values**: Color names or ANSI codes
- **Description**: Color style for the command prompt
- **Example**:
  ```json
  "prompt_style": "blue"
  ```

#### `error_style`
- **Type**: String
- **Default**: `"red"`
- **Description**: Color style for error messages
- **Example**:
  ```json
  "error_style": "bright_red"
  ```

#### `warning_style`
- **Type**: String
- **Default**: `"yellow"`
- **Description**: Color style for warning messages

#### `success_style`
- **Type**: String
- **Default**: `"green"`
- **Description**: Color style for success messages

#### `info_style`
- **Type**: String
- **Default**: `"blue"`
- **Description**: Color style for informational messages

## Environment Variables

Environment variables override configuration file settings:

### Connection Variables
- `REDIS_HOST`: Override default_host
- `REDIS_PORT`: Override default_port
- `REDIS_DB`: Override default_db
- `REDIS_USERNAME`: Override default_username
- `REDIS_PASSWORD`: Override default_password

### Application Variables
- `REDIS_SHELL_CONFIG`: Path to configuration file
- `REDIS_SHELL_LOG_LEVEL`: Override log_level
- `REDIS_SHELL_LOG_FILE`: Override log_file

### Example Usage
```bash
export REDIS_HOST=redis.example.com
export REDIS_PORT=6380
export REDIS_PASSWORD=secret123
export REDIS_SHELL_LOG_LEVEL=debug
redis-shell
```

## Command Line Options

Command line options have the highest priority:

### Connection Options
```bash
redis-shell --host redis.example.com --port 6379 --db 1 --password secret
```

### SSL Options
```bash
redis-shell --ssl --ssl-ca-certs /path/to/ca.crt --ssl-cert-reqs required
```

### Application Options
```bash
redis-shell --log-level debug --log-file /tmp/redis-shell.log --config-file /path/to/config.json
```

## Runtime Configuration

Use the `/config` extension to modify configuration at runtime:

### View Configuration
```bash
# View all configuration
localhost:6379> /config get --all

# View specific section
localhost:6379> /config get general

# View specific setting
localhost:6379> /config get redis default_host
```

### Modify Configuration
```bash
# Change a setting
localhost:6379> /config set general history_size 200

# Change Redis defaults
localhost:6379> /config set redis default_host redis.example.com

# Save changes to disk
localhost:6379> /config save
```

## Examples

### Development Environment
```json
{
  "general": {
    "history_size": 500,
    "log_level": "debug",
    "log_file": "~/.config/redis-shell/debug.log"
  },
  "redis": {
    "default_host": "localhost",
    "default_port": 6379,
    "timeout": 10
  },
  "ui": {
    "prompt_style": "cyan",
    "error_style": "bright_red"
  }
}
```

### Production Environment
```json
{
  "general": {
    "history_size": 100,
    "log_level": "warning",
    "log_file": "/var/log/redis-shell.log"
  },
  "redis": {
    "default_host": "redis-prod.example.com",
    "default_port": 6380,
    "ssl": true,
    "ssl_ca_certs": "/etc/ssl/certs/ca-bundle.crt",
    "ssl_cert_reqs": "required",
    "timeout": 30
  }
}
```

### Multi-Environment Setup
```bash
# Development
export REDIS_SHELL_CONFIG=~/.config/redis-shell/dev-config.json
redis-shell

# Staging
export REDIS_SHELL_CONFIG=~/.config/redis-shell/staging-config.json
redis-shell

# Production
export REDIS_SHELL_CONFIG=~/.config/redis-shell/prod-config.json
redis-shell
```

### SSL Configuration Example
```json
{
  "redis": {
    "default_host": "secure-redis.example.com",
    "default_port": 6380,
    "ssl": true,
    "ssl_ca_certs": "~/.config/redis-shell/ca.crt",
    "ssl_certfile": "~/.config/redis-shell/client.crt",
    "ssl_keyfile": "~/.config/redis-shell/client.key",
    "ssl_cert_reqs": "required"
  }
}
```

### Custom Extension Directory
```json
{
  "extensions": {
    "extension_dir": "/opt/company/redis-shell-extensions"
  }
}
```

## Configuration Validation

Redis Shell validates configuration on startup. Common validation errors:

### Invalid JSON Syntax
```bash
Error: Invalid JSON in configuration file
```
**Solution**: Validate JSON syntax using `python -m json.tool config.json`

### Invalid Values
```bash
Error: Invalid log_level 'invalid'
```
**Solution**: Use valid values as documented above

### File Permissions
```bash
Error: Cannot read configuration file
```
**Solution**: Check file permissions with `ls -la config.json`

## Best Practices

1. **Use Environment Variables**: For sensitive data like passwords
2. **Separate Environments**: Use different config files for dev/staging/prod
3. **Version Control**: Keep configuration files in version control (excluding secrets)
4. **Backup**: Keep backups of working configurations
5. **Validation**: Test configuration changes in development first
