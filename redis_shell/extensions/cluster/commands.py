from typing import Optional, Dict, Any
import redis
import time
import os
from .cluster import ClusterDeployer
from ...state import StateManager

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

            print("Checking cluster status...")
            status = deployer.check_cluster()

            # Save cluster state
            self._state.set_extension_state('cluster', {
                'active': True,
                'running': True,
                'ports': deployer.ports,
                'status': status
            })

            return status
        except Exception as e:
            if self._deployer:
                self._deployer.cleanup()
            self._deployer = None
            self._state.clear_extension_state('cluster')
            return f"Error deploying cluster: {str(e)}"

    def _info(self) -> str:
        """Get cluster information."""
        state = self._state.get_extension_state('cluster')
        if not state.get('active'):
            return "No active cluster. Use '/cluster deploy' to create one."

        if not self._deployer:
            # Recreate deployer from state
            self._deployer = ClusterDeployer()
            self._deployer.ports = state['ports']

        # Check if the cluster is actually running by checking ports and connectivity
        cluster_running = False

        # First check if the ports are in use
        ports_in_use = all(ClusterDeployer.is_port_in_use(port) for port in self._deployer.ports)

        # If ports are in use, try to connect to verify Redis is running
        if ports_in_use:
            try:
                # Try to connect to the first node
                node = redis.Redis(port=self._deployer.ports[0])
                # Try a simple ping to see if it's responsive
                node.ping()

                # Verify this is our cluster by checking for the config file
                # This ensures we're not connecting to some other Redis instance on these ports
                cluster_is_ours = any(os.path.exists(f"redis-{port}.conf") for port in self._deployer.ports)

                if cluster_is_ours:
                    cluster_running = True
                else:
                    # There's a Redis instance running on these ports, but it's not our cluster
                    return "Found Redis instances on the expected ports, but they don't appear to be from the cluster created by '/cluster deploy'."

            except Exception:
                # If we can't connect, the cluster is not running properly
                cluster_running = False
        else:
            # If ports are not in use, cluster is definitely not running
            cluster_running = False

        # Update the state based on our check
        state['running'] = cluster_running
        self._state.set_extension_state('cluster', state)

        # If the cluster is not running, return a message
        if not cluster_running:
            return "Cluster is currently stopped. Use '/cluster start' to restart it."

        # If the cluster is running, get its status
        try:
            status = self._deployer.check_cluster()
            state['status'] = status
            self._state.set_extension_state('cluster', state)
            return status
        except Exception as e:
            # This is unexpected - we could ping but not get cluster info
            # Don't change the running state, just report the error
            print(f"Warning: Error getting detailed cluster info: {str(e)}")
            return "Cluster is running, but could not get detailed information. Try using '/resp' mode and running 'cluster info' directly."

    def _remove(self) -> str:
        """Remove the cluster and clean up."""
        state = self._state.get_extension_state('cluster')
        if not state.get('active'):
            return "No active cluster."

        if not self._deployer:
            # Recreate deployer from state
            self._deployer = ClusterDeployer()
            self._deployer.ports = state['ports']

        self._deployer.cleanup()
        self._deployer = None
        self._state.clear_extension_state('cluster')
        return "Cluster removed and cleaned up."

    def _stop(self) -> str:
        """Stop the cluster without cleaning up data."""
        state = self._state.get_extension_state('cluster')
        if not state.get('active'):
            return "No active cluster."

        if not self._deployer:
            # Recreate deployer from state
            self._deployer = ClusterDeployer()
            self._deployer.ports = state['ports']

        # Actually stop the Redis processes
        if self._deployer.processes:
            for proc in self._deployer.processes:
                try:
                    proc.terminate()
                    proc.wait(1)
                except Exception as e:
                    print(f"Error stopping process: {e}")

        # If we don't have process references (e.g., after a restart),
        # try to find and kill Redis processes on these ports
        else:
            for port in self._deployer.ports:
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

        # Update state to indicate cluster is stopped but can be restarted
        state['running'] = False
        self._state.set_extension_state('cluster', state)

        return "Cluster stopped but data preserved."

    def _start(self) -> str:
        """Start the cluster without losing data."""
        state = self._state.get_extension_state('cluster')
        if not state.get('active'):
            return "No active cluster. Use '/cluster deploy' to create one."

        if not self._deployer:
            # Recreate deployer from state
            self._deployer = ClusterDeployer()
            self._deployer.ports = state['ports']

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

        # Update state to indicate cluster is running
        state['running'] = True
        self._state.set_extension_state('cluster', state)

        # Check cluster status
        try:
            status = self._deployer.check_cluster()
            print(f"Cluster status after restart: {status}")
        except Exception as e:
            print(f"Warning: Cluster started but could not get detailed status: {str(e)}")
            print("The cluster is running, but you may need to use '/resp' mode and run 'cluster info' directly for detailed information.")

        return "Cluster started with data preserved."
