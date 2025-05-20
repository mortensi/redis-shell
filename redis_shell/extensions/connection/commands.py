import redis
from typing import Optional, Dict, Any, List
import argparse
import socket
from redis_shell.state_manager import StateManager
from redis_shell.connection_manager import ConnectionManager
import logging

logger = logging.getLogger(__name__)

class ConnectionCommands:
    def __init__(self):
        self._state = StateManager()
        self._connection_manager = ConnectionManager()
        self._connections = self._load_connections()
        self._current_connection_id = self._get_current_connection_id()

        # Initialize the connection manager with the loaded connections
        self._connection_manager.set_connections(self._connections, self._current_connection_id)

    def _load_connections(self) -> Dict[str, Dict[str, Any]]:
        """Load connections from state."""
        state = self._state.get_extension_state('connection')
        return state.get('connections', {})

    def _save_connections(self):
        """Save connections to state."""
        # Get the current state from the connection manager
        #self._connections = self._connection_manager.get_connections()
        #self._current_connection_id = self._connection_manager.get_current_connection_id()

        # Save to state
        state = self._state.get_extension_state('connection')
        state['connections'] = self._connections
        state['current_connection_id'] = self._current_connection_id
        self._state.set_extension_state('connection', state)

        # Force the state to be saved to disk immediately
        self._state.save_to_disk()

    def _get_current_connection_id(self) -> Optional[str]:
        """Get the current connection ID."""
        state = self._state.get_extension_state('connection')
        return state.get('current_connection_id')

    def handle_command(self, cmd: str, args: list) -> Optional[str]:
        """Handle connection commands."""
        if cmd == "create":
            return self._create(args)
        elif cmd == "destroy":
            return self._destroy(args)
        elif cmd == "list":
            return self._list()
        elif cmd == "use":
            return self._use(args)
        return None

    def _create(self, args: list) -> str:
        """Create a new Redis connection."""
        parser = argparse.ArgumentParser(description='Create a new Redis connection')
        parser.add_argument('--host', default='127.0.0.1', help='Redis host')
        parser.add_argument('--port', type=int, default=6379, help='Redis port')
        parser.add_argument('--db', type=int, default=0, help='Redis database number')
        parser.add_argument('--username', default='default', help='Redis username')
        parser.add_argument('--password', default='', help='Redis password')
        parser.add_argument('--ssl', action='store_true', help='Enable SSL/TLS connection')
        parser.add_argument('--ssl-ca-certs', help='Path to CA certificate file')
        parser.add_argument('--ssl-ca-path', help='Path to CA certificates directory')
        parser.add_argument('--ssl-keyfile', help='Path to private key file')
        parser.add_argument('--ssl-certfile', help='Path to certificate file')
        parser.add_argument('--ssl-cert-reqs', default='required',
                           choices=['none', 'optional', 'required'],
                           help='Certificate requirements (none, optional, required)')

        try:
            # Parse arguments
            parsed_args = parser.parse_args(args)

            # Generate connection ID - find the first available ID
            existing_ids = set(int(id) for id in self._connections.keys() if id.isdigit())
            connection_id = 1
            while connection_id in existing_ids:
                connection_id += 1
            connection_id = str(connection_id)

            # Create connection info
            connection_info = {
                'host': parsed_args.host,
                'port': parsed_args.port,
                'db': parsed_args.db,
                'username': parsed_args.username,
                'password': parsed_args.password,
                'ssl': parsed_args.ssl,
                'ssl_ca_certs': parsed_args.ssl_ca_certs,
                'ssl_ca_path': parsed_args.ssl_ca_path,
                'ssl_keyfile': parsed_args.ssl_keyfile,
                'ssl_certfile': parsed_args.ssl_certfile,
                'ssl_cert_reqs': parsed_args.ssl_cert_reqs
            }

            # Test connection
            try:
                r = redis.Redis(
                    host=connection_info['host'],
                    port=connection_info['port'],
                    db=connection_info['db'],
                    username=connection_info['username'],
                    password=connection_info['password'],
                    ssl=connection_info['ssl'],
                    ssl_ca_certs=connection_info['ssl_ca_certs'],
                    ssl_ca_path=connection_info['ssl_ca_path'],
                    ssl_keyfile=connection_info['ssl_keyfile'],
                    ssl_certfile=connection_info['ssl_certfile'],
                    ssl_cert_reqs=connection_info['ssl_cert_reqs']
                )
                r.ping()
            except redis.RedisError as e:
                return f"Error connecting to Redis: {str(e)}"

            # Add connection to the connection manager
            self._connection_manager.add_connection(connection_id, connection_info)

            # Save connections to state
            self._save_connections()

            # If this is the first connection, it will be set as current by the connection manager
            # Return connection info to CLI for updating the prompt
            if len(self._connections) == 1:
                return f"Connection created with ID: {connection_id}\nUse '/connection use {connection_id}' to switch to this connection."

            return f"Connection created with ID: {connection_id}"
        except Exception as e:
            return f"Error creating connection: {str(e)}"

    def _destroy(self, args: list) -> str:
        """Remove a Redis connection."""
        if not args:
            return "Error: Connection ID required."

        connection_id = args[0]

        if connection_id not in self._connections:
            return f"Error: Connection with ID {connection_id} not found."

        # Remove connection from the connection manager
        self._connection_manager.remove_connection(connection_id)

        # Save connections to state
        self._save_connections()

        return f"Connection {connection_id} removed."

    def _list(self) -> str:
        """List all available Redis connections."""
        if not self._connections:
            return "No connections available. Use '/connection create' to create one."

        result = "Available Redis connections:\n"
        result += "-" * 100 + "\n"
        result += f"{'ID':<5} {'Host':<15} {'Port':<6} {'DB':<4} {'Username':<10} {'SSL':<5} {'Current':<8}\n"
        result += "-" * 100 + "\n"

        for conn_id, conn_info in self._connections.items():
            current = "✓" if conn_id == self._current_connection_id else ""
            ssl_enabled = "Yes" if conn_info.get('ssl', False) else "No"
            result += f"{conn_id:<5} {conn_info['host']:<15} {conn_info['port']:<6} {conn_info['db']:<4} {conn_info.get('username', 'default'):<10} {ssl_enabled:<5} {current:<8}\n"

        return result

    def _use(self, args: list) -> str:
        """Switch to a specific Redis connection."""
        if not args:
            return "Error: Connection ID required."

        connection_id = args[0]

        if connection_id not in self._connections:
            return f"Error: Connection with ID {connection_id} not found."

        # Set current connection in the connection manager
        self._connection_manager.set_current_connection_id(connection_id)

        # Save connections to state
        self._save_connections()

        # Get connection info from the connection manager
        conn_info = self._connection_manager.get_connection_info(connection_id)

        # Return connection info to CLI for updating the connection
        # Format: SWITCH_CONNECTION:host:port:db:username:password:ssl:ssl_ca_certs:ssl_ca_path:ssl_keyfile:ssl_certfile:ssl_cert_reqs
        return (f"SWITCH_CONNECTION:{conn_info['host']}:{conn_info['port']}:{conn_info['db']}:"
                f"{conn_info.get('username', 'default')}:{conn_info.get('password', '')}:"
                f"{str(conn_info.get('ssl', False)).lower()}:{conn_info.get('ssl_ca_certs', '')}:"
                f"{conn_info.get('ssl_ca_path', '')}:{conn_info.get('ssl_keyfile', '')}:"
                f"{conn_info.get('ssl_certfile', '')}:{conn_info.get('ssl_cert_reqs', 'required')}")

    def get_current_connection(self) -> Optional[Dict[str, Any]]:
        """Get the current connection info."""
        if not self._current_connection_id:
            return None

        return self._connections.get(self._current_connection_id)

    def get_hosts(self, incomplete="") -> List[str]:
        """Return host completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of host suggestions that match the incomplete text
        """
        # Common Redis hosts
        hosts = [
            "localhost",
            "127.0.0.1",
            "redis-server",
            "redis.local"
        ]

        # Add hosts from existing connections
        for conn in self._connections.values():
            if conn['host'] not in hosts:
                hosts.append(conn['host'])

        # Try to resolve the local hostname
        try:
            local_hostname = socket.gethostname()
            if local_hostname not in hosts:
                hosts.append(local_hostname)
        except Exception:
            pass

        # Filter hosts based on the incomplete text
        return [h for h in hosts if incomplete == "" or h.startswith(incomplete)]

    def get_ports(self, incomplete="") -> List[str]:
        """Return port completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of port suggestions that match the incomplete text
        """
        # Common Redis ports
        ports = [
            "6379",  # Default Redis port
            "6380",
            "6381",
            "6382",
            "7379"   # Alternative Redis port
        ]

        # Add ports from existing connections
        for conn in self._connections.values():
            port_str = str(conn['port'])
            if port_str not in ports:
                ports.append(port_str)

        # Filter ports based on the incomplete text
        return [p for p in ports if incomplete == "" or p.startswith(incomplete)]

    def get_connection_ids(self, incomplete="") -> List[str]:
        """Return connection ID completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of connection IDs that match the incomplete text
        """
        # Get all connection IDs
        conn_ids = list(self._connections.keys())

        # Filter IDs based on the incomplete text
        return [cid for cid in conn_ids if incomplete == "" or cid.startswith(incomplete)]

    def get_cert_reqs(self, incomplete="") -> List[str]:
        """Return SSL certificate requirements completions.

        Args:
            incomplete: The partial text to match against

        Returns:
            list: A list of certificate requirements that match the incomplete text
        """
        # SSL certificate requirements options
        cert_reqs = [
            "none",
            "optional",
            "required"
        ]

        # Filter options based on the incomplete text
        return [req for req in cert_reqs if incomplete == "" or req.startswith(incomplete)]
