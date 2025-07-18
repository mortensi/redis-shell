# Examples and Recipes

This document provides practical examples and recipes for common Redis Shell use cases. Each example includes step-by-step instructions and explanations.

## Table of Contents

- [Database Management](#database-management)
- [Development Workflows](#development-workflows)
- [Data Migration](#data-migration)
- [Testing and QA](#testing-and-qa)
- [Production Operations](#production-operations)
- [Automation Scripts](#automation-scripts)

## Database Management

### Backup and Restore Operations

#### Complete Database Backup

```bash
# Connect to your Redis instance
redis-shell --host production-redis.com --port 6379 --password secret

# Create a complete backup
production-redis.com:6379> /data export --folder /backups/redis
Scanning keys...
Found 50,000 keys to export
Export completed: /backups/redis/redis-export-20240118-143022-production-redis-6379.txt

# Verify backup
production-redis.com:6379> /data status
Last export: /backups/redis/redis-export-20240118-143022-production-redis-6379.txt (50,000 keys)
```

#### Selective Data Backup

```bash
# Backup only user data
localhost:6379> /data export --pattern "user:*" --folder /backups/users
Export completed: /backups/users/redis-export-20240118-143045-localhost-6379.txt

# Backup session data
localhost:6379> /data export --pattern "session:*" --folder /backups/sessions
Export completed: /backups/sessions/redis-export-20240118-143100-localhost-6379.txt

# Backup cache data with specific naming
localhost:6379> /data export --pattern "cache:*" --folder /backups/cache
Export completed: /backups/cache/redis-export-20240118-143115-localhost-6379.txt
```

#### Database Restore

```bash
# Connect to target Redis instance
redis-shell --host staging-redis.com --port 6379

# Restore from backup
staging-redis.com:6379> /data import --file /backups/redis/redis-export-20240118-143022-production-redis-6379.txt
Importing data from /backups/redis/redis-export-20240118-143022-production-redis-6379.txt...
Import completed: 50,000 keys imported, 0 errors

# Verify import
staging-redis.com:6379> DBSIZE
(integer) 50000
```

### Database Cleanup

#### Remove Expired Sessions

```bash
# Connect to Redis
redis-shell

# Find session keys
localhost:6379> SCAN 0 MATCH "session:*" COUNT 100
1) "0"
2) 1) "session:user123"
   2) "session:user456"
   3) "session:user789"

# Check TTL and remove expired sessions
localhost:6379> TTL session:user123
(integer) -1

# Set expiration for sessions without TTL
localhost:6379> EXPIRE session:user123 3600
(integer) 1
```

#### Clean Up Test Data

```bash
# Remove all test keys
localhost:6379> /data export --pattern "test:*" --folder /tmp/cleanup
# Review the export file first, then delete
localhost:6379> EVAL "return redis.call('del', unpack(redis.call('keys', 'test:*')))" 0
```

## Development Workflows

### Multi-Environment Setup

#### Development Environment

```bash
# Create development configuration
mkdir -p ~/.config/redis-shell
cat > ~/.config/redis-shell/dev-config.json << EOF
{
  "general": {
    "history_size": 500,
    "log_level": "debug"
  },
  "redis": {
    "default_host": "localhost",
    "default_port": 6379,
    "default_db": 0
  },
  "ui": {
    "prompt_style": "cyan"
  }
}
EOF

# Use development config
export REDIS_SHELL_CONFIG=~/.config/redis-shell/dev-config.json
redis-shell
```

#### Multi-Environment Connection Management

```bash
# Start Redis Shell
redis-shell

# Set up development connection
localhost:6379> /connection create --host dev-redis.com --port 6379 --db 0
Connection created with ID: 2

# Set up staging connection
localhost:6379> /connection create --host staging-redis.com --port 6379 --db 0 --password staging-pass
Connection created with ID: 3

# Set up production connection (read-only user)
localhost:6379> /connection create --host prod-redis.com --port 6379 --username readonly --password prod-pass
Connection created with ID: 4

# List all environments
localhost:6379> /connection list
Connections:
* 1: localhost:6379 (db: 0) [Current]
  2: dev-redis.com:6379 (db: 0)
  3: staging-redis.com:6379 (db: 0)
  4: prod-redis.com:6379 (db: 0)

# Switch to staging for testing
localhost:6379> /connection use 3
Switched to connection 3
staging-redis.com:6379>
```

### Testing Data Setup

#### Create Test Dataset

```bash
# Connect to test Redis
redis-shell --host test-redis.com --port 6379

# Create test users
test-redis.com:6379> HSET user:1001 name "Alice" email "alice@test.com" role "admin"
test-redis.com:6379> HSET user:1002 name "Bob" email "bob@test.com" role "user"
test-redis.com:6379> HSET user:1003 name "Charlie" email "charlie@test.com" role "user"

# Create test sessions
test-redis.com:6379> SET session:alice "user:1001" EX 3600
test-redis.com:6379> SET session:bob "user:1002" EX 3600

# Create test cache data
test-redis.com:6379> SET cache:popular_items "[\"item1\", \"item2\", \"item3\"]" EX 300
test-redis.com:6379> SET cache:user_preferences:1001 "{\"theme\": \"dark\", \"lang\": \"en\"}" EX 1800

# Export test dataset for reuse
test-redis.com:6379> /data export --folder /tmp/test-data
Export completed: /tmp/test-data/redis-export-20240118-143200-test-redis-6379.txt
```

#### Load Test Data in Different Environments

```bash
# Load test data in development
redis-shell --host localhost --port 6379
localhost:6379> /data import --file /tmp/test-data/redis-export-20240118-143200-test-redis-6379.txt
Import completed: 8 keys imported

# Load test data in CI environment
redis-shell --host ci-redis --port 6379
ci-redis:6379> /data import --file /tmp/test-data/redis-export-20240118-143200-test-redis-6379.txt
Import completed: 8 keys imported
```

## Data Migration

### Redis Version Migration

#### From Redis 5 to Redis 6

```bash
# Export from Redis 5 instance
redis-shell --host redis5.example.com --port 6379
redis5.example.com:6379> /data export --folder /migration/redis5-to-6
Export completed: /migration/redis5-to-6/redis-export-20240118-143300-redis5-6379.txt

# Import to Redis 6 instance
redis-shell --host redis6.example.com --port 6379
redis6.example.com:6379> /data import --file /migration/redis5-to-6/redis-export-20240118-143300-redis5-6379.txt
Import completed: 25,000 keys imported

# Verify migration
redis6.example.com:6379> DBSIZE
(integer) 25000
redis6.example.com:6379> INFO server
# redis_version:6.2.7
```

### Cloud Migration

#### AWS ElastiCache to Redis Cloud

```bash
# Export from ElastiCache (via bastion host)
redis-shell --host elasticache.abc123.cache.amazonaws.com --port 6379
elasticache:6379> /data export --pattern "*" --folder /migration/aws-to-cloud
Export completed: /migration/aws-to-cloud/redis-export-20240118-143400-elasticache-6379.txt

# Import to Redis Cloud
redis-shell --host redis-12345.c1.us-east-1-1.ec2.cloud.redislabs.com --port 12345 --password cloud-password
redis-cloud:12345> /data import --file /migration/aws-to-cloud/redis-export-20240118-143400-elasticache-6379.txt
Import completed: 100,000 keys imported
```

### Database Consolidation

#### Merge Multiple Databases

```bash
# Export from database 0
redis-shell --host source-redis.com --port 6379 --db 0
source-redis.com:6379[0]> /data export --folder /consolidation --pattern "*"
Export completed: /consolidation/redis-export-20240118-143500-source-redis-6379-db0.txt

# Export from database 1
redis-shell --host source-redis.com --port 6379 --db 1
source-redis.com:6379[1]> /data export --folder /consolidation --pattern "*"
Export completed: /consolidation/redis-export-20240118-143515-source-redis-6379-db1.txt

# Import both to target database
redis-shell --host target-redis.com --port 6379 --db 0
target-redis.com:6379> /data import --file /consolidation/redis-export-20240118-143500-source-redis-6379-db0.txt
Import completed: 15,000 keys imported

target-redis.com:6379> /data import --file /consolidation/redis-export-20240118-143515-source-redis-6379-db1.txt
Import completed: 8,000 keys imported

# Verify consolidation
target-redis.com:6379> DBSIZE
(integer) 23000
```

## Testing and QA

### Load Testing Setup

#### Deploy Test Cluster

```bash
# Start Redis Shell
redis-shell

# Deploy a local cluster for load testing
localhost:6379> /cluster deploy
Deploying Redis cluster...
Cluster deployed successfully!
Master nodes: 30000, 30001, 30002
Replica nodes: 30003, 30004, 30005

# Connect to cluster
localhost:6379> /connection create --host localhost --port 30000
Connection created with ID: 2

localhost:6379> /connection use 2
Switched to connection 2
localhost:30000>

# Verify cluster status
localhost:30000> CLUSTER INFO
cluster_state:ok
cluster_slots_assigned:16384
cluster_slots_ok:16384
cluster_slots_pfail:0
cluster_slots_fail:0
```

#### Performance Testing Data

```bash
# Create performance test data
localhost:30000> EVAL "
for i=1,10000 do
  redis.call('SET', 'perf:key:' .. i, 'value' .. i)
  redis.call('HSET', 'perf:hash:' .. i, 'field1', 'value1', 'field2', 'value2')
  redis.call('LPUSH', 'perf:list:' .. i, 'item1', 'item2', 'item3')
end
return 'OK'
" 0

# Verify test data
localhost:30000> DBSIZE
(integer) 30000

# Export test data for reuse
localhost:30000> /data export --pattern "perf:*" --folder /tmp/perf-data
Export completed: /tmp/perf-data/redis-export-20240118-143600-localhost-30000.txt
```

### Integration Testing

#### Test Environment Reset

```bash
# Create reset script
cat > reset-test-env.sh << 'EOF'
#!/bin/bash
redis-shell --host test-redis.com --port 6379 --command "FLUSHDB"
redis-shell --host test-redis.com --port 6379 --command "/data import --file /test-data/baseline.txt"
echo "Test environment reset complete"
EOF

chmod +x reset-test-env.sh

# Use in CI/CD pipeline
./reset-test-env.sh
```

## Production Operations

### Health Monitoring

#### Connection Health Check

```bash
# Create health check script
cat > redis-health-check.sh << 'EOF'
#!/bin/bash

REDIS_HOST=${1:-localhost}
REDIS_PORT=${2:-6379}

# Test basic connectivity
if redis-shell --host $REDIS_HOST --port $REDIS_PORT --command "PING" > /dev/null 2>&1; then
    echo "✓ Redis connectivity: OK"
else
    echo "✗ Redis connectivity: FAILED"
    exit 1
fi

# Check memory usage
MEMORY_USAGE=$(redis-shell --host $REDIS_HOST --port $REDIS_PORT --command "INFO memory" | grep used_memory_human | cut -d: -f2)
echo "Memory usage: $MEMORY_USAGE"

# Check connected clients
CLIENTS=$(redis-shell --host $REDIS_HOST --port $REDIS_PORT --command "INFO clients" | grep connected_clients | cut -d: -f2)
echo "Connected clients: $CLIENTS"

echo "Health check complete"
EOF

chmod +x redis-health-check.sh

# Run health check
./redis-health-check.sh prod-redis.com 6379
```

### Maintenance Operations

#### Scheduled Backup

```bash
# Create backup script
cat > redis-backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/backups/redis/$(date +%Y%m%d)"
REDIS_HOST=${1:-localhost}
REDIS_PORT=${2:-6379}

mkdir -p $BACKUP_DIR

# Create backup
redis-shell --host $REDIS_HOST --port $REDIS_PORT --command "/data export --folder $BACKUP_DIR"

# Compress backup
gzip $BACKUP_DIR/redis-export-*.txt

# Clean old backups (keep 7 days)
find /backups/redis -type d -mtime +7 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x redis-backup.sh

# Add to crontab for daily backups
# 0 2 * * * /path/to/redis-backup.sh prod-redis.com 6379
```

## Automation Scripts

### Deployment Automation

#### Environment Provisioning

```bash
# Create environment setup script
cat > setup-redis-env.sh << 'EOF'
#!/bin/bash

ENV_NAME=$1
REDIS_HOST=$2
REDIS_PORT=$3

if [ -z "$ENV_NAME" ] || [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
    echo "Usage: $0 <env_name> <redis_host> <redis_port>"
    exit 1
fi

# Create environment-specific config
CONFIG_FILE="$HOME/.config/redis-shell/${ENV_NAME}-config.json"
mkdir -p "$(dirname $CONFIG_FILE)"

cat > $CONFIG_FILE << EOL
{
  "general": {
    "history_size": 200,
    "log_level": "info"
  },
  "redis": {
    "default_host": "$REDIS_HOST",
    "default_port": $REDIS_PORT,
    "timeout": 10
  },
  "ui": {
    "prompt_style": "green"
  }
}
EOL

# Create connection script
CONNECT_SCRIPT="$HOME/bin/redis-$ENV_NAME"
mkdir -p "$(dirname $CONNECT_SCRIPT)"

cat > $CONNECT_SCRIPT << EOL
#!/bin/bash
export REDIS_SHELL_CONFIG=$CONFIG_FILE
redis-shell
EOL

chmod +x $CONNECT_SCRIPT

echo "Environment '$ENV_NAME' configured"
echo "Connect using: redis-$ENV_NAME"
EOF

chmod +x setup-redis-env.sh

# Set up environments
./setup-redis-env.sh dev localhost 6379
./setup-redis-env.sh staging staging-redis.com 6379
./setup-redis-env.sh prod prod-redis.com 6379
```

### Data Synchronization

#### Cross-Environment Sync

```bash
# Create sync script
cat > redis-sync.sh << 'EOF'
#!/bin/bash

SOURCE_HOST=$1
SOURCE_PORT=$2
TARGET_HOST=$3
TARGET_PORT=$4
PATTERN=${5:-"*"}

if [ $# -lt 4 ]; then
    echo "Usage: $0 <source_host> <source_port> <target_host> <target_port> [pattern]"
    exit 1
fi

TEMP_FILE="/tmp/redis-sync-$(date +%s).txt"

echo "Exporting from $SOURCE_HOST:$SOURCE_PORT..."
redis-shell --host $SOURCE_HOST --port $SOURCE_PORT --command "/data export --pattern '$PATTERN' --folder /tmp" > /dev/null

# Find the exported file
EXPORT_FILE=$(ls -t /tmp/redis-export-*-$SOURCE_HOST-$SOURCE_PORT.txt | head -1)

echo "Importing to $TARGET_HOST:$TARGET_PORT..."
redis-shell --host $TARGET_HOST --port $TARGET_PORT --command "/data import --file '$EXPORT_FILE'"

# Clean up
rm -f $EXPORT_FILE

echo "Sync completed"
EOF

chmod +x redis-sync.sh

# Sync user data from staging to dev
./redis-sync.sh staging-redis.com 6379 localhost 6379 "user:*"
```

These examples demonstrate practical, real-world usage patterns for Redis Shell. Each recipe can be adapted to your specific needs and integrated into your development and operations workflows.
