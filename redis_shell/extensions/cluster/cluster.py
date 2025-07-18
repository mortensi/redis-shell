import os
import subprocess
import time
import socket
import redis
import shutil

class ClusterDeployer:
    def __init__(self):
        self.ports = [30001, 30002, 30003]
        self.processes = []

    @staticmethod
    def is_port_in_use(port):
        """Check if a port is in use.

        Args:
            port (int): The port to check

        Returns:
            bool: True if the port is in use, False otherwise
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    @staticmethod
    def kill_processes_by_port(port, force=False):
        """Kill all processes using a specific port.

        Args:
            port (int): The port to check
            force (bool): Whether to use SIGKILL (True) or SIGTERM (False)

        Returns:
            list: List of PIDs that were killed
        """
        import subprocess
        import os
        import signal

        killed_pids = []

        try:
            # Find processes using this port
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-t'],
                capture_output=True,
                text=True
            )

            if result.stdout:
                # The output might contain multiple PIDs, one per line
                for pid_str in result.stdout.strip().split('\n'):
                    try:
                        pid = int(pid_str.strip())
                        sig = signal.SIGKILL if force else signal.SIGTERM
                        os.kill(pid, sig)
                        killed_pids.append(pid)
                    except ValueError:
                        # Skip invalid PIDs
                        continue
                    except ProcessLookupError:
                        # Process already gone
                        continue
        except Exception:
            # Ignore errors
            pass

        return killed_pids

    def start_nodes(self):
        # Start Redis instances
        redis_server_path = self._find_redis_server()
        if not redis_server_path:
            raise RuntimeError("redis-server not found in PATH. Please ensure Redis is installed and accessible.")

        print(f"Using redis-server at: {redis_server_path}")

        # Check if any ports are already in use and clean them up
        ports_in_use = [port for port in self.ports if self.is_port_in_use(port)]
        if ports_in_use:
            print(f"Ports {ports_in_use} are already in use. Cleaning up existing Redis instances...")
            self.cleanup()
            # Wait a bit longer for cleanup to complete
            time.sleep(2)

            # Check again if ports are still in use
            still_in_use = [port for port in self.ports if self.is_port_in_use(port)]
            if still_in_use:
                raise RuntimeError(f"Could not free up ports {still_in_use}. Please manually stop Redis instances on these ports.")

        for port in self.ports:
            # Use a unique RDB filename for each cluster node to avoid conflicts
            # and ensure we start with a clean state
            rdb_filename = f"cluster-{port}.rdb"
            config = f"""port {port}
cluster-enabled yes
cluster-config-file nodes-{port}.conf
dbfilename {rdb_filename}
dir ./
"""
            with open(f"redis-{port}.conf", "w") as f:
                f.write(config)

            # Remove any existing RDB file for this port to ensure clean start
            if os.path.exists(rdb_filename):
                try:
                    os.remove(rdb_filename)
                    print(f"Removed existing RDB file: {rdb_filename}")
                except Exception as e:
                    print(f"Warning: Could not remove {rdb_filename}: {e}")

            try:
                process = subprocess.Popen(
                    [redis_server_path, f'redis-{port}.conf'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.processes.append(process)

                # Give the process a moment to start and check if it's still running
                time.sleep(0.5)
                if process.poll() is not None:
                    # Process has already terminated
                    stdout, stderr = process.communicate()
                    error_msg = f"Redis server on port {port} failed to start (exit code: {process.returncode})"
                    if stderr:
                        stderr_text = stderr.decode('utf-8', errors='replace').strip()
                        error_msg += f"\nSTDERR: {stderr_text}"
                    if stdout:
                        stdout_text = stdout.decode('utf-8', errors='replace').strip()
                        error_msg += f"\nSTDOUT: {stdout_text}"
                    raise RuntimeError(error_msg)

            except FileNotFoundError:
                raise RuntimeError(f"Failed to start redis-server: command not found at {redis_server_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to start Redis server on port {port}: {str(e)}")

    def _find_redis_server(self):
        """Find the redis-server executable in the system PATH."""
        # First try to find it using shutil.which
        redis_server_path = shutil.which('redis-server')
        if redis_server_path:
            return redis_server_path

        # If not found, try common installation paths
        common_paths = [
            '/usr/local/bin/redis-server',
            '/opt/homebrew/bin/redis-server',
            '/usr/bin/redis-server',
            '/opt/redis/bin/redis-server'
        ]

        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return None

    def create_cluster(self):
        # Connect to each node
        nodes = [redis.Redis(port=port) for port in self.ports]

        # Flush all data and reset cluster state
        for node in nodes:
            node.execute_command('FLUSHALL')
            node.execute_command('CLUSTER RESET')

        # Make nodes meet each other
        for i, node in enumerate(nodes):
            for port in self.ports[i+1:]:
                node.execute_command('CLUSTER MEET', '127.0.0.1', port)
        time.sleep(1)

        # Assign slots
        slots_per_node = 16384 // len(self.ports)
        for i, node in enumerate(nodes):
            start = i * slots_per_node
            end = start + slots_per_node - 1 if i < len(self.ports)-1 else 16383
            for slot in range(start, end + 1):
                node.execute_command('CLUSTER ADDSLOTS', slot)

    def check_cluster(self):
        """Check the status of the cluster.

        Returns:
            str: A string containing the cluster info or an error message.

        Raises:
            Exception: If there's an error connecting to the cluster.
        """
        node = redis.Redis(port=self.ports[0])

        # Get cluster info
        info = node.execute_command('CLUSTER INFO')

        # Format the info for display
        formatted_info = "Cluster Info:\n"

        # Handle different response types for CLUSTER INFO
        if isinstance(info, bytes):
            # If it's bytes, decode to string
            info_str = info.decode('utf-8')
            formatted_info += info_str

            # Parse the info string into a dictionary for easier access
            info_dict = {}
            for line in info_str.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
        elif isinstance(info, dict):
            # If it's already a dictionary, format it nicely
            for key, value in info.items():
                formatted_info += f"{key}: {value}\n"
        elif isinstance(info, str):
            # If it's already a string, use it directly
            formatted_info += info
        else:
            # For any other type, convert to string
            formatted_info += str(info)

        # Get cluster slots information
        try:
            slots = node.execute_command('CLUSTER SLOTS')

            # Add slots information to the output
            formatted_info += "\n\nCluster Slots:\n"

            # Process slots information
            if isinstance(slots, list):
                for slot_range in slots:
                    if isinstance(slot_range, list) and len(slot_range) >= 3:
                        start_slot = slot_range[0]
                        end_slot = slot_range[1]
                        master_info = slot_range[2]

                        if isinstance(master_info, list) and len(master_info) >= 2:
                            master_host = master_info[0]
                            if isinstance(master_host, bytes):
                                master_host = master_host.decode('utf-8')
                            master_port = master_info[1]

                            formatted_info += f"Slots {start_slot}-{end_slot}: Master {master_host}:{master_port}\n"

                            # Add replica information if available
                            if len(slot_range) > 3:
                                for i in range(3, len(slot_range)):
                                    replica_info = slot_range[i]
                                    if isinstance(replica_info, list) and len(replica_info) >= 2:
                                        replica_host = replica_info[0]
                                        if isinstance(replica_host, bytes):
                                            replica_host = replica_host.decode('utf-8')
                                        replica_port = replica_info[1]
                                        formatted_info += f"  Replica: {replica_host}:{replica_port}\n"
            else:
                formatted_info += f"Unexpected format: {slots}\n"
        except Exception as e:
            formatted_info += f"\nError getting CLUSTER SLOTS: {str(e)}\n"

        return formatted_info

    def cleanup(self):
        """Clean up the cluster by stopping processes and removing configuration files.

        This method will:
        1. Try to gracefully shut down Redis instances using the SHUTDOWN command
        2. Fall back to terminating processes if SHUTDOWN fails
        3. Remove all configuration files
        """
        # First, try to gracefully shut down Redis instances
        shutdown_success = {}
        for port in self.ports:
            shutdown_success[port] = False
            if self.is_port_in_use(port):
                try:
                    # Try to connect to Redis on this port
                    r = redis.Redis(host='localhost', port=port)
                    # Check if it's responsive
                    if r.ping():
                        # Send shutdown command
                        r.shutdown()
                        print(f"Gracefully shut down Redis server on port {port}")
                        shutdown_success[port] = True
                except Exception as e:
                    print(f"Could not gracefully shut down Redis on port {port}: {e}")

        # Give some time for Redis to shut down
        time.sleep(1)

        # For any instances that didn't shut down gracefully, try terminating processes
        # First, terminate processes we have references to
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(1)
            except Exception as e:
                print(f"Error terminating process: {e}")

        # Then check if any ports are still in use and try to kill those processes
        for port in self.ports:
            if not shutdown_success[port] and self.is_port_in_use(port):
                try:
                    # First try with SIGTERM
                    killed_pids = self.kill_processes_by_port(port, force=False)
                    for pid in killed_pids:
                        print(f"Stopped Redis server on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error stopping Redis on port {port}: {e}")

        # Check if any ports are still in use and try again with SIGKILL as a last resort
        time.sleep(0.5)
        for port in self.ports:
            if self.is_port_in_use(port):
                try:
                    # Try with SIGKILL
                    killed_pids = self.kill_processes_by_port(port, force=True)
                    for pid in killed_pids:
                        print(f"Forcefully stopped Redis server on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error forcefully stopping Redis on port {port}: {e}")

        # Clear the processes list
        self.processes = []

        # Clean up files
        for port in self.ports:
            try:
                # Try to remove configuration files
                if os.path.exists(f'redis-{port}.conf'):
                    os.remove(f'redis-{port}.conf')
                    print(f"Removed redis-{port}.conf")

                if os.path.exists(f'nodes-{port}.conf'):
                    os.remove(f'nodes-{port}.conf')
                    print(f"Removed nodes-{port}.conf")

                # Remove cluster-specific RDB files
                rdb_filename = f'cluster-{port}.rdb'
                if os.path.exists(rdb_filename):
                    os.remove(rdb_filename)
                    print(f"Removed {rdb_filename}")
            except Exception as e:
                print(f"Error removing configuration files for port {port}: {e}")
