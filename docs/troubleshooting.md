# Troubleshooting Guide

This guide covers common issues you might encounter when using Redis Shell and their solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Connection Problems](#connection-problems)
- [SSL/TLS Issues](#ssltls-issues)
- [Extension Problems](#extension-problems)
- [Performance Issues](#performance-issues)
- [Configuration Problems](#configuration-problems)
- [Import/Export Issues](#importexport-issues)
- [Cluster and Sentinel Issues](#cluster-and-sentinel-issues)
- [General Debugging](#general-debugging)

## Installation Issues

### Command Not Found

**Problem:**
```bash
redis-shell: command not found
```

**Solutions:**

1. **Virtual Environment Not Activated:**
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   redis-shell
   ```

2. **Installation Not Completed:**
   ```bash
   cd redis-shell
   uv pip install -e .
   ```

3. **Using PEX Executable:**
   ```bash
   ./redis-shell.pex
   # Or add to PATH
   chmod +x redis-shell.pex
   sudo mv redis-shell.pex /usr/local/bin/redis-shell
   ```

### Import Errors

**Problem:**
```bash
ImportError: No module named 'redis_shell'
```

**Solutions:**

1. **Install in Development Mode:**
   ```bash
   uv pip install -e .
   ```

2. **Check Python Path:**
   ```bash
   python -c "import sys; print(sys.path)"
   # Ensure the redis-shell directory is in the path
   ```

3. **Reinstall Dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```

### Permission Errors

**Problem:**
```bash
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

1. **Use Virtual Environment:**
   ```bash
   python -m venv redis-shell-env
   source redis-shell-env/bin/activate
   uv pip install -e .
   ```

2. **Fix Directory Permissions:**
   ```bash
   chmod -R 755 ~/.config/redis-shell/
   ```

## Connection Problems

### Connection Refused

**Problem:**
```bash
Error: Connection refused
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solutions:**

1. **Check Redis Server Status:**
   ```bash
   # Check if Redis is running
   redis-cli ping
   # Or check process
   ps aux | grep redis
   ```

2. **Start Redis Server:**
   ```bash
   # Using Docker
   docker run -d --name redis-test -p 6379:6379 redis:latest
   
   # Using system service
   sudo systemctl start redis
   # Or on macOS
   brew services start redis
   ```

3. **Check Connection Parameters:**
   ```bash
   redis-shell --host localhost --port 6379
   # Verify host and port are correct
   ```

### Authentication Failed

**Problem:**
```bash
redis.exceptions.AuthenticationError: Authentication failed
```

**Solutions:**

1. **Provide Correct Password:**
   ```bash
   redis-shell --password your_password
   # Or use environment variable
   export REDIS_PASSWORD=your_password
   redis-shell
   ```

2. **Check Redis Configuration:**
   ```bash
   # In redis.conf, check:
   # requirepass your_password
   # user default on >your_password ~* &* +@all
   ```

3. **Use Correct Username:**
   ```bash
   redis-shell --username myuser --password mypassword
   ```

### Timeout Errors

**Problem:**
```bash
redis.exceptions.TimeoutError: Timeout reading from socket
```

**Solutions:**

1. **Increase Timeout:**
   ```bash
   redis-shell --host slow-redis.com
   # Then configure timeout
   localhost:6379> /config set redis timeout 30
   ```

2. **Check Network Connectivity:**
   ```bash
   ping redis.example.com
   telnet redis.example.com 6379
   ```

3. **Check Redis Server Load:**
   ```bash
   redis-cli --latency -h redis.example.com
   ```

## SSL/TLS Issues

### SSL Certificate Verification Failed

**Problem:**
```bash
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**Solutions:**

1. **Use Correct CA Certificates:**
   ```bash
   redis-shell --host secure-redis.com --ssl --ssl-ca-certs /path/to/ca.crt
   ```

2. **Disable Certificate Verification (Development Only):**
   ```bash
   redis-shell --host secure-redis.com --ssl --ssl-cert-reqs none
   ```

3. **Check Certificate Paths:**
   ```bash
   ls -la /path/to/certificates/
   # Ensure files exist and are readable
   ```

### SSL Handshake Failed

**Problem:**
```bash
ssl.SSLError: [SSL: HANDSHAKE_FAILURE] handshake failure
```

**Solutions:**

1. **Check SSL Configuration:**
   ```bash
   openssl s_client -connect secure-redis.com:6380
   ```

2. **Use Correct SSL Parameters:**
   ```bash
   redis-shell --host secure-redis.com --port 6380 --ssl \
     --ssl-certfile client.crt --ssl-keyfile client.key
   ```

## Extension Problems

### Extension Not Loading

**Problem:**
```bash
Error loading extension: myextension
```

**Solutions:**

1. **Check Extension Directory:**
   ```bash
   ls -la ~/.config/redis-shell/extensions/myextension/
   # Should contain extension.json and commands.py
   ```

2. **Validate Extension JSON:**
   ```bash
   python -m json.tool ~/.config/redis-shell/extensions/myextension/extension.json
   ```

3. **Check Python Syntax:**
   ```bash
   python -m py_compile ~/.config/redis-shell/extensions/myextension/commands.py
   ```

4. **Review Extension Structure:**
   ```
   ~/.config/redis-shell/extensions/myextension/
   ├── extension.json
   └── commands.py
   ```

### Extension Command Not Found

**Problem:**
```bash
Unknown command: /myext hello
```

**Solutions:**

1. **Check Extension Registration:**
   ```bash
   localhost:6379> /help
   # Look for your extension in the list
   ```

2. **Restart Redis Shell:**
   ```bash
   # Extensions are loaded at startup
   exit
   redis-shell
   ```

3. **Check Extension Namespace:**
   ```json
   {
     "namespace": "/myext",
     "commands": [{"name": "hello", ...}]
   }
   ```

### Extension Import Errors

**Problem:**
```bash
ImportError in extension: No module named 'requests'
```

**Solutions:**

1. **Install Extension Dependencies:**
   ```bash
   uv pip install requests
   # Or create requirements.txt in extension directory
   ```

2. **Use Virtual Environment:**
   ```bash
   source .venv/bin/activate
   uv pip install -r ~/.config/redis-shell/extensions/myextension/requirements.txt
   ```

## Performance Issues

### Slow Command Execution

**Problem:**
Commands take a long time to execute.

**Solutions:**

1. **Check Redis Server Performance:**
   ```bash
   redis-cli --latency -h your-redis-host
   redis-cli --latency-history -h your-redis-host
   ```

2. **Use SCAN Instead of KEYS:**
   ```bash
   # Instead of
   localhost:6379> KEYS *
   # Use data export which uses SCAN
   localhost:6379> /data export
   ```

3. **Monitor Redis:**
   ```bash
   redis-cli monitor
   # Check for slow queries
   redis-cli slowlog get 10
   ```

### Memory Issues

**Problem:**
```bash
MemoryError: Unable to allocate memory
```

**Solutions:**

1. **Export in Smaller Batches:**
   ```bash
   localhost:6379> /data export --pattern "user:1*"
   localhost:6379> /data export --pattern "user:2*"
   ```

2. **Check Available Memory:**
   ```bash
   free -h  # Linux
   vm_stat  # macOS
   ```

3. **Increase System Memory or Use Streaming:**
   ```bash
   # Consider using redis-cli for large exports
   redis-cli --scan --pattern "user:*" | head -1000
   ```

## Configuration Problems

### Configuration File Not Found

**Problem:**
```bash
Warning: Configuration file not found, using defaults
```

**Solutions:**

1. **Create Configuration File:**
   ```bash
   mkdir -p ~/.config/redis-shell
   redis-shell  # Will create default config
   ```

2. **Specify Configuration Path:**
   ```bash
   export REDIS_SHELL_CONFIG=/path/to/config.json
   redis-shell
   ```

3. **Check File Permissions:**
   ```bash
   ls -la ~/.redis-shell
   chmod 644 ~/.redis-shell
   ```

### Invalid Configuration

**Problem:**
```bash
Error: Invalid configuration format
```

**Solutions:**

1. **Validate JSON Syntax:**
   ```bash
   python -m json.tool ~/.redis-shell
   ```

2. **Reset to Defaults:**
   ```bash
   mv ~/.redis-shell ~/.redis-shell.backup
   redis-shell  # Will create new default config
   ```

3. **Check Configuration Structure:**
   ```json
   {
     "general": {...},
     "redis": {...},
     "extensions": {...},
     "ui": {...}
   }
   ```

## Import/Export Issues

### Export Fails with Large Datasets

**Problem:**
```bash
Export failed: Memory error or timeout
```

**Solutions:**

1. **Use Pattern-Based Export:**
   ```bash
   localhost:6379> /data export --pattern "user:*"
   localhost:6379> /data export --pattern "session:*"
   ```

2. **Use SCAN (Default) Instead of KEYS:**
   ```bash
   # Don't use --force-keys with large datasets
   localhost:6379> /data export --pattern "*"
   ```

3. **Export to Different Directory:**
   ```bash
   localhost:6379> /data export --folder /tmp
   # Ensure sufficient disk space
   ```

### Import Fails

**Problem:**
```bash
Import failed: Invalid file format
```

**Solutions:**

1. **Check File Format:**
   ```bash
   head -5 redis-export-file.txt
   # Should show Redis commands like SET, HSET, etc.
   ```

2. **Verify File Integrity:**
   ```bash
   wc -l redis-export-file.txt
   # Check if file is complete
   ```

3. **Import Smaller Files:**
   ```bash
   split -l 1000 large-export.txt small-export-
   # Import each part separately
   ```

## Cluster and Sentinel Issues

### Cluster Deployment Fails

**Problem:**
```bash
Error: Failed to create cluster
```

**Solutions:**

1. **Check Port Availability:**
   ```bash
   netstat -ln | grep 30000
   # Ensure ports 30000-30005 are free
   ```

2. **Check Redis Installation:**
   ```bash
   which redis-server
   redis-server --version
   ```

3. **Clean Up Previous Attempts:**
   ```bash
   localhost:6379> /cluster remove
   # Then try deploying again
   ```

### Sentinel Connection Issues

**Problem:**
```bash
Error: Cannot connect to Sentinel
```

**Solutions:**

1. **Check Sentinel Status:**
   ```bash
   redis-cli -p 26379 ping
   ```

2. **Verify Sentinel Configuration:**
   ```bash
   localhost:6379> /sentinel info
   ```

3. **Restart Sentinel Setup:**
   ```bash
   localhost:6379> /sentinel remove
   localhost:6379> /sentinel deploy
   ```

## General Debugging

### Enable Debug Logging

```bash
# Set log level to debug
redis-shell --log-level debug

# Or in configuration
localhost:6379> /config set general log_level debug
localhost:6379> /config save
```

### Check System Resources

```bash
# Check disk space
df -h

# Check memory usage
free -h  # Linux
vm_stat  # macOS

# Check network connectivity
ping redis.example.com
telnet redis.example.com 6379
```

### Get Help

1. **Use Built-in Help:**
   ```bash
   localhost:6379> /help
   localhost:6379> /data --help
   ```

2. **Check Version:**
   ```bash
   redis-shell --version
   ```

3. **Review Logs:**
   ```bash
   # Check log file location
   localhost:6379> /config get general log_file
   tail -f /path/to/logfile
   ```

### Report Issues

When reporting issues, include:

1. **Redis Shell Version:**
   ```bash
   redis-shell --version
   ```

2. **System Information:**
   ```bash
   python --version
   uname -a  # Linux/macOS
   ```

3. **Error Messages:**
   ```bash
   # Full error output with stack trace
   redis-shell --log-level debug
   ```

4. **Configuration:**
   ```bash
   localhost:6379> /config get --all
   ```

5. **Steps to Reproduce:**
   - Exact commands used
   - Expected vs actual behavior
   - Environment details
