from typing import Optional, Dict, Any, List, Union
import redis
from redis.cluster import RedisCluster
import argparse
import os
import glob
import threading
import datetime
import base64
import json
import logging
from ...state import StateManager
from ...connection_manager import ConnectionManager
from ...utils.file_utils import PathHandler
from ...utils.completion_utils import completion_registry
from ...utils.redis_utils import RedisConnectionHelper

logger = logging.getLogger(__name__)

class DataCommands:
    def __init__(self, cli=None):
        self._state = StateManager()
        self._connection_manager = ConnectionManager()
        self._export_thread = None
        self._export_status = None
        self._current_operation = None
        # Create a stop event for thread control
        self._stop_event = threading.Event()
        # Initialize it to not-set
        self._stop_event.clear()
        # Store reference to CLI instance (for backward compatibility)
        self._cli = cli

    def get_key_patterns(self, incomplete=""):
        """Return key pattern completions for Redis keys.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of completion items that match the incomplete text
        """
        return completion_registry.get_completions("key_patterns", incomplete)

    def get_folders(self, incomplete=""):
        """Return folder completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of folder paths that match the incomplete text
        """
        return PathHandler.get_directory_completions(incomplete)

    def get_export_files(self, incomplete=""):
        """Return export file completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of export file paths that match the incomplete text
        """
        # Get directory completions first
        completions = PathHandler.get_directory_completions(incomplete)

        # Then add file completions for Redis export files only
        base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path(incomplete)

        try:
            # Get all files in the base directory that match the pattern
            full_pattern = os.path.join(base_dir, "*.txt")

            for file_path in glob.glob(full_pattern):
                if os.path.isfile(file_path):
                    file_name = os.path.basename(file_path)

                    # Only include files that start with redis-export-
                    if not file_name.startswith('redis-export-'):
                        continue

                    # Format the path based on whether we're using absolute or relative paths
                    if is_absolute:
                        # For absolute paths, preserve the directory structure
                        if prefix and file_name.startswith(prefix):
                            completions.append(path_prefix + file_name)
                        elif not prefix:
                            completions.append(path_prefix + file_name)
                    elif os.path.sep in incomplete:
                        # For relative paths with directories, preserve the directory structure
                        if prefix and file_name.startswith(prefix):
                            completions.append(path_prefix + file_name)
                        elif not prefix:
                            completions.append(path_prefix + file_name)
                    else:
                        # For simple completions in the current directory
                        if prefix and file_name.startswith(prefix):
                            completions.append(file_name)
                        elif not prefix:
                            completions.append(file_name)
        except (FileNotFoundError, PermissionError):
            pass

        return completions

    def _format_for_command(self, value):
        """Format a value for use in a Redis command.

        This handles binary data by using base64 encoding for non-printable characters.
        For simple strings, it just adds quotes.

        Args:
            value: The value to format (string or bytes)

        Returns:
            str: The formatted value ready for use in a Redis command
        """
        if value is None:
            return '""'

        # For bytes, we need to handle binary data
        if isinstance(value, bytes):
            try:
                # Try to decode as UTF-8 first
                decoded = value.decode('utf-8')
                # Check if it contains any non-printable characters
                if all(c.isprintable() or c.isspace() for c in decoded):
                    # If it's all printable, just quote it
                    return f'"{self._escape_quotes(decoded)}"'
                else:
                    # Otherwise, use base64
                    b64 = base64.b64encode(value).decode('ascii')
                    return f'"\\x{b64}"'
            except UnicodeDecodeError:
                # If it can't be decoded as UTF-8, use base64
                b64 = base64.b64encode(value).decode('ascii')
                return f'"\\x{b64}"'
        else:
            # For strings, just quote and escape
            return f'"{self._escape_quotes(str(value))}"'

    def _escape_quotes(self, s):
        """Escape quotes in a string."""
        return s.replace('"', '\\"')

    def handle_command(self, cmd: str, args: list) -> Optional[str]:
        """Handle data commands."""
        if cmd == "export":
            return self._export(args)
        elif cmd == "import":
            return self._import(args)
        elif cmd == "status":
            return self._status()
        return None

    def _export(self, args: list) -> str:
        """Export Redis data to a file."""
        import signal

        # Define a signal handler for Ctrl+C
        def signal_handler(*_):
            print("\nCtrl+C detected! Cancelling export operation...")
            if self._export_thread and self._export_thread.is_alive():
                self._stop_event.set()
                print("Stop signal sent to export thread.")
            else:
                print("No export thread running.")

        parser = argparse.ArgumentParser(description='Export Redis data')
        parser.add_argument('--pattern', type=str, default='*', help='Pattern to match keys (default: "*")')
        parser.add_argument('--folder', type=str, default='.', help='Folder to save the export file')
        parser.add_argument('--cancel', action='store_true', help='Cancel a running export operation')
        parser.add_argument('--force-keys', action='store_true', help='Force using KEYS command instead of SCAN')

        try:
            parsed_args = parser.parse_args(args)

            # Check if we're cancelling an export
            if parsed_args.cancel:
                if self._export_thread and self._export_thread.is_alive():
                    self._stop_event.set()
                    return "Cancelling export operation..."
                else:
                    return "No export operation is currently running."

            # Get the pattern, folder, and force_keys options
            pattern = parsed_args.pattern
            folder = parsed_args.folder
            force_keys = parsed_args.force_keys

            # Check if a thread is already running
            if self._export_thread and self._export_thread.is_alive():
                return "An export operation is already running. Use '/data status' to check its status or '/data export --cancel' to cancel it."

            # Reset the stop event
            self._stop_event.clear()

            # Reset any previous status
            self._export_status = None
            self._current_operation = "export"
            self._export_status = "Starting export operation..."

            # Set up signal handler for Ctrl+C
            original_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, signal_handler)

            # Create the export thread
            self._export_thread = threading.Thread(
                target=self._export_thread_func,
                args=(pattern, folder, force_keys)
            )
            self._export_thread.daemon = True  # Make thread a daemon so it exits when main thread exits

            # Store the original handler for later restoration
            self._original_sigint_handler = original_handler

            # Start the thread
            try:
                self._export_thread.start()

                # Start a timer to restore the signal handler after a delay
                # This ensures the signal handler is restored even if the thread completes
                def restore_signal_handler():
                    if hasattr(self, '_original_sigint_handler'):
                        try:
                            signal.signal(signal.SIGINT, self._original_sigint_handler)
                            print("Restored original SIGINT handler")
                        except Exception:
                            pass  # Ignore errors when restoring

                # Create a timer to restore the handler after 30 minutes (worst case)
                timer = threading.Timer(1800, restore_signal_handler)
                timer.daemon = True
                timer.start()

                return f"Export operation started with pattern '{pattern}'.\n" \
                       f"Use '/data status' to check its status or '/data export --cancel' to cancel it.\n" \
                       f"You can also press Ctrl+C to cancel the operation."
            except Exception as e:
                # Restore original signal handler
                signal.signal(signal.SIGINT, original_handler)
                self._export_status = f"Error starting export thread: {str(e)}"
                self._current_operation = None
                return f"Error starting export thread: {str(e)}"
        except Exception as e:
            self._export_status = None
            self._current_operation = None
            return f"Error starting export: {str(e)}"

    def _export_thread_func(self, pattern: str, folder: str, force_keys: bool = False):
        """Thread function for exporting data."""
        try:
            # Get the current Redis connection from the connection manager
            redis_client = self._connection_manager.get_redis_client()

            if redis_client:
                # Get connection parameters from the connection manager
                host, port, db, password = self._connection_manager.get_connection_parameters()
                # Check if this is a cluster connection
                is_cluster = self._connection_manager.is_cluster_connection()
                if is_cluster:
                    print(f"Using current Redis Cluster connection from connection manager: {host}:{port}")
                else:
                    print(f"Using current Redis connection from connection manager: {host}:{port} (db: {db})")
            elif self._cli and hasattr(self._cli, 'redis'):
                # Fall back to CLI connection if connection manager doesn't have a connection
                # This is for backward compatibility
                host = self._cli.host
                port = self._cli.port
                db = self._cli.redis.connection_pool.connection_kwargs.get('db', 0)
                password = self._cli.redis.connection_pool.connection_kwargs.get('password', None)
                print(f"Using current Redis connection from CLI: {host}:{port} (db: {db})")
            else:
                # Fall back to default connection if no connection is available
                host = 'localhost'
                port = 6379
                db = 0
                password = None
                print("No active connection available, using default connection: localhost:6379")

            try:
                # If we already have a Redis client from the connection manager, use it
                if redis_client:
                    standard_client = redis_client
                else:
                    # Otherwise, create a standard Redis client
                    standard_client = redis.Redis(
                        host=host,
                        port=port,
                        db=db,
                        password=password,
                        decode_responses=False
                    )

                # Check if this is a cluster by running CLUSTER SLOTS
                is_cluster = False
                cluster_nodes = []

                try:
                    print("Checking if Redis instance is part of a cluster...")
                    slots_info = standard_client.execute_command('CLUSTER SLOTS')

                    if slots_info and isinstance(slots_info, list) and len(slots_info) > 0:
                        is_cluster = True
                        print("Redis instance is part of a cluster. Will use Cluster API.")

                        # Extract cluster nodes from slots info
                        for slot_range in slots_info:
                            if isinstance(slot_range, list) and len(slot_range) >= 3:
                                # Process master node
                                master_info = slot_range[2]
                                if isinstance(master_info, list) and len(master_info) >= 2:
                                    master_host = master_info[0]
                                    if isinstance(master_host, bytes):
                                        master_host = master_host.decode('utf-8')
                                    master_port = master_info[1]

                                    # Add to nodes list if not already there
                                    node_addr = f"{master_host}:{master_port}"
                                    if node_addr not in cluster_nodes:
                                        cluster_nodes.append(node_addr)
                                        print(f"Found cluster node: {node_addr} (master)")
                except Exception as e:
                    print(f"Not a cluster or error checking cluster status: {str(e)}")
                    is_cluster = False

                # Create the appropriate Redis client based on whether it's a cluster
                if is_cluster and cluster_nodes:
                    try:
                        # Format startup nodes for RedisCluster
                        startup_nodes = []
                        for node in cluster_nodes:
                            host, port = node.split(':')
                            startup_nodes.append({"host": host, "port": int(port)})

                        # Create a RedisCluster client
                        print(f"Creating RedisCluster client with {len(startup_nodes)} nodes")
                        r = RedisCluster(
                            startup_nodes=startup_nodes,
                            decode_responses=False,
                            password=password
                        )
                        print("Successfully created RedisCluster client")
                    except Exception as e:
                        print(f"Error creating RedisCluster client: {str(e)}")
                        print("Falling back to standard Redis client")
                        is_cluster = False

                # If not a cluster or cluster client creation failed, use standard Redis client
                if not is_cluster:
                    r = redis.Redis(
                        host=host,
                        port=port,
                        db=db,
                        password=password,
                        decode_responses=False
                    )
                    print("Using standard Redis client")
            except Exception as e:
                print(f"Error creating Redis client: {str(e)}")
                self._export_status = f"Error creating Redis client: {str(e)}"
                return

            # Connection info already printed above

            # Generate filename with datetime, host, and port
            now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            host = r.connection_pool.connection_kwargs.get('host', 'localhost')
            port = r.connection_pool.connection_kwargs.get('port', 6379)
            filename = f"redis-export-{now}-{host}-{port}.txt"
            filepath = os.path.join(folder, filename)

            # Print connection info for debugging
            print(f"Connected to Redis at {host}:{port}")
            try:
                info = r.info()
                print(f"Redis version: {info.get('redis_version')}")
                print(f"Redis mode: {info.get('redis_mode')}")
                print(f"Keys in current database: {info.get('db0', {}).get('keys', 'unknown')}")
            except Exception as e:
                print(f"Warning: Could not get Redis info: {e}")

            # Create the folder if it doesn't exist
            os.makedirs(folder, exist_ok=True)
            print(f"Export file will be saved to: {filepath}")

            # Open the file for writing
            with open(filepath, 'w') as f:
                # Update status
                self._export_status = f"Scanning keys with pattern '{pattern}'..."

                # Use SCAN to iterate through keys
                print(f"Scanning and exporting keys matching pattern '{pattern}'...")
                cursor = '0'
                processed_keys = 0
                batch_size = 100  # Process keys in batches of 100
                max_iterations = 10000  # Safety limit to prevent infinite loops

                try:
                    # Use a completely different approach to avoid the infinite loop
                    # Instead of using SCAN, we'll use KEYS for small databases
                    # For larger databases, we'll still use SCAN but with better safeguards

                    # First, check the database size
                    try:
                        db_size = r.dbsize()
                        print(f"Database size: {db_size} keys")

                        # If database is small (less than 10000 keys) or force_keys is True, use KEYS instead of SCAN
                        if db_size < 10000 or force_keys:
                            if force_keys:
                                print(f"Using KEYS command (forced by --force-keys option)")
                            else:
                                print(f"Using KEYS command for small database ({db_size} keys)")
                            all_keys = r.keys(pattern=pattern)
                            print(f"Found {len(all_keys)} keys matching pattern '{pattern}'")

                            # Process all keys directly
                            for key in all_keys:
                                # Check if we should stop
                                if self._stop_event.is_set():
                                    self._export_status = "Export operation cancelled."
                                    print("Export operation cancelled.")
                                    return

                                try:
                                    # Handle the key (don't try to decode)
                                    key_str = self._format_for_command(key)

                                    # Get the key type
                                    key_type = r.type(key)
                                    if isinstance(key_type, bytes):
                                        key_type = key_type.decode('utf-8', errors='replace')

                                    # Export based on key type
                                    if key_type == 'string':
                                        value = r.get(key)
                                        value_str = self._format_for_command(value)
                                        f.write(f'SET {key_str} {value_str}\n')

                                    elif key_type == 'hash':
                                        hash_data = r.hgetall(key)
                                        cmd_parts = [f'HSET {key_str}']

                                        for field, value in hash_data.items():
                                            field_str = self._format_for_command(field)
                                            value_str = self._format_for_command(value)
                                            cmd_parts.append(f'{field_str} {value_str}')

                                        f.write(' '.join(cmd_parts) + '\n')

                                    elif key_type == 'list':
                                        list_data = r.lrange(key, 0, -1)
                                        f.write(f'DEL {key_str}\n')

                                        cmd_parts = [f'RPUSH {key_str}']
                                        for item in list_data:
                                            item_str = self._format_for_command(item)
                                            cmd_parts.append(item_str)

                                        f.write(' '.join(cmd_parts) + '\n')

                                    elif key_type == 'set':
                                        set_data = r.smembers(key)
                                        f.write(f'DEL {key_str}\n')

                                        cmd_parts = [f'SADD {key_str}']
                                        for item in set_data:
                                            item_str = self._format_for_command(item)
                                            cmd_parts.append(item_str)

                                        f.write(' '.join(cmd_parts) + '\n')

                                    elif key_type == 'zset':
                                        zset_data = r.zrange(key, 0, -1, withscores=True)
                                        f.write(f'DEL {key_str}\n')

                                        cmd_parts = [f'ZADD {key_str}']
                                        for item, score in zset_data:
                                            item_str = self._format_for_command(item)
                                            cmd_parts.append(f'{score} {item_str}')

                                        f.write(' '.join(cmd_parts) + '\n')

                                    elif key_type == 'stream':
                                        # For streams, we need to get all entries and their fields
                                        stream_data = r.xrange(key, '-', '+')
                                        f.write(f'DEL {key_str}\n')

                                        for entry_id, fields in stream_data:
                                            # Entry ID is always ASCII
                                            if isinstance(entry_id, bytes):
                                                entry_id = entry_id.decode('ascii', errors='replace')

                                            cmd = f'XADD {key_str} {entry_id}'
                                            for field, value in fields.items():
                                                field_str = self._format_for_command(field)
                                                value_str = self._format_for_command(value)
                                                cmd += f' {field_str} {value_str}'
                                            f.write(cmd + '\n')

                                    # Handle ReJSON-RL type (Redis JSON)
                                    elif key_type == 'ReJSON-RL':
                                        try:
                                            # Use the JSON module (assumed to be available in Redis 8)
                                            json_data = r.json().get(key)

                                            # Convert the JSON data to a string
                                            json_str = json.dumps(json_data)
                                            value_str = self._format_for_command(json_str)

                                            # Write the JSON.SET command
                                            f.write(f'JSON.SET {key_str} $ {value_str}\n')
                                        except Exception as e:
                                            print(f"Error exporting JSON data for key {key_str}: {str(e)}")
                                            f.write(f'# Error exporting JSON data for key {key_str}: {str(e)}\n')

                                    # Handle other types or add a comment for unsupported types
                                    else:
                                        f.write(f'# Unsupported type {key_type} for key {key_str}\n')

                                    processed_keys += 1

                                    # Update status every 10 keys
                                    if processed_keys % 10 == 0:
                                        self._export_status = f"Exported {processed_keys} keys..."
                                        print(f"Progress: Exported {processed_keys} keys...")

                                except KeyboardInterrupt:
                                    self._stop_event.set()
                                    self._export_status = "Export operation cancelled by keyboard interrupt."
                                    print("Export operation cancelled by keyboard interrupt.")
                                    return
                                except Exception as e:
                                    print(f"Error processing key {key}: {str(e)}")
                                    continue  # Skip this key and continue with the next one

                            # All done with KEYS approach
                            print(f"Completed exporting {processed_keys} keys using KEYS command.")

                        # For larger databases, use SCAN with better safeguards
                        else:
                            print(f"Using SCAN command for large database ({db_size} keys)")

                            # Track seen cursors to detect loops
                            seen_cursors = set()
                            iteration_count = 0
                            last_key_count = 0

                            # Start with cursor 0
                            cursor = '0'

                            while iteration_count < max_iterations:
                                iteration_count += 1

                                # Check if we should stop (allows Ctrl+C to work)
                                if self._stop_event.is_set():
                                    self._export_status = "Export operation cancelled."
                                    print("Export operation cancelled.")
                                    return

                                # Check for cursor loops
                                if cursor in seen_cursors and cursor != '0':
                                    print(f"Warning: Cursor {cursor} has been seen before. Breaking loop.")
                                    break

                                # Add cursor to seen set
                                seen_cursors.add(cursor)

                                try:
                                    # Get a batch of keys
                                    cursor, keys = r.scan(cursor=cursor, match=pattern, count=batch_size)

                                    # Convert cursor to string if it's bytes
                                    if isinstance(cursor, bytes):
                                        cursor = cursor.decode('utf-8')

                                    print(f"SCAN iteration {iteration_count}: cursor={cursor}, keys={len(keys)}")

                                    # Check if we're making progress
                                    if len(keys) == 0 and iteration_count > 3:
                                        print("Warning: No keys returned in this iteration.")

                                    # Process the keys in this batch
                                    for key in keys:
                                        # Check if we should stop
                                        if self._stop_event.is_set():
                                            self._export_status = "Export operation cancelled."
                                            print("Export operation cancelled.")
                                            return

                                        try:
                                            # Handle the key (don't try to decode)
                                            key_str = self._format_for_command(key)

                                            # Get the key type
                                            key_type = r.type(key)
                                            if isinstance(key_type, bytes):
                                                key_type = key_type.decode('utf-8', errors='replace')

                                            # Export based on key type
                                            if key_type == 'string':
                                                value = r.get(key)
                                                value_str = self._format_for_command(value)
                                                f.write(f'SET {key_str} {value_str}\n')

                                            elif key_type == 'hash':
                                                hash_data = r.hgetall(key)
                                                cmd_parts = [f'HSET {key_str}']

                                                for field, value in hash_data.items():
                                                    field_str = self._format_for_command(field)
                                                    value_str = self._format_for_command(value)
                                                    cmd_parts.append(f'{field_str} {value_str}')

                                                f.write(' '.join(cmd_parts) + '\n')

                                            elif key_type == 'list':
                                                list_data = r.lrange(key, 0, -1)
                                                f.write(f'DEL {key_str}\n')

                                                cmd_parts = [f'RPUSH {key_str}']
                                                for item in list_data:
                                                    item_str = self._format_for_command(item)
                                                    cmd_parts.append(item_str)

                                                f.write(' '.join(cmd_parts) + '\n')

                                            elif key_type == 'set':
                                                set_data = r.smembers(key)
                                                f.write(f'DEL {key_str}\n')

                                                cmd_parts = [f'SADD {key_str}']
                                                for item in set_data:
                                                    item_str = self._format_for_command(item)
                                                    cmd_parts.append(item_str)

                                                f.write(' '.join(cmd_parts) + '\n')

                                            elif key_type == 'zset':
                                                zset_data = r.zrange(key, 0, -1, withscores=True)
                                                f.write(f'DEL {key_str}\n')

                                                cmd_parts = [f'ZADD {key_str}']
                                                for item, score in zset_data:
                                                    item_str = self._format_for_command(item)
                                                    cmd_parts.append(f'{score} {item_str}')

                                                f.write(' '.join(cmd_parts) + '\n')

                                            elif key_type == 'stream':
                                                # For streams, we need to get all entries and their fields
                                                stream_data = r.xrange(key, '-', '+')
                                                f.write(f'DEL {key_str}\n')

                                                for entry_id, fields in stream_data:
                                                    # Entry ID is always ASCII
                                                    if isinstance(entry_id, bytes):
                                                        entry_id = entry_id.decode('ascii', errors='replace')

                                                    cmd = f'XADD {key_str} {entry_id}'
                                                    for field, value in fields.items():
                                                        field_str = self._format_for_command(field)
                                                        value_str = self._format_for_command(value)
                                                        cmd += f' {field_str} {value_str}'
                                                    f.write(cmd + '\n')

                                            # Handle ReJSON-RL type (Redis JSON)
                                            elif key_type == 'ReJSON-RL':
                                                try:
                                                    # Use the JSON module (assumed to be available in Redis 8)
                                                    json_data = r.json().get(key)

                                                    # Convert the JSON data to a string
                                                    json_str = json.dumps(json_data)
                                                    value_str = self._format_for_command(json_str)

                                                    # Write the JSON.SET command
                                                    f.write(f'JSON.SET {key_str} $ {value_str}\n')
                                                except Exception as e:
                                                    print(f"Error exporting JSON data for key {key_str}: {str(e)}")
                                                    f.write(f'# Error exporting JSON data for key {key_str}: {str(e)}\n')

                                            # Handle other types or add a comment for unsupported types
                                            else:
                                                f.write(f'# Unsupported type {key_type} for key {key_str}\n')

                                            processed_keys += 1

                                            # Update status every 10 keys
                                            if processed_keys % 10 == 0:
                                                self._export_status = f"Exported {processed_keys} keys..."
                                                print(f"Progress: Exported {processed_keys} keys...")

                                        except KeyboardInterrupt:
                                            self._stop_event.set()
                                            self._export_status = "Export operation cancelled by keyboard interrupt."
                                            print("Export operation cancelled by keyboard interrupt.")
                                            return
                                        except Exception as e:
                                            print(f"Error processing key {key}: {str(e)}")
                                            continue  # Skip this key and continue with the next one

                                    # Check if we're making progress
                                    if processed_keys == last_key_count and iteration_count > 5:
                                        print("Warning: No new keys processed in this iteration.")

                                    last_key_count = processed_keys

                                    # If cursor is 0, we've completed the scan
                                    if cursor == '0':
                                        print("SCAN completed (cursor is 0)")
                                        break

                                except KeyboardInterrupt:
                                    self._stop_event.set()
                                    self._export_status = "Export operation cancelled by keyboard interrupt."
                                    print("Export operation cancelled by keyboard interrupt.")
                                    return
                                except Exception as e:
                                    print(f"Error during SCAN: {str(e)}")
                                    # Try to continue with the next cursor
                                    if cursor == '0':
                                        break

                            # Check if we hit the iteration limit
                            if iteration_count >= max_iterations:
                                self._export_status = f"Export operation stopped after {max_iterations} iterations (safety limit)."
                                print(f"Warning: Export operation stopped after {max_iterations} iterations (safety limit).")

                    except KeyboardInterrupt:
                        self._stop_event.set()
                        self._export_status = "Export operation cancelled by keyboard interrupt."
                        print("Export operation cancelled by keyboard interrupt.")
                        return
                    except Exception as e:
                        self._export_status = f"Error determining database size: {str(e)}"
                        print(f"Error determining database size: {str(e)}")
                        return

                except KeyboardInterrupt:
                    self._stop_event.set()
                    self._export_status = "Export operation cancelled by keyboard interrupt."
                    print("Export operation cancelled by keyboard interrupt.")
                    return
                except Exception as e:
                    self._export_status = f"Error during key export: {str(e)}"
                    print(f"Error during export: {str(e)}")
                    return

                # Final status update
                self._export_status = f"Completed exporting {processed_keys} keys."
                print(f"Completed exporting {processed_keys} keys.")

            # Check if the file was written successfully
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"Export file created: {filepath} (size: {file_size} bytes)")

                if file_size == 0:
                    self._export_status = f"Warning: Export file is empty. No keys were exported."
                    self._current_operation = None
                    return
            else:
                self._export_status = f"Error: Failed to create export file."
                self._current_operation = None
                return

            # Update state with successful export
            state = self._state.get_extension_state('data') or {}
            state['last_export'] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'pattern': pattern,
                'file': filepath,
                'keys_exported': processed_keys,
                'file_size': file_size
            }
            self._state.set_extension_state('data', state)

            self._export_status = f"Export completed successfully. {processed_keys} keys exported to {filepath} (size: {file_size} bytes)."
            self._current_operation = None

            # Restore original signal handler if it exists
            import signal
            if hasattr(self, '_original_sigint_handler'):
                try:
                    signal.signal(signal.SIGINT, self._original_sigint_handler)
                    print("Restored original SIGINT handler after export completion")
                except Exception:
                    pass  # Ignore errors when restoring

        except Exception as e:
            self._export_status = f"Error during export: {str(e)}"
            self._current_operation = None

            # Restore original signal handler if it exists
            import signal
            if hasattr(self, '_original_sigint_handler'):
                try:
                    signal.signal(signal.SIGINT, self._original_sigint_handler)
                    print("Restored original SIGINT handler after export error")
                except Exception:
                    pass  # Ignore errors when restoring

    def _import(self, args: list) -> str:
        """Import Redis data from a file."""
        parser = argparse.ArgumentParser(description='Import Redis data')
        parser.add_argument('--file', type=str, required=True, help='Path to the import file')

        try:
            parsed_args = parser.parse_args(args)
            file_path = parsed_args.file

            # Check if the file exists
            if not os.path.isfile(file_path):
                return f"Error: File '{file_path}' does not exist."

            # Get the current Redis connection from the connection manager
            redis_client = self._connection_manager.get_redis_client()

            if redis_client:
                # Get connection parameters from the connection manager
                host, port, db, password = self._connection_manager.get_connection_parameters()
                # Check if this is a cluster connection
                is_cluster = self._connection_manager.is_cluster_connection()
                if is_cluster:
                    print(f"Using current Redis Cluster connection from connection manager: {host}:{port}")
                else:
                    print(f"Using current Redis connection from connection manager: {host}:{port} (db: {db})")
            elif self._cli and hasattr(self._cli, 'redis'):
                # Fall back to CLI connection if connection manager doesn't have a connection
                # This is for backward compatibility
                host = self._cli.host
                port = self._cli.port
                db = self._cli.redis.connection_pool.connection_kwargs.get('db', 0)
                password = self._cli.redis.connection_pool.connection_kwargs.get('password', None)
                print(f"Using current Redis connection from CLI: {host}:{port} (db: {db})")
            else:
                # Fall back to default connection if no connection is available
                host = 'localhost'
                port = 6379
                db = 0
                password = None
                print("No active connection available, using default connection: localhost:6379")

            try:
                # If we already have a Redis client from the connection manager, use it
                if redis_client:
                    # Use the client from the connection manager
                    r = redis_client

                    # Get the cluster status from the connection manager
                    is_cluster = self._connection_manager.is_cluster_connection()

                    if is_cluster:
                        print("Using existing Redis Cluster client from connection manager")
                    else:
                        print("Using existing Redis client from connection manager")
                else:
                    # We need to create a new client - let the connection manager handle the details
                    # of whether it's a cluster or not
                    print(f"Creating new Redis client for {host}:{port}")

                    # Create a connection in the connection manager
                    connection_info = {
                        'host': host,
                        'port': port,
                        'db': db,
                        'password': password
                    }

                    # Generate a temporary connection ID
                    import uuid
                    temp_conn_id = f"temp_{uuid.uuid4().hex[:8]}"

                    # Add the connection to the connection manager
                    self._connection_manager.add_connection(temp_conn_id, connection_info)

                    # Get the client from the connection manager
                    r = self._connection_manager.get_redis_client(temp_conn_id)

                    # Check if it's a cluster
                    is_cluster = self._connection_manager.is_cluster_connection(temp_conn_id)

                    if is_cluster:
                        print("Redis instance is part of a cluster")
                    else:
                        print("Using standard Redis client")

                    # We don't need to remove the temporary connection as it will be
                    # garbage collected when the connection manager is reinitialized
            except Exception as e:
                return f"Error creating Redis client: {str(e)}"

            # Connection info already printed above

            # Read and execute commands from the file
            with open(file_path, 'r') as f:
                lines = f.readlines()

                total_lines = len(lines)
                successful_commands = 0
                failed_commands = 0

                print(f"Importing {total_lines} lines from {file_path}...")

                # Report progress every 100 lines
                progress_interval = max(1, min(100, total_lines // 10))

                for i, line in enumerate(lines):
                    # Report progress
                    if i > 0 and i % progress_interval == 0:
                        print(f"Progress: {i}/{total_lines} lines processed ({i/total_lines*100:.1f}%)")
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    try:
                        # Parse the command
                        parts = []
                        current_part = ''
                        in_quotes = False

                        for char in line:
                            if char == '"' and (not current_part.endswith('\\') or current_part.endswith('\\\\')):
                                in_quotes = not in_quotes
                                current_part += char
                            elif char.isspace() and not in_quotes:
                                if current_part:
                                    parts.append(current_part)
                                    current_part = ''
                            else:
                                current_part += char

                        if current_part:
                            parts.append(current_part)

                        # Extract command and arguments
                        if not parts:
                            continue

                        command = parts[0].upper()
                        args = parts[1:]

                        # Process arguments - handle quoted strings and base64-encoded binary data
                        processed_args = []
                        for arg in args:
                            # Check if it's a quoted string
                            if arg.startswith('"') and arg.endswith('"'):
                                # Remove the quotes
                                arg = arg[1:-1]

                                # Check if it's base64-encoded binary data
                                if arg.startswith('\\x'):
                                    try:
                                        # Remove the \x prefix and decode from base64
                                        binary_data = base64.b64decode(arg[2:])
                                        processed_args.append(binary_data)
                                    except Exception as e:
                                        print(f"Warning: Failed to decode base64 data: {e}")
                                        # Fall back to the original string
                                        processed_args.append(arg)
                                else:
                                    # Unescape quotes
                                    arg = arg.replace('\\"', '"')
                                    processed_args.append(arg)
                            else:
                                # Not a quoted string, pass as is
                                processed_args.append(arg)

                        # Use the processed arguments
                        args = processed_args

                        # Execute the command
                        # Special handling for JSON.SET commands since they need to use the json() module
                        print(f"Executing command: {command} with args: {args}")
                        if command == 'JSON.SET':
                            # Special handling for JSON.SET commands
                            print(f"Executing JSON.SET command: {args}")
                            r.json().set(args[0], args[1], json.loads(args[2]))
                        else:
                            # For all other commands, use execute_command which works for both standard Redis and cluster
                            r.execute_command(command, *args)
                        successful_commands += 1

                    except Exception as e:
                        failed_commands += 1
                        print(f"Error executing command '{line}': {str(e)}")

            # Update state with successful import
            state = self._state.get_extension_state('data') or {}
            state['last_import'] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'file': file_path,
                'commands_executed': successful_commands,
                'commands_failed': failed_commands
            }
            self._state.set_extension_state('data', state)

            # Print final progress
            print(f"Import completed: {successful_commands} commands executed successfully, {failed_commands} failed.")

            return f"Import completed. {successful_commands} commands executed successfully, {failed_commands} failed."

        except Exception as e:
            return f"Error during import: {str(e)}"

    def _status(self) -> str:
        """Check the status of data export/import operations."""
        result = []

        # Check if an export operation is running
        if self._export_thread and self._export_thread.is_alive():
            result.append(f"Current operation: {self._current_operation}")
            result.append(f"Status: {self._export_status}")
            result.append("Use '/data export --cancel' to cancel the operation.")
            result.append("You can also press Ctrl+C to cancel the operation.")

            # Add thread information for debugging
            result.append(f"\nThread information:")
            result.append(f"  Thread alive: {self._export_thread.is_alive()}")
            result.append(f"  Thread daemon: {self._export_thread.daemon}")
            result.append(f"  Stop event is set: {self._stop_event.is_set()}")
        else:
            if self._export_status and "cancelled" in self._export_status.lower():
                result.append(f"Last operation was cancelled: {self._export_status}")
            else:
                result.append("No data operations currently running.")

        # Get information about the last export/import
        state = self._state.get_extension_state('data') or {}

        if 'last_export' in state:
            export_info = state['last_export']
            result.append("\nLast export:")
            result.append(f"  Time: {export_info.get('timestamp')}")
            result.append(f"  Pattern: {export_info.get('pattern')}")
            result.append(f"  File: {export_info.get('file')}")
            result.append(f"  Keys exported: {export_info.get('keys_exported')}")
            if 'file_size' in export_info:
                result.append(f"  File size: {export_info.get('file_size')} bytes")

            # Check if the file still exists
            file_path = export_info.get('file')
            if file_path and os.path.exists(file_path):
                result.append(f"  File status: Exists")
                if os.path.getsize(file_path) == 0:
                    result.append(f"  Warning: File is empty")
            elif file_path:
                result.append(f"  File status: Does not exist")

        if 'last_import' in state:
            import_info = state['last_import']
            result.append("\nLast import:")
            result.append(f"  Time: {import_info.get('timestamp')}")
            result.append(f"  File: {import_info.get('file')}")
            result.append(f"  Commands executed: {import_info.get('commands_executed')}")
            result.append(f"  Commands failed: {import_info.get('commands_failed')}")

        return '\n'.join(result)
