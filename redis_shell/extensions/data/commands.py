from typing import Optional, Awaitable
import argparse
import os
import glob
import datetime
import base64
import json
import logging
from redis_shell.state_manager import StateManager
from redis_shell.connection_manager import ConnectionManager
from redis_shell.utils.file_utils import PathHandler
from redis_shell.utils.completion_utils import completion_registry

logger = logging.getLogger(__name__)

class DataCommands:
    def __init__(self, cli=None):
        self._state = StateManager()
        self._connection_manager = ConnectionManager()
        # Store reference to CLI instance (for backward compatibility)
        self._cli = cli

    def get_key_patterns(self, incomplete=""):
        """Return key pattern completions for Redis keys."""
        return completion_registry.get_completions("key_patterns", incomplete)

    def get_folders(self, incomplete=""):
        """Return folder completions."""
        return PathHandler.get_directory_completions(incomplete)

    def get_export_files(self, incomplete=""):
        """Return export file completions."""
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
        """Format a value for use in a Redis command."""
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

    def resolve_awaitable_sync(self, value):
        """Utility function to resolve Awaitable types synchronously."""
        if isinstance(value, Awaitable):
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(value)
            finally:
                loop.close()
        return value

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
        parser = argparse.ArgumentParser(description='Export Redis data')
        parser.add_argument('--pattern', type=str, default='*', help='Pattern to match keys (default: "*")')
        parser.add_argument('--folder', type=str, default='.', help='Folder to save the export file')

        try:
            parsed_args = parser.parse_args(args)
            pattern = parsed_args.pattern
            folder = parsed_args.folder

            # Get Redis client
            r = self._connection_manager.get_redis_client()
            if not r and self._cli and hasattr(self._cli, 'redis'):
                r = self._cli.redis
            if not r:
                return "Error: No active Redis connection available. Please create a connection first with /connection create."

            # Generate filename
            now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            host = r.connection_pool.connection_kwargs.get('host', 'localhost')
            port = r.connection_pool.connection_kwargs.get('port', 6379)
            filename = f"redis-export-{now}-{host}-{port}.txt"
            filepath = os.path.join(folder, filename)

            # Create folder if needed
            os.makedirs(folder, exist_ok=True)
            print(f"Exporting to: {filepath}")

            # Export data
            processed_keys = 0
            start_time = datetime.datetime.now()
            print(f"Starting export at {start_time}")

            with open(filepath, 'w') as f:
                # Use a larger scan count for better performance
                scan_count_param = 1000
                cursor = 0
                scan_count = 0

                # For specific patterns, try KEYS first if it's likely to be faster
                if '*' not in pattern or pattern.count('*') == 1:
                    try:
                        print(f"Trying KEYS command for pattern '{pattern}'...")
                        keys_start = datetime.datetime.now()
                        all_keys = self.resolve_awaitable_sync(r.keys(pattern))
                        keys_time = (datetime.datetime.now() - keys_start).total_seconds()
                        print(f"KEYS found {len(all_keys)} keys in {keys_time:.3f}s")

                        # Process all keys at once
                        for key in all_keys:
                            self._export_single_key(r, f, key)
                            processed_keys += 1
                            if processed_keys % 100 == 0:
                                print(f"Exported {processed_keys} keys...")
                    except Exception as e:
                        print(f"KEYS failed ({e}), falling back to SCAN...")
                        # Fall back to SCAN if KEYS fails
                        processed_keys = 0
                        cursor = 0

                # Use SCAN if KEYS wasn't used or failed
                if processed_keys == 0:
                    while cursor != 0 or processed_keys == 0:
                        scan_start = datetime.datetime.now()
                        scan_result = self.resolve_awaitable_sync(r.scan(cursor=cursor, match=pattern, count=scan_count_param))
                        cursor, keys = int(scan_result[0]), scan_result[1]
                        scan_count += 1
                        scan_time = (datetime.datetime.now() - scan_start).total_seconds()

                        if len(keys) > 0 or scan_count % 10 == 0:  # Only log every 10th empty scan
                            print(f"SCAN #{scan_count}: cursor={cursor}, found {len(keys)} keys, took {scan_time:.3f}s")

                        for key in keys:
                            self._export_single_key(r, f, key)
                            processed_keys += 1
                            if processed_keys % 100 == 0:
                                print(f"Exported {processed_keys} keys...")


            # Save export info to state
            state = self._state.get_extension_state('data') or {}
            state['last_export'] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'pattern': pattern,
                'file': filepath,
                'keys_exported': processed_keys,
                'file_size': os.path.getsize(filepath)
            }
            self._state.set_extension_state('data', state)

            return f"Export completed. {processed_keys} keys exported to {filepath}"

        except Exception as e:
            return f"Error during export: {str(e)}"

    def _export_single_key(self, r, f, key):
        """Export a single key to the file."""
        # Decode key for display and Redis operations
        if isinstance(key, bytes):
            key_display = key.decode('utf-8', errors='replace')
            key_for_redis = key_display  # Use decoded string for Redis operations
        else:
            key_display = str(key)
            key_for_redis = key_display

        key_str = self._format_for_command(key)

        # Get key type
        key_type = self.resolve_awaitable_sync(r.type(key_for_redis))
        if isinstance(key_type, bytes):
            key_type = key_type.decode('utf-8', errors='replace')

        # Export based on type
        if key_type == 'string':
            value = self.resolve_awaitable_sync(r.get(key_for_redis))
            value_str = self._format_for_command(value)
            f.write(f'SET {key_str} {value_str}\n')
        elif key_type == 'hash':
            hash_data = self.resolve_awaitable_sync(r.hgetall(key_for_redis))
            cmd_parts = [f'HSET {key_str}']
            for field, value in hash_data.items():
                field_str = self._format_for_command(field)
                value_str = self._format_for_command(value)
                cmd_parts.append(f'{field_str} {value_str}')
            f.write(' '.join(cmd_parts) + '\n')
        elif key_type == 'list':
            list_data = self.resolve_awaitable_sync(r.lrange(key_for_redis, 0, -1))
            f.write(f'DEL {key_str}\n')
            cmd_parts = [f'RPUSH {key_str}']
            for item in list_data:
                cmd_parts.append(self._format_for_command(item))
            f.write(' '.join(cmd_parts) + '\n')
        elif key_type == 'set':
            set_data = self.resolve_awaitable_sync(r.smembers(key_for_redis))
            f.write(f'DEL {key_str}\n')
            cmd_parts = [f'SADD {key_str}']
            for item in set_data:
                cmd_parts.append(self._format_for_command(item))
            f.write(' '.join(cmd_parts) + '\n')
        elif key_type == 'zset':
            zset_data = self.resolve_awaitable_sync(r.zrange(key_for_redis, 0, -1, withscores=True))
            f.write(f'DEL {key_str}\n')
            cmd_parts = [f'ZADD {key_str}']
            for item, score in zset_data:
                cmd_parts.append(f'{score} {self._format_for_command(item)}')
            f.write(' '.join(cmd_parts) + '\n')
        elif key_type == 'stream':
            stream_data = self.resolve_awaitable_sync(r.xrange(key_for_redis, '-', '+'))
            f.write(f'DEL {key_str}\n')
            for entry_id, fields in stream_data:
                if isinstance(entry_id, bytes):
                    entry_id = entry_id.decode('ascii', errors='replace')
                cmd = f'XADD {key_str} {entry_id}'
                for field, value in fields.items():
                    cmd += f' {self._format_for_command(field)} {self._format_for_command(value)}'
                f.write(cmd + '\n')
        elif key_type in ['ReJSON-RL', 'TSDB-TYPE']:
            # Handle special Redis module types
            if key_type == 'ReJSON-RL':
                try:
                    json_data = self.resolve_awaitable_sync(r.json().get(key_for_redis))
                    # Convert to JSON string and encode as base64 to avoid parsing issues
                    json_str = json.dumps(json_data, ensure_ascii=False)
                    json_bytes = json_str.encode('utf-8')
                    json_b64 = base64.b64encode(json_bytes).decode('ascii')
                    f.write(f'# JSON.SET {key_str} $ <base64_json:{json_b64}>\n')
                except Exception as e:
                    f.write(f'# Error exporting JSON key {key_str}: {e}\n')
            elif key_type == 'TSDB-TYPE':
                try:
                    # Get TimeSeries info to understand the configuration
                    ts_info = self.resolve_awaitable_sync(r.execute_command('TS.INFO', key_for_redis))

                    # Parse TS.INFO response to get configuration
                    info_dict = {}
                    if ts_info:
                        for i in range(0, len(ts_info), 2):
                            if i + 1 < len(ts_info):
                                info_key = ts_info[i].decode('utf-8') if isinstance(ts_info[i], bytes) else str(ts_info[i])
                                info_value = ts_info[i + 1]
                                if isinstance(info_value, bytes):
                                    info_value = info_value.decode('utf-8')
                                info_dict[info_key] = info_value

                    # Build TS.CREATE command with proper configuration
                    create_cmd = f'TS.CREATE {key_str}'

                    # Add retention if specified
                    if 'retentionTime' in info_dict and info_dict['retentionTime'] != '0':
                        create_cmd += f' RETENTION {info_dict["retentionTime"]}'

                    # Add duplicate policy - use LAST to allow overwrites during import
                    create_cmd += ' DUPLICATE_POLICY LAST'

                    # Add labels if they exist
                    if 'labels' in info_dict and info_dict['labels']:
                        labels = info_dict['labels']
                        if isinstance(labels, list) and len(labels) > 0:
                            create_cmd += ' LABELS'
                            for j in range(0, len(labels), 2):
                                if j + 1 < len(labels):
                                    label_key = labels[j].decode('utf-8') if isinstance(labels[j], bytes) else str(labels[j])
                                    label_value = labels[j + 1].decode('utf-8') if isinstance(labels[j + 1], bytes) else str(labels[j + 1])
                                    create_cmd += f' {label_key} {label_value}'

                    f.write(create_cmd + '\n')

                    # Export all data points
                    ts_range = self.resolve_awaitable_sync(r.execute_command('TS.RANGE', key_for_redis, '-', '+'))
                    if ts_range:  # Check if ts_range is not None
                        for timestamp, value in ts_range:
                            # Convert bytes values to proper numeric format
                            if isinstance(value, bytes):
                                try:
                                    # Try to decode and convert to float
                                    value_str = value.decode('utf-8')
                                    # Remove any quotes if present
                                    value_str = value_str.strip('"\'')
                                    # Convert to float to ensure it's a valid number
                                    numeric_value = float(value_str)
                                    f.write(f'TS.ADD {key_str} {timestamp} {numeric_value}\n')
                                except (UnicodeDecodeError, ValueError) as ve:
                                    f.write(f'# Error converting TimeSeries value for key {key_str}: {ve} (raw value: {value})\n')
                            else:
                                # Value is already in proper format
                                f.write(f'TS.ADD {key_str} {timestamp} {value}\n')
                except Exception as e:
                    f.write(f'# Error exporting TimeSeries key {key_str}: {e}\n')
        else:
            f.write(f'# Unsupported type {key_type} for key {key_str}\n')

        print(f"Exported: {key_display} ({key_type})")

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

            # Get the current Redis connection
            redis_client = self._connection_manager.get_redis_client()
            if not redis_client and self._cli and hasattr(self._cli, 'redis'):
                redis_client = self._cli.redis
            if not redis_client:
                return "Error: No active Redis connection available. Please create a connection first with /connection create."

            # Read and execute commands from the file
            with open(file_path, 'r') as f:
                lines = f.readlines()

                total_lines = len(lines)
                successful_commands = 0
                failed_commands = 0

                print(f"Importing {total_lines} lines from {file_path}...")

                for i, line in enumerate(lines):
                    # Report progress
                    if i > 0 and i % 100 == 0:
                        print(f"Progress: {i}/{total_lines} lines processed ({i/total_lines*100:.1f}%)")

                    line = line.strip()
                    # Skip empty lines and comments, but handle special JSON comments
                    if not line:
                        continue

                    # Handle special base64-encoded JSON comments
                    if line.startswith('# JSON.SET ') and '<base64_json:' in line:
                        # Extract the JSON.SET command from the comment
                        # Format: # JSON.SET "key" $ <base64_json:base64data>
                        try:
                            parts = line.split(' ', 3)  # ['#', 'JSON.SET', '"key"', '$ <base64_json:...>']
                            if len(parts) >= 4:
                                key_part = parts[2].strip('"')
                                path_and_data = parts[3]

                                # Extract base64 data
                                start_marker = '<base64_json:'
                                end_marker = '>'
                                start_idx = path_and_data.find(start_marker)
                                end_idx = path_and_data.find(end_marker, start_idx)

                                if start_idx != -1 and end_idx != -1:
                                    b64_data = path_and_data[start_idx + len(start_marker):end_idx]

                                    # Decode base64 and parse JSON
                                    json_bytes = base64.b64decode(b64_data)
                                    json_str = json_bytes.decode('utf-8')
                                    json_data = json.loads(json_str)

                                    # Execute the JSON.SET command
                                    self.resolve_awaitable_sync(redis_client.json().set(key_part, '$', json_data))
                                    successful_commands += 1
                                    continue
                        except Exception as e:
                            failed_commands += 1
                            print(f"ERROR: Failed to execute JSON command from comment '{line}'")
                            print(f"       Error: {str(e)}")
                            print()
                            continue

                    # Skip regular comments
                    if line.startswith('#'):
                        continue

                    command = "UNKNOWN"
                    args = []
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
                        if command == 'JSON.SET':
                            # Special handling for JSON.SET commands
                            key_name = args[0]
                            path = args[1]
                            json_str = args[2]

                            # Unescape the JSON string
                            unescaped_json = json_str.replace('\\"', '"').replace('\\\\', '\\')

                            # Parse the JSON
                            try:
                                json_data = json.loads(unescaped_json)
                                self.resolve_awaitable_sync(redis_client.json().set(key_name, path, json_data))
                            except json.JSONDecodeError as je:
                                # If JSON parsing fails, try using the original string as-is
                                print(f"Warning: JSON decode failed for {key_name}, trying raw string: {je}")
                                json_data = json.loads(json_str)
                                self.resolve_awaitable_sync(redis_client.json().set(key_name, path, json_data))
                        elif command in ['TS.CREATE', 'TS.ADD']:
                            # Special handling for time series commands
                            if command == 'TS.CREATE':
                                # For TS.CREATE, try to delete the key first if it exists to avoid conflicts
                                try:
                                    key_name = args[0]
                                    # Check if key exists and delete it
                                    if self.resolve_awaitable_sync(redis_client.exists(key_name)):
                                        self.resolve_awaitable_sync(redis_client.delete(key_name))
                                except Exception:
                                    pass  # Ignore errors when trying to delete

                            self.resolve_awaitable_sync(redis_client.execute_command(command, *args))
                        else:
                            # For all other commands, use execute_command
                            self.resolve_awaitable_sync(redis_client.execute_command(command, *args))

                        successful_commands += 1

                    except Exception as e:
                        failed_commands += 1
                        print(f"ERROR: Failed to execute command '{line.strip()}'")
                        print(f"       Command: {command}")
                        print(f"       Args: {args}")
                        print(f"       Error: {str(e)}")
                        print()

            # Update state with successful import
            state = self._state.get_extension_state('data') or {}
            state['last_import'] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'file': file_path,
                'commands_executed': successful_commands,
                'commands_failed': failed_commands
            }
            self._state.set_extension_state('data', state)

            print(f"Import completed: {successful_commands} commands executed successfully, {failed_commands} failed.")
            return f"Import completed. {successful_commands} commands executed successfully, {failed_commands} failed."

        except Exception as e:
            return f"Error during import: {str(e)}"

    def _status(self) -> str:
        """Check the status of data export/import operations."""
        result = []

        # Get information about the last export/import
        state = self._state.get_extension_state('data') or {}

        if 'last_export' in state:
            export_info = state['last_export']
            result.append("Last export:")
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

        if not result:
            result.append("No data operations have been performed yet.")

        return '\n'.join(result)
