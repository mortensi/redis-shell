import os
import subprocess
import time
import socket
import redis

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
        for port in self.ports:
            config = f"port {port}\ncluster-enabled yes\ncluster-config-file nodes-{port}.conf\n"
            with open(f"redis-{port}.conf", "w") as f:
                f.write(config)

            process = subprocess.Popen(
                ['redis-server', f'redis-{port}.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            time.sleep(0.5)

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
        # Stop Redis processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(1)
            except:
                pass
        self.processes = []

        # Clean up files
        for port in self.ports:
            try:
                os.remove(f'redis-{port}.conf')
                os.remove(f'nodes-{port}.conf')
            except:
                pass
