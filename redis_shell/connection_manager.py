"""
Connection Manager for Redis Shell.

This module provides a singleton class for managing Redis connections across all extensions.
"""

import redis
from redis.cluster import RedisCluster
from typing import Dict, Any, Optional, List, Tuple, Union
import threading
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Singleton class for managing Redis connections across all extensions.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConnectionManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._connections: Dict[str, Dict[str, Any]] = {}
        self._current_connection_id: Optional[str] = None
        self._redis_clients: Dict[str, Union[redis.Redis, RedisCluster]] = {}
        self._initialized = True

    def set_connections(self, connections: Dict[str, Dict[str, Any]], current_id: Optional[str] = None):
        """Set the connections dictionary and optionally the current connection ID."""
        self._connections = connections
        if current_id is not None:
            self._current_connection_id = current_id

        # Clear the Redis clients cache to force recreation
        self._redis_clients = {}

    def get_connections(self) -> Dict[str, Dict[str, Any]]:
        """Get all connections."""
        return self._connections

    def get_connection_info(self, connection_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get connection info for a specific connection ID or the current connection."""
        if connection_id is None:
            connection_id = self._current_connection_id

        if connection_id is None or connection_id not in self._connections:
            return None

        return self._connections[connection_id]

    def get_current_connection_id(self) -> Optional[str]:
        """Get the current connection ID."""
        return self._current_connection_id

    def set_current_connection_id(self, connection_id: str):
        """Set the current connection ID."""
        if connection_id in self._connections:
            self._current_connection_id = connection_id
            # Clear the Redis clients cache to force recreation
            self._redis_clients = {}
            return True
        return False

    def add_connection(self, connection_id: str, connection_info: Dict[str, Any]) -> bool:
        """Add a new connection."""
        if connection_id in self._connections:
            return False

        self._connections[connection_id] = connection_info

        # If this is the first connection, set it as current
        if len(self._connections) == 1:
            self._current_connection_id = connection_id

        return True

    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection."""
        if connection_id not in self._connections:
            logger.debug("Connection not found in remove_connection")
            return False

        # Remove the connection
        del self._connections[connection_id]

        # If current connection was removed, set to None or the first available
        if self._current_connection_id == connection_id:
            if self._connections:
                self._current_connection_id = next(iter(self._connections))
            else:
                self._current_connection_id = None

        # Remove from Redis clients cache
        if connection_id in self._redis_clients:
            del self._redis_clients[connection_id]

        return True

    def get_redis_client(self, connection_id: Optional[str] = None) -> Optional[Union[redis.Redis, RedisCluster]]:
        """
        Get a Redis client for a specific connection ID or the current connection.

        This method will create a new client if one doesn't exist, or return a cached client.
        It will also detect if the connection is to a Redis cluster and create the appropriate client.
        """
        if connection_id is None:
            connection_id = self._current_connection_id

        if connection_id is None or connection_id not in self._connections:
            return None

        # Return cached client if it exists
        if connection_id in self._redis_clients:
            return self._redis_clients[connection_id]

        # Get connection info
        conn_info = self._connections[connection_id]
        host = conn_info.get('host', 'localhost')
        port = conn_info.get('port', 6379)
        db = conn_info.get('db', 0)
        password = conn_info.get('password')

        # Create a standard Redis client to check if it's a cluster
        try:
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
                logger.debug(f"Checking if Redis instance at {host}:{port} is part of a cluster...")
                slots_info = standard_client.execute_command('CLUSTER SLOTS')

                if slots_info and isinstance(slots_info, list) and len(slots_info) > 0:
                    is_cluster = True
                    logger.info(f"Redis instance at {host}:{port} is part of a cluster. Will use Cluster API.")

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
                                    logger.debug(f"Found cluster node: {node_addr} (master)")
            except Exception as e:
                logger.debug(f"Not a cluster or error checking cluster status: {str(e)}")
                is_cluster = False

            # Create the appropriate Redis client based on whether it's a cluster
            if is_cluster and cluster_nodes:
                try:
                    # Format startup nodes for RedisCluster
                    startup_nodes = []
                    for node in cluster_nodes:
                        node_host, node_port = node.split(':')
                        startup_nodes.append({"host": node_host, "port": int(node_port)})

                    # Create a RedisCluster client
                    logger.debug(f"Creating RedisCluster client with {len(startup_nodes)} nodes")
                    # For Redis Cluster, we need to use the host:port format for the first node
                    # and let the client discover the rest of the cluster
                    first_node = startup_nodes[0]
                    client = RedisCluster(
                        host=first_node['host'],
                        port=first_node['port'],
                        password=password,
                        decode_responses=False
                    )
                    logger.debug("Successfully created RedisCluster client")

                    # Store the client in the cache
                    self._redis_clients[connection_id] = client

                    # Store the cluster info in the connection info
                    conn_info['is_cluster'] = True
                    conn_info['cluster_nodes'] = cluster_nodes
                    self._connections[connection_id] = conn_info

                    return client
                except Exception as e:
                    logger.error(f"Error creating RedisCluster client: {str(e)}")
                    # If it's a cluster, we must use a cluster client
                    # Don't fall back to a standard client
                    raise

            # If not a cluster or cluster client creation failed, use standard Redis client
            logger.debug(f"Using standard Redis client for {host}:{port}")
            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False
            )

            # Store the client in the cache
            self._redis_clients[connection_id] = client

            # Update the connection info
            conn_info['is_cluster'] = False
            self._connections[connection_id] = conn_info

            return client

        except Exception as e:
            logger.error(f"Error creating Redis client: {str(e)}")
            # If there's an error creating the client, return None
            return None

    def get_connection_parameters(self, connection_id: Optional[str] = None) -> Tuple[str, int, int, Optional[str]]:
        """
        Get connection parameters (host, port, db, password) for a specific connection ID or the current connection.

        Returns:
            Tuple[str, int, int, Optional[str]]: (host, port, db, password)
        """
        if connection_id is None:
            connection_id = self._current_connection_id

        if connection_id is None or connection_id not in self._connections:
            return ('localhost', 6379, 0, None)

        conn_info = self._connections[connection_id]
        host = conn_info.get('host', 'localhost')
        port = conn_info.get('port', 6379)
        db = conn_info.get('db', 0)
        password = conn_info.get('password')

        return (host, port, db, password)

    def is_cluster_connection(self, connection_id: Optional[str] = None) -> bool:
        """
        Check if a connection is to a Redis cluster.

        Args:
            connection_id: The connection ID to check. If None, the current connection is used.

        Returns:
            bool: True if the connection is to a Redis cluster, False otherwise.
        """
        if connection_id is None:
            connection_id = self._current_connection_id

        if connection_id is None or connection_id not in self._connections:
            return False

        conn_info = self._connections[connection_id]
        return conn_info.get('is_cluster', False)
