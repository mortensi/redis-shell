from typing import Optional, Dict, Any
import redis
import time
from .sentinel import SentinelDeployer
from ...state import StateManager

class SentinelCommands:
    def __init__(self):
        self._deployer = None
        self._state = StateManager()
    
    def _get_deployer(self):
        if not self._deployer:
            self._deployer = SentinelDeployer()
        return self._deployer
    
    def handle_command(self, cmd: str, args: list) -> Optional[str]:
        """Handle sentinel commands."""
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
        """Deploy a new Redis Sentinel setup with master and replicas."""
        try:
            deployer = self._get_deployer()
            print("Starting Redis instances (1 master, 2 replicas)...")
            deployer.start_redis_instances()
            
            print("Starting Redis Sentinel...")
            deployer.start_sentinel()
            
            print("Checking Sentinel status...")
            status = deployer.check_sentinel()
            
            # Save sentinel state
            self._state.set_extension_state('sentinel', {
                'active': True,
                'running': True,
                'sentinel_port': deployer.sentinel_port,
                'redis_ports': deployer.redis_ports,
                'master_name': deployer.master_name,
                'status': status
            })
            
            return status
        except Exception as e:
            if self._deployer:
                self._deployer.cleanup()
            self._deployer = None
            self._state.clear_extension_state('sentinel')
            return f"Error deploying Sentinel: {str(e)}"
    
    def _info(self) -> str:
        """Get information about the Sentinel setup."""
        state = self._state.get_extension_state('sentinel')
        if not state.get('active'):
            return "No active Sentinel setup. Use '/sentinel deploy' to create one."
        
        if not self._deployer:
            # Recreate deployer from state
            self._deployer = SentinelDeployer()
            self._deployer.sentinel_port = state.get('sentinel_port', 5000)
            self._deployer.redis_ports = state.get('redis_ports', [40001, 40002, 40003])
            self._deployer.master_name = state.get('master_name', 'mymaster')
        
        # Check if the sentinel is actually running by checking ports and connectivity
        sentinel_running = False
        
        # First check if the sentinel port is in use
        sentinel_port_in_use = SentinelDeployer.is_port_in_use(self._deployer.sentinel_port)
        
        # Check if at least the master Redis port is in use
        master_port_in_use = SentinelDeployer.is_port_in_use(self._deployer.redis_ports[0])
        
        # If ports are in use, try to connect to verify Sentinel is running
        if sentinel_port_in_use and master_port_in_use:
            try:
                # Try to connect to the sentinel
                sentinel = redis.Redis(port=self._deployer.sentinel_port)
                # Try a simple ping to see if it's responsive
                sentinel.ping()
                sentinel_running = True
            except Exception:
                # If we can't connect, the sentinel is not running properly
                sentinel_running = False
        else:
            # If ports are not in use, sentinel is definitely not running
            sentinel_running = False
        
        # Update the state based on our check
        state['running'] = sentinel_running
        self._state.set_extension_state('sentinel', state)
        
        # If the sentinel is not running, return a message
        if not sentinel_running:
            return "Sentinel is currently stopped. Use '/sentinel start' to restart it."
        
        # If the sentinel is running, get its status
        try:
            status = self._deployer.check_sentinel()
            state['status'] = status
            self._state.set_extension_state('sentinel', state)
            return status
        except Exception as e:
            # This is unexpected - we could ping but not get sentinel info
            # Don't change the running state, just report the error
            print(f"Warning: Error getting detailed sentinel info: {str(e)}")
            return "Sentinel is running, but could not get detailed information. Try using '/resp' mode and running 'info' directly."
    
    def _remove(self) -> str:
        """Remove the Sentinel setup and clean up."""
        state = self._state.get_extension_state('sentinel')
        if not state.get('active'):
            return "No active Sentinel setup."
        
        if not self._deployer:
            # Recreate deployer from state
            self._deployer = SentinelDeployer()
            self._deployer.sentinel_port = state.get('sentinel_port', 5000)
            self._deployer.redis_ports = state.get('redis_ports', [40001, 40002, 40003])
            self._deployer.master_name = state.get('master_name', 'mymaster')
        
        self._deployer.cleanup()
        self._deployer = None
        self._state.clear_extension_state('sentinel')
        return "Sentinel setup removed and cleaned up."
    
    def _stop(self) -> str:
        """Stop the Sentinel setup without cleaning up data."""
        state = self._state.get_extension_state('sentinel')
        if not state.get('active'):
            return "No active Sentinel setup."
        
        if not self._deployer:
            # Recreate deployer from state
            self._deployer = SentinelDeployer()
            self._deployer.sentinel_port = state.get('sentinel_port', 5000)
            self._deployer.redis_ports = state.get('redis_ports', [40001, 40002, 40003])
            self._deployer.master_name = state.get('master_name', 'mymaster')
        
        # Actually stop the processes
        if self._deployer.processes:
            for proc in self._deployer.processes:
                try:
                    proc.terminate()
                    proc.wait(1)
                except Exception as e:
                    print(f"Error stopping process: {e}")
        
        # If we don't have process references (e.g., after a restart),
        # try to find and kill processes on our ports
        else:
            all_ports = [self._deployer.sentinel_port] + self._deployer.redis_ports
            for port in all_ports:
                try:
                    # Kill processes using this port
                    killed_pids = SentinelDeployer.kill_processes_by_port(port, force=False)
                    for pid in killed_pids:
                        print(f"Stopped process on port {port} (PID: {pid})")
                except Exception as e:
                    print(f"Error stopping process on port {port}: {e}")
        
        # Clear the processes list but keep the configuration for restart
        self._deployer.processes = []
        
        # Verify that everything is actually stopped
        time.sleep(0.5)  # Give some time for processes to terminate
        
        # Check if any ports are still in use
        all_ports = [self._deployer.sentinel_port] + self._deployer.redis_ports
        ports_still_in_use = any(SentinelDeployer.is_port_in_use(port) for port in all_ports)
        
        if ports_still_in_use:
            # Some ports are still in use, try one more time with more force
            for port in all_ports:
                if SentinelDeployer.is_port_in_use(port):
                    try:
                        # Kill processes using this port with SIGKILL
                        killed_pids = SentinelDeployer.kill_processes_by_port(port, force=True)
                        for pid in killed_pids:
                            print(f"Forcefully stopped process on port {port} (PID: {pid})")
                    except Exception as e:
                        print(f"Error forcefully stopping process on port {port}: {e}")
            
            # Check again after forceful termination
            time.sleep(0.5)
            ports_still_in_use = any(SentinelDeployer.is_port_in_use(port) for port in all_ports)
            
            if ports_still_in_use:
                print("Warning: Some processes could not be stopped.")
        
        # Update state to indicate sentinel is stopped but can be restarted
        state['running'] = False
        self._state.set_extension_state('sentinel', state)
        
        return "Sentinel setup stopped but data preserved."
    
    def _start(self) -> str:
        """Start the Sentinel setup without losing data."""
        state = self._state.get_extension_state('sentinel')
        if not state.get('active'):
            return "No active Sentinel setup. Use '/sentinel deploy' to create one."
        
        if not self._deployer:
            # Recreate deployer from state
            self._deployer = SentinelDeployer()
            self._deployer.sentinel_port = state.get('sentinel_port', 5000)
            self._deployer.redis_ports = state.get('redis_ports', [40001, 40002, 40003])
            self._deployer.master_name = state.get('master_name', 'mymaster')
        
        # Start the Redis instances
        self._deployer.start_redis_instances()
        
        # Start the Sentinel
        self._deployer.start_sentinel()
        
        # Wait a moment for everything to start up
        time.sleep(1)
        
        # Verify that the sentinel is actually running
        sentinel_running = False
        
        # First check if the ports are in use
        all_ports = [self._deployer.sentinel_port] + self._deployer.redis_ports
        ports_in_use = all(SentinelDeployer.is_port_in_use(port) for port in all_ports)
        
        if not ports_in_use:
            return "Failed to start the Sentinel setup. Some ports are not in use."
        
        # If ports are in use, try to connect to verify Sentinel is running
        try:
            # Try to connect to the sentinel
            sentinel = redis.Redis(port=self._deployer.sentinel_port)
            # Try a simple ping to see if it's responsive
            sentinel.ping()
            sentinel_running = True
        except Exception as e:
            return f"Error starting Sentinel: {str(e)}"
        
        if not sentinel_running:
            return "Failed to start the Sentinel setup. Check the logs for errors."
        
        # Update state to indicate sentinel is running
        state['running'] = True
        self._state.set_extension_state('sentinel', state)
        
        # Check sentinel status
        try:
            status = self._deployer.check_sentinel()
            print(f"Sentinel status after restart: {status}")
        except Exception as e:
            print(f"Warning: Sentinel started but could not get detailed status: {str(e)}")
            print("The Sentinel is running, but you may need to use '/resp' mode and run commands directly for detailed information.")
        
        return "Sentinel setup started with data preserved."
