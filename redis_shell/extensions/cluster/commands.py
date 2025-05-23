from typing import Optional, Dict, Any
import redis
import time
import os
import sys
import importlib.util

# Import ClusterDeployer directly from the module
cluster_module_path = os.path.join(os.path.dirname(__file__), 'cluster.py')
spec = importlib.util.spec_from_file_location("cluster_module", cluster_module_path)
cluster_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster_module)
ClusterDeployer = cluster_module.ClusterDeployer

from redis_shell.state_manager import StateManager
from redis_shell.config import config

class ClusterCommands:
    def __init__(self, cli=None):
        self._deployer = None
        self._state = StateManager()
        self._cli = cli  # Store reference to CLI instance

    def _get_deployer(self):
        if not self._deployer:
            self._deployer = ClusterDeployer()
        return self._deployer

    def handle_command(self, cmd: str, args: list) -> Optional[str]:
        """Handle cluster commands."""
        if cmd == "deploy":
            return self._deploy()
        elif cmd == "info":
            return self._info()
        elif cmd == "remove":
            return self._remove()
        elif cmd == "stop":
            return self._stop()
        elif cmd == "start":
            return self._start()
        return None

    def _deploy(self) -> str:
        """Deploy a new Redis cluster."""
        try:
            deployer = self._get_deployer()
            print("Starting Redis nodes...")
            deployer.start_nodes()

            print("Creating cluster...")
            deployer.create_cluster()

            # Save cluster configuration immediately after creation
            # This ensures the configuration is saved even if status check fails
            config.set('cluster', 'active', True)
            config.set('cluster', 'running', True)
            config.set('cluster', 'ports', deployer.ports)
            config.save_config()

            print("Checking cluster status...")
            try:
                status = deployer.check_cluster()
                # Update status in configuration
                config.set('cluster', 'status', status)
                config.save_config()

                # Explicitly save cluster state to the state manager
                self._state.set_extension_state('cluster', {
                    'active': True,
                    'running': True,
                    'ports': deployer.ports,
                    'status': status
                })

                return status
            except Exception as status_error:
                # If status check fails, still report success but with a warning
                print(f"Warning: Cluster created but could not get status: {str(status_error)}")
                return "Cluster deployed successfully, but status check failed. Use '/cluster info' to check status."

        except Exception as e:
            if self._deployer:
                self._deployer.cleanup()
            self._deployer = None

            # Clear cluster configuration only if we failed before saving it
            if 'cluster' in config.config:
                del config.config['cluster']
                config.save_config()

            return f"Error deploying cluster: {str(e)}"

    def _info(self) -> str:
        """Get cluster information.

        This method checks the status of a Redis cluster by:
        1. Reading cluster info from the configuration
        2. Attempting to connect to any available node in the cluster
        3. Checking the cluster status live
        """
        # First check if we have a cluster in the configuration
        cluster_config = config.get_section('cluster')
        ports_to_check = []

        if cluster_config.get('active') and 'ports' in cluster_config:
            # Get ports from configuration
            ports_to_check = cluster_config['ports']
            # Using ports from configuration
        else:
            # No cluster in configuration, use default ports
            # Use default ports from ClusterDeployer
            if not self._deployer:
                self._deployer = ClusterDeployer()
            ports_to_check = self._deployer.ports

        # Try to connect to any available node
        connected_port = None
        node = None

        for port in ports_to_check:
            if ClusterDeployer.is_port_in_use(port):
                try:
                    # Try to connect to this node
                    temp_node = redis.Redis(port=port)
                    # Check if it's responsive
                    temp_node.ping()
                    # Found a working node
                    connected_port = port
                    node = temp_node
                    # Successfully connected to Redis node
                    break
                except Exception as e:
                    # Port is in use but could not connect to Redis
                    continue

        # If we couldn't connect to any node
        if not node:
            # Update configuration if it exists
            if cluster_config.get('active'):
                config.set('cluster', 'running', False)
                config.save_config()

            return "No running Redis cluster found. Use '/cluster deploy' to create one."

        # We have a connection, now check if it's a cluster
        try:
            # Try to run a cluster command to verify it's a cluster
            # If this succeeds, it's a cluster; if it fails, it will throw an exception
            node.execute_command('CLUSTER INFO')

            # If we get here, it's a cluster. Update the deployer and state
            if not self._deployer:
                self._deployer = ClusterDeployer()

            # Update ports in deployer if needed
            if connected_port not in self._deployer.ports:
                # We connected to a port that's not in our default list
                # Try to get all cluster nodes
                try:
                    slots = node.execute_command('CLUSTER SLOTS')
                    cluster_ports = set()

                    # Extract all ports from slots info
                    if isinstance(slots, list):
                        for slot_range in slots:
                            if isinstance(slot_range, list) and len(slot_range) >= 3:
                                # Add master port
                                master_info = slot_range[2]
                                if isinstance(master_info, list) and len(master_info) >= 2:
                                    cluster_ports.add(master_info[1])

                                # Add replica ports
                                for i in range(3, len(slot_range)):
                                    replica_info = slot_range[i]
                                    if isinstance(replica_info, list) and len(replica_info) >= 2:
                                        cluster_ports.add(replica_info[1])

                    if cluster_ports:
                        self._deployer.ports = list(cluster_ports)
                        print(f"Updated cluster ports to: {self._deployer.ports}")
                except Exception as e:
                    # If we can't get slots info, just use the connected port
                    self._deployer.ports = [connected_port]
                    print(f"Could not get cluster slots, using connected port: {connected_port}")

            # Update configuration
            config.set('cluster', 'active', True)
            config.set('cluster', 'running', True)
            config.set('cluster', 'ports', self._deployer.ports)

            # Get detailed cluster status
            status = self._deployer.check_cluster()
            config.set('cluster', 'status', status)
            config.save_config()
            return status

        except Exception as e:
            # This is not a cluster or there was an error
            print(f"Error checking cluster status: {str(e)}")
            return f"Connected to Redis on port {connected_port}, but it doesn't appear to be a cluster or there was an error: {str(e)}"

    def _remove(self) -> str:
        """Remove the cluster and clean up.

        This method attempts to clean up the cluster regardless of the state in the configuration.
        It will:
        1. Try to get ports from the configuration
        2. If no configuration is found, use default ports
        3. Try to gracefully shut down Redis instances using the SHUTDOWN command
        4. Fall back to killing processes if SHUTDOWN fails
        5. Remove all cluster configuration files
        6. Clear the configuration
        """
        # Get ports to clean up
        ports_to_clean = []

        # Always reload the configuration from disk
        cluster_config = config.get_section('cluster')

        if cluster_config.get('active') and 'ports' in cluster_config:
            # Get ports from configuration
            ports_to_clean = cluster_config['ports']
            # Using ports from configuration
        else:
            # No cluster in configuration, use default ports
            # Use default ports from ClusterDeployer
            if not self._deployer:
                self._deployer = ClusterDeployer()
            ports_to_clean = self._deployer.ports

        # Create or update deployer
        if not self._deployer:
            self._deployer = ClusterDeployer()
        self._deployer.ports = ports_to_clean

        # First, try to gracefully shut down Redis instances
        shutdown_success = {}
        for port in ports_to_clean:
            shutdown_success[port] = False
            if ClusterDeployer.is_port_in_use(port):
                try:
                    # Try to connect to Redis on this port
                    r = redis.Redis(host='localhost', port=port)
                    # Check if it's responsive
                    if r.ping():
                        # Send shutdown command
                        r.shutdown()
                        # Gracefully shut down Redis server
                        shutdown_success[port] = True
                except Exception as e:
                    # Could not gracefully shut down Redis server
                    pass

        # Give some time for Redis to shut down
        time.sleep(1)

        # For any instances that didn't shut down gracefully, try killing processes
        killed_processes = False
        for port in ports_to_clean:
            if not shutdown_success[port] and ClusterDeployer.is_port_in_use(port):
                try:
                    # Try to kill processes on this port
                    killed_pids = ClusterDeployer.kill_processes_by_port(port, force=False)
                    if killed_pids:
                        killed_processes = True
                        for pid in killed_pids:
                            print(f"Stopped Redis server on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error stopping Redis on port {port}: {str(e)}")

        # If some processes were resistant, try again with force
        time.sleep(0.5)  # Give some time for processes to terminate
        for port in ports_to_clean:
            if ClusterDeployer.is_port_in_use(port):
                try:
                    # Kill processes using this port with SIGKILL
                    killed_pids = ClusterDeployer.kill_processes_by_port(port, force=True)
                    if killed_pids:
                        killed_processes = True
                        for pid in killed_pids:
                            print(f"Forcefully stopped Redis server on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error forcefully stopping Redis on port {port}: {str(e)}")

        # Clean up configuration files
        for port in ports_to_clean:
            try:
                # Try to remove configuration files
                if os.path.exists(f'redis-{port}.conf'):
                    os.remove(f'redis-{port}.conf')
                    print(f"Removed redis-{port}.conf")

                if os.path.exists(f'nodes-{port}.conf'):
                    os.remove(f'nodes-{port}.conf')
                    print(f"Removed nodes-{port}.conf")
            except Exception as e:
                print(f"Error removing configuration files for port {port}: {e}")

        # Clear deployer
        self._deployer = None

        # Remove cluster configuration from config
        # First, reload the configuration to ensure we have the latest
        config._load_config()

        if 'cluster' in config.config:
            del config.config['cluster']
            config.save_config()

        # Double-check that the configuration was cleared
        # Reload the configuration again to verify
        config._load_config()

        if 'cluster' in config.config:
            # If for some reason it's still there, try again with a different approach
            config.config['cluster'] = {}
            config.save_config()

        if any(shutdown_success.values()):
            return "Cluster processes gracefully shut down and configuration cleaned up."
        elif killed_processes:
            return "Cluster processes stopped and configuration cleaned up."
        else:
            return "No running cluster processes found. Configuration cleaned up."

    def _stop(self) -> str:
        """Stop the cluster without cleaning up data.

        This method will:
        1. Try to gracefully shut down Redis instances using the SHUTDOWN command
        2. Fall back to killing processes if SHUTDOWN fails
        3. Update the configuration to indicate the cluster is stopped but can be restarted
        """
        cluster_config = config.get_section('cluster')
        if not cluster_config.get('active'):
            return "No active cluster."

        if not self._deployer:
            # Recreate deployer from configuration
            self._deployer = ClusterDeployer()
            self._deployer.ports = cluster_config['ports']

        # First, try to gracefully shut down Redis instances
        shutdown_success = {}
        for port in self._deployer.ports:
            shutdown_success[port] = False
            if ClusterDeployer.is_port_in_use(port):
                try:
                    # Try to connect to Redis on this port
                    r = redis.Redis(host='localhost', port=port)
                    # Check if it's responsive
                    if r.ping():
                        # Send shutdown command with SAVE option to ensure data is saved
                        r.shutdown(save=True)
                        print(f"Gracefully shut down Redis server on port {port} with data saved")
                        shutdown_success[port] = True
                except Exception as e:
                    print(f"Could not gracefully shut down Redis on port {port}: {str(e)}")

        # Give some time for Redis to shut down
        time.sleep(1)

        # For any instances that didn't shut down gracefully, try terminating processes
        # First, terminate processes we have references to
        if self._deployer.processes:
            for proc in self._deployer.processes:
                try:
                    proc.terminate()
                    proc.wait(1)
                except Exception as e:
                    print(f"Error terminating process: {e}")

        # Then check if any ports are still in use and try to kill those processes
        for port in self._deployer.ports:
            if not shutdown_success[port] and ClusterDeployer.is_port_in_use(port):
                try:
                    # Kill processes using this port
                    killed_pids = ClusterDeployer.kill_processes_by_port(port, force=False)
                    for pid in killed_pids:
                        print(f"Stopped Redis server on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error stopping Redis on port {port}: {e}")

        # Clear the processes list but keep the ports for restart
        self._deployer.processes = []

        # Verify that the cluster is actually stopped
        time.sleep(0.5)  # Give some time for processes to terminate

        # Check if any ports are still in use
        ports_still_in_use = any(ClusterDeployer.is_port_in_use(port) for port in self._deployer.ports)

        if ports_still_in_use:
            # Some ports are still in use, try one more time with more force
            for port in self._deployer.ports:
                if ClusterDeployer.is_port_in_use(port):
                    try:
                        # Kill processes using this port with SIGKILL
                        killed_pids = ClusterDeployer.kill_processes_by_port(port, force=True)
                        for pid in killed_pids:
                            print(f"Forcefully stopped Redis server on port {port} (PID: {pid})")
                    except Exception as e:
                        print(f"Error forcefully stopping Redis on port {port}: {e}")

            # Check again after forceful termination
            time.sleep(0.5)
            ports_still_in_use = any(ClusterDeployer.is_port_in_use(port) for port in self._deployer.ports)

            if ports_still_in_use:
                print("Warning: Some Redis processes could not be stopped.")

        # Update configuration to indicate cluster is stopped but can be restarted
        config.set('cluster', 'running', False)
        config.save_config()

        if any(shutdown_success.values()):
            return "Cluster gracefully stopped with data preserved."
        else:
            return "Cluster stopped but data preserved."

    def _start(self) -> str:
        """Start the cluster without losing data."""
        cluster_config = config.get_section('cluster')
        if not cluster_config.get('active'):
            return "No active cluster. Use '/cluster deploy' to create one."

        if not self._deployer:
            # Recreate deployer from configuration
            self._deployer = ClusterDeployer()
            self._deployer.ports = cluster_config['ports']

        # Start the Redis nodes
        self._deployer.start_nodes()

        # Wait a moment for the nodes to start up
        time.sleep(1)

        # Verify that the cluster is actually running
        cluster_running = False

        # First check if the ports are in use
        ports_in_use = all(ClusterDeployer.is_port_in_use(port) for port in self._deployer.ports)

        if not ports_in_use:
            return "Failed to start the cluster. Some ports are not in use."

        # If ports are in use, try to connect to verify Redis is running
        try:
            # Try to connect to the first node
            node = redis.Redis(port=self._deployer.ports[0])
            # Try a simple ping to see if it's responsive
            node.ping()
            cluster_running = True
        except Exception as e:
            return f"Error starting cluster: {str(e)}"

        if not cluster_running:
            return "Failed to start the cluster. Check the logs for errors."

        # Update configuration to indicate cluster is running
        config.set('cluster', 'running', True)
        config.save_config()

        # Check cluster status
        try:
            status = self._deployer.check_cluster()
            print(f"Cluster status after restart: {status}")
        except Exception as e:
            print(f"Warning: Cluster started but could not get detailed status: {str(e)}")
            print("The cluster is running, but you may need to use '/resp' mode and run 'cluster info' directly for detailed information.")

        return "Cluster started with data preserved."

    def save_state_on_exit(self):
        """Ensure the configuration is saved to persistent storage on exit."""
        config.save_config()
