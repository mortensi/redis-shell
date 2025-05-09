from typing import Optional, Dict, Any
from .cluster import ClusterDeployer
from ...state import StateManager

class ClusterCommands:
    def __init__(self):
        self._deployer = None
        self._state = StateManager()

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
        elif cmd == "stop":
            return self._stop()
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
        
        status = self._deployer.check_cluster()
        state['status'] = status
        self._state.set_extension_state('cluster', state)
        return status

    def _stop(self) -> str:
        """Stop the cluster."""
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
        return "Cluster stopped and cleaned up."
