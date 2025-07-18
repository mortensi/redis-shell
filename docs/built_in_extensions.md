# Built-in Extensions Reference

Redis Shell comes with several powerful built-in extensions that extend its functionality beyond basic Redis commands. Each extension provides a set of commands under a specific namespace.

## Table of Contents

- [Data Extension (`/data`)](#data-extension-data)
- [Connection Extension (`/connection`)](#connection-extension-connection)
- [Cluster Extension (`/cluster`)](#cluster-extension-cluster)
- [Sentinel Extension (`/sentinel`)](#sentinel-extension-sentinel)
- [Config Extension (`/config`)](#config-extension-config)

## Data Extension (`/data`)

The Data extension provides import and export functionality for Redis data, making it easy to backup, migrate, or share Redis datasets.

### Commands

#### `/data export`

Export Redis data to a file with various filtering and formatting options.

**Usage:**
```bash
/data export [--pattern PATTERN] [--folder FOLDER] [--force-keys] [--cancel] [--reset]
```

**Options:**
- `--pattern PATTERN`: Pattern to match keys (default: "*")
- `--folder FOLDER`: Folder to save the export file (default: current directory)
- `--force-keys`: Use KEYS command instead of SCAN (faster but blocks Redis)
- `--cancel`: Cancel a running export operation
- `--reset`: Reset export state

**Examples:**

```bash
# Export all keys
localhost:6379> /data export
Scanning keys...
Found 1,234 keys to export
Exporting keys...
Export completed: redis-export-20240118-143022-localhost-6379.txt

# Export keys matching a pattern
localhost:6379> /data export --pattern "user:*"
Scanning keys matching pattern 'user:*'...
Found 45 keys to export
Export completed: redis-export-20240118-143045-localhost-6379.txt

# Export to a specific folder
localhost:6379> /data export --folder /tmp/backups
Export completed: /tmp/backups/redis-export-20240118-143100-localhost-6379.txt

# Force using KEYS command (use with caution on large databases)
localhost:6379> /data export --pattern "session:*" --force-keys
Using KEYS command for faster export...
Export completed: redis-export-20240118-143115-localhost-6379.txt
```

#### `/data import`

Import Redis data from a previously exported file.

**Usage:**
```bash
/data import --file FILE_PATH
```

**Options:**
- `--file FILE_PATH`: Path to the import file (required)

**Examples:**

```bash
# Import from a file
localhost:6379> /data import --file redis-export-20240118-143022-localhost-6379.txt
Importing data from redis-export-20240118-143022-localhost-6379.txt...
Processing 1,234 keys...
Import completed: 1,234 keys imported, 0 errors

# Import with tab completion for file paths
localhost:6379> /data import --file [TAB]
redis-export-20240118-143022-localhost-6379.txt
redis-export-20240118-143045-localhost-6379.txt
```

#### `/data status`

Check the status of ongoing export or import operations.

**Usage:**
```bash
/data status
```

**Examples:**

```bash
# Check status during an export
localhost:6379> /data status
Export in progress:
  Pattern: user:*
  Progress: 234/456 keys (51%)
  Elapsed: 00:02:15
  Estimated remaining: 00:02:10

# Check status when no operation is running
localhost:6379> /data status
No export or import operation in progress.
Last export: redis-export-20240118-143022-localhost-6379.txt (1,234 keys)
```

### Use Cases

1. **Database Backup**: Regular exports for backup purposes
2. **Data Migration**: Moving data between Redis instances
3. **Development**: Sharing datasets between team members
4. **Testing**: Creating test datasets from production data subsets

## Connection Extension (`/connection`)

The Connection extension enables management of multiple Redis connections, allowing you to work with multiple Redis instances simultaneously.

### Commands

#### `/connection create`

Create a new Redis connection.

**Usage:**
```bash
/connection create [--host HOST] [--port PORT] [--db DB] [--username USERNAME] [--password PASSWORD] [--ssl] [--ssl-ca-certs SSL_CA_CERTS] [--ssl-ca-path SSL_CA_PATH] [--ssl-keyfile SSL_KEYFILE] [--ssl-certfile SSL_CERTFILE] [--ssl-cert-reqs SSL_CERT_REQS]
```

**Options:**
- `--host HOST`: Redis host (default: 127.0.0.1)
- `--port PORT`: Redis port (default: 6379)
- `--db DB`: Redis database number (default: 0)
- `--username USERNAME`: Redis username (default: default)
- `--password PASSWORD`: Redis password
- `--ssl`: Enable SSL/TLS connection
- `--ssl-ca-certs`: Path to CA certificate file
- `--ssl-ca-path`: Path to CA certificates directory
- `--ssl-keyfile`: Path to private key file
- `--ssl-certfile`: Path to certificate file
- `--ssl-cert-reqs`: Certificate requirements (none, optional, required)

**Examples:**

```bash
# Create a connection to a remote Redis
localhost:6379> /connection create --host redis.example.com --port 6379 --password secret123
Connection created with ID: 2

# Create an SSL connection
localhost:6379> /connection create --host secure-redis.com --port 6380 --ssl --ssl-cert-reqs required
Connection created with ID: 3

# Create a connection to a different database
localhost:6379> /connection create --host localhost --port 6379 --db 1
Connection created with ID: 4
```

#### `/connection list`

List all available Redis connections.

**Usage:**
```bash
/connection list
```

**Examples:**

```bash
localhost:6379> /connection list
Connections:
* 1: localhost:6379 (db: 0) [Current]
  2: redis.example.com:6379 (db: 0)
  3: secure-redis.com:6380 (db: 0) [SSL]
  4: localhost:6379 (db: 1)
```

#### `/connection use`

Switch to a specific Redis connection.

**Usage:**
```bash
/connection use <id>
```

**Examples:**

```bash
# Switch to connection 2
localhost:6379> /connection use 2
Switched to connection 2
redis.example.com:6379> 

# The prompt changes to reflect the current connection
redis.example.com:6379> /connection use 1
Switched to connection 1
localhost:6379>
```

#### `/connection destroy`

Remove a Redis connection.

**Usage:**
```bash
/connection destroy <id>
```

**Examples:**

```bash
localhost:6379> /connection destroy 3
Connection 3 (secure-redis.com:6380) destroyed

# Cannot destroy the current connection
localhost:6379> /connection destroy 1
Error: Cannot destroy the current connection. Switch to another connection first.
```

### Use Cases

1. **Multi-Environment Management**: Connect to dev, staging, and production Redis instances
2. **Database Separation**: Work with different Redis databases simultaneously
3. **Cluster Management**: Manage multiple Redis cluster nodes
4. **Comparison Operations**: Compare data between different Redis instances

## Cluster Extension (`/cluster`)

The Cluster extension provides tools for deploying, managing, and monitoring Redis clusters for development and testing purposes.

### Commands

#### `/cluster deploy`

Deploy a new Redis cluster locally.

**Usage:**
```bash
/cluster deploy
```

**Examples:**

```bash
localhost:6379> /cluster deploy
Deploying Redis cluster...
Creating 6 nodes (3 masters, 3 replicas)...
Starting Redis nodes on ports 30000-30005...
Configuring cluster...
Cluster deployed successfully!
Master nodes: 30000, 30001, 30002
Replica nodes: 30003, 30004, 30005
```

#### `/cluster info`

Get information about the deployed cluster.

**Usage:**
```bash
/cluster info
```

**Examples:**

```bash
localhost:6379> /cluster info
Redis Cluster Information:
Status: Running
Nodes: 6 (3 masters, 3 replicas)
Master nodes:
  127.0.0.1:30000 (slots: 0-5460)
  127.0.0.1:30001 (slots: 5461-10922)  
  127.0.0.1:30002 (slots: 10923-16383)
Replica nodes:
  127.0.0.1:30003 -> 127.0.0.1:30000
  127.0.0.1:30004 -> 127.0.0.1:30001
  127.0.0.1:30005 -> 127.0.0.1:30002
```

#### `/cluster start`

Start a previously stopped cluster.

**Usage:**
```bash
/cluster start
```

#### `/cluster stop`

Stop the cluster without removing data.

**Usage:**
```bash
/cluster stop
```

#### `/cluster remove`

Remove the cluster and clean up all data.

**Usage:**
```bash
/cluster remove
```

**Examples:**

```bash
localhost:6379> /cluster remove
Stopping cluster nodes...
Removing cluster data...
Cluster removed successfully!
```

### Use Cases

1. **Development Testing**: Test applications against Redis clusters locally
2. **Learning**: Understand Redis cluster behavior and operations
3. **Integration Testing**: Automated testing with cluster setups
4. **Prototyping**: Quick cluster setup for proof-of-concept work

## Sentinel Extension (`/sentinel`)

The Sentinel extension provides Redis Sentinel deployment and management for high availability testing.

### Commands

The Sentinel extension provides the same command structure as the Cluster extension:

- `/sentinel deploy`: Deploy a Redis Sentinel setup
- `/sentinel info`: Get Sentinel information  
- `/sentinel start`: Start Sentinel services
- `/sentinel stop`: Stop Sentinel services
- `/sentinel remove`: Remove Sentinel setup

**Examples:**

```bash
# Deploy Sentinel setup
localhost:6379> /sentinel deploy
Deploying Redis Sentinel setup...
Creating master and 2 replicas...
Starting Sentinel instances...
Sentinel setup completed!

# Get Sentinel information
localhost:6379> /sentinel info
Redis Sentinel Information:
Master: 127.0.0.1:26379
Replicas: 127.0.0.1:26380, 127.0.0.1:26381
Sentinels: 127.0.0.1:26382, 127.0.0.1:26383, 127.0.0.1:26384
```

### Use Cases

1. **High Availability Testing**: Test failover scenarios
2. **Monitoring Setup**: Learn Sentinel monitoring capabilities
3. **Development**: Develop applications with Sentinel awareness
4. **Training**: Understand Redis high availability concepts

## Config Extension (`/config`)

The Config extension provides runtime configuration management for Redis Shell.

### Commands

#### `/config get`

Get configuration values.

**Usage:**
```bash
/config get <section> <key>
/config get --all
```

**Examples:**

```bash
# Get a specific configuration value
localhost:6379> /config get general history_size
100

# Get all configuration
localhost:6379> /config get --all
[general]
history_size = 100
log_level = info
state_file = ~/.redis-shell

[redis]
default_host = 127.0.0.1
default_port = 6379
timeout = 5
```

#### `/config set`

Set configuration values.

**Usage:**
```bash
/config set <section> <key> <value>
```

**Examples:**

```bash
# Set history size
localhost:6379> /config set general history_size 200
Configuration updated: general.history_size = 200

# Set default Redis host
localhost:6379> /config set redis default_host redis.example.com
Configuration updated: redis.default_host = redis.example.com
```

#### `/config save`

Save configuration to disk.

**Usage:**
```bash
/config save
```

**Examples:**

```bash
localhost:6379> /config save
Configuration saved to ~/.redis-shell
```

### Use Cases

1. **Personalization**: Customize Redis Shell behavior
2. **Environment Setup**: Configure defaults for different environments
3. **Team Settings**: Share configuration across team members
4. **Automation**: Script configuration changes
