import os
import subprocess
import time
import socket
import redis

class SentinelDeployer:
    def __init__(self):
        # Default ports
        self.sentinel_port = 5000
        self.redis_ports = [40001, 40002, 40003]  # Master is first, replicas follow
        self.master_name = "mymaster"
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

    def start_redis_instances(self):
        """Start Redis instances (1 master, 2 replicas)."""
        # Start master first
        master_port = self.redis_ports[0]
        master_config = f"""
port {master_port}
daemonize no
logfile "redis-{master_port}.log"
dbfilename "dump-{master_port}.rdb"
dir ./
protected-mode no
        """
        with open(f"redis-{master_port}.conf", "w") as f:
            f.write(master_config)

        print(f"Starting Redis master on port {master_port}...")
        master_process = subprocess.Popen(
            ['redis-server', f'redis-{master_port}.conf'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(master_process)

        # Wait for master to be ready
        master_ready = False
        for _ in range(10):  # Try for 5 seconds
            if self.is_port_in_use(master_port):
                try:
                    # Try to connect to the master
                    r = redis.Redis(port=master_port)
                    r.ping()
                    master_ready = True
                    break
                except:
                    pass
            time.sleep(0.5)

        if not master_ready:
            raise Exception(f"Failed to start Redis master on port {master_port}")

        print(f"Redis master started successfully on port {master_port}")

        # Start replicas
        for i, port in enumerate(self.redis_ports[1:], 1):
            replica_config = f"""
port {port}
daemonize no
logfile "redis-{port}.log"
dbfilename "dump-{port}.rdb"
dir ./
protected-mode no
replicaof 127.0.0.1 {master_port}
            """
            with open(f"redis-{port}.conf", "w") as f:
                f.write(replica_config)

            print(f"Starting Redis replica {i} on port {port}...")
            replica_process = subprocess.Popen(
                ['redis-server', f'redis-{port}.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(replica_process)

            # Wait for replica to be ready
            replica_ready = False
            for _ in range(10):  # Try for 5 seconds
                if self.is_port_in_use(port):
                    try:
                        # Try to connect to the replica
                        r = redis.Redis(port=port)
                        r.ping()
                        replica_ready = True
                        break
                    except:
                        pass
                time.sleep(0.5)

            if not replica_ready:
                print(f"Warning: Failed to verify Redis replica on port {port}")
            else:
                print(f"Redis replica {i} started successfully on port {port}")

        # Verify replication is working
        try:
            master = redis.Redis(port=master_port)
            info = master.info('replication')
            if info.get('connected_slaves', 0) < len(self.redis_ports) - 1:
                print(f"Warning: Not all replicas are connected to the master. Connected: {info.get('connected_slaves', 0)}")
        except Exception as e:
            print(f"Warning: Could not verify replication status: {e}")

    def start_sentinel(self):
        """Start Redis Sentinel."""
        sentinel_config = f"""
port {self.sentinel_port}
daemonize no
logfile "sentinel-{self.sentinel_port}.log"
dir ./
sentinel monitor {self.master_name} 127.0.0.1 {self.redis_ports[0]} 2
sentinel down-after-milliseconds {self.master_name} 5000
sentinel failover-timeout {self.master_name} 60000
sentinel parallel-syncs {self.master_name} 1
        """
        with open(f"sentinel-{self.sentinel_port}.conf", "w") as f:
            f.write(sentinel_config)

        print(f"Starting Redis Sentinel on port {self.sentinel_port}...")
        sentinel_process = subprocess.Popen(
            ['redis-sentinel', f'sentinel-{self.sentinel_port}.conf'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(sentinel_process)

        # Wait for sentinel to be ready
        sentinel_ready = False
        for _ in range(10):  # Try for 5 seconds
            if self.is_port_in_use(self.sentinel_port):
                try:
                    # Try to connect to the sentinel
                    s = redis.Redis(port=self.sentinel_port)
                    s.ping()
                    sentinel_ready = True
                    break
                except:
                    pass
            time.sleep(0.5)

        if not sentinel_ready:
            print(f"Warning: Failed to verify Redis Sentinel on port {self.sentinel_port}")
        else:
            print(f"Redis Sentinel started successfully on port {self.sentinel_port}")

        # Give sentinel time to discover replicas
        print("Waiting for Sentinel to discover all instances...")
        time.sleep(3)

    def check_sentinel(self):
        """Check the status of the Sentinel setup.

        Returns:
            str: A string containing the sentinel info or an error message.

        Raises:
            Exception: If there's an error connecting to the sentinel.
        """
        # First check direct Redis instances
        master_status = "Unknown"
        replica_statuses = []

        try:
            # Check master
            master = redis.Redis(port=self.redis_ports[0])
            master_info = master.info()
            master_status = "Running"

            # Check master is running properly
            master.info('replication')

            # Check replicas
            for i, port in enumerate(self.redis_ports[1:], 1):
                try:
                    replica = redis.Redis(port=port)
                    # Verify replica is running
                    replica.ping()
                    replica_repl = replica.info('replication')

                    if replica_repl.get('master_link_status') == 'up':
                        replica_statuses.append(f"Replica {i} (port {port}): Connected to master")
                    else:
                        replica_statuses.append(f"Replica {i} (port {port}): Disconnected from master")
                except Exception as e:
                    replica_statuses.append(f"Replica {i} (port {port}): Error - {str(e)}")
        except Exception as e:
            master_status = f"Error - {str(e)}"

        # Now check Sentinel
        try:
            # Connect to sentinel
            sentinel = redis.Redis(port=self.sentinel_port)

            # Get sentinel info
            sentinel_info = sentinel.info()

            # Get master info
            master_info = sentinel.execute_command('SENTINEL', 'master', self.master_name)

            # Get replicas info
            replicas_info = sentinel.execute_command('SENTINEL', 'replicas', self.master_name)

            # Format the info for display
            formatted_info = "Sentinel Info:\n"

            # Add Redis instances direct status
            formatted_info += "\nDirect Redis Status:\n"
            formatted_info += f"  Master (port {self.redis_ports[0]}): {master_status}\n"
            for status in replica_statuses:
                formatted_info += f"  {status}\n"

            # Format sentinel info
            formatted_info += f"\nSentinel Status:\n"
            formatted_info += f"  Version: {sentinel_info.get('redis_version', 'unknown')}\n"
            formatted_info += f"  Port: {self.sentinel_port}\n"

            # Format master info
            if isinstance(master_info, list):
                formatted_info += "\nMaster (as seen by Sentinel):\n"
                # Convert list to dict for easier access
                master_dict = {}
                for i in range(0, len(master_info), 2):
                    if i+1 < len(master_info):
                        key = master_info[i].decode('utf-8') if isinstance(master_info[i], bytes) else str(master_info[i])
                        value = master_info[i+1].decode('utf-8') if isinstance(master_info[i+1], bytes) else str(master_info[i+1])
                        master_dict[key] = value

                # Display important master info
                formatted_info += f"  Name: {self.master_name}\n"
                formatted_info += f"  IP: {master_dict.get('ip', 'unknown')}\n"
                formatted_info += f"  Port: {master_dict.get('port', 'unknown')}\n"
                formatted_info += f"  Flags: {master_dict.get('flags', 'unknown')}\n"
                formatted_info += f"  Replicas: {master_dict.get('num-slaves', '0')}\n"

                # Add more detailed status
                if 'disconnected' in master_dict.get('flags', ''):
                    formatted_info += f"  Status: Disconnected (Sentinel cannot reach the master)\n"
                    formatted_info += f"  Last Ping: {master_dict.get('last-ping-sent', 'unknown')}\n"
                    formatted_info += f"  Last OK Ping: {master_dict.get('last-ok-ping-reply', 'unknown')}\n"
                else:
                    formatted_info += f"  Status: Connected\n"

            # Format replicas info
            if isinstance(replicas_info, list):
                formatted_info += "\nReplicas (as seen by Sentinel):\n"
                if not replicas_info:
                    formatted_info += "  No replicas detected by Sentinel\n"

                for i, replica in enumerate(replicas_info):
                    if isinstance(replica, list):
                        # Convert list to dict for easier access
                        replica_dict = {}
                        for j in range(0, len(replica), 2):
                            if j+1 < len(replica):
                                key = replica[j].decode('utf-8') if isinstance(replica[j], bytes) else str(replica[j])
                                value = replica[j+1].decode('utf-8') if isinstance(replica[j+1], bytes) else str(replica[j+1])
                                replica_dict[key] = value

                        # Display important replica info
                        formatted_info += f"  Replica {i+1}:\n"
                        formatted_info += f"    IP: {replica_dict.get('ip', 'unknown')}\n"
                        formatted_info += f"    Port: {replica_dict.get('port', 'unknown')}\n"
                        formatted_info += f"    Flags: {replica_dict.get('flags', 'unknown')}\n"

                        # Add more detailed status
                        if 'disconnected' in replica_dict.get('flags', ''):
                            formatted_info += f"    Status: Disconnected\n"
                        else:
                            formatted_info += f"    Status: Connected\n"

            # Add troubleshooting info if needed
            if master_status.startswith("Error") or 'disconnected' in master_dict.get('flags', ''):
                formatted_info += "\nTroubleshooting:\n"
                formatted_info += "  If Sentinel cannot connect to the master or replicas, check:\n"
                formatted_info += "  1. Firewall settings\n"
                formatted_info += "  2. Redis protected-mode (should be 'no')\n"
                formatted_info += "  3. Redis bind settings\n"
                formatted_info += "  4. Network connectivity\n"

            return formatted_info

        except Exception as e:
            # If we can't connect to Sentinel, return a basic status
            formatted_info = "Sentinel Info (Limited - Sentinel connection failed):\n\n"
            formatted_info += f"Error connecting to Sentinel: {str(e)}\n\n"

            # Add Redis instances direct status
            formatted_info += "Direct Redis Status:\n"
            formatted_info += f"  Master (port {self.redis_ports[0]}): {master_status}\n"
            for status in replica_statuses:
                formatted_info += f"  {status}\n"

            return formatted_info

    def cleanup(self):
        """Stop all processes and clean up files."""
        # Stop processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(1)
            except:
                pass
        self.processes = []

        # Kill any remaining processes on our ports
        all_ports = [self.sentinel_port] + self.redis_ports
        for port in all_ports:
            self.kill_processes_by_port(port, force=True)

        # Clean up files
        for port in self.redis_ports:
            try:
                os.remove(f'redis-{port}.conf')
                os.remove(f'redis-{port}.log')
                os.remove(f'dump-{port}.rdb')
            except:
                pass

        try:
            os.remove(f'sentinel-{self.sentinel_port}.conf')
            os.remove(f'sentinel-{self.sentinel_port}.log')
        except:
            pass
