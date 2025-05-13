"""
Redis utilities for redis-shell.

This module contains utilities for Redis operations, connection management, and Redis-related completions.
"""

import redis
from redis.cluster import RedisCluster
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
import logging

logger = logging.getLogger(__name__)

class RedisConnectionHelper:
    """Helper class for Redis connection operations."""
    
    @staticmethod
    def create_redis_client(
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = False,
        ssl: bool = False,
        ssl_ca_certs: Optional[str] = None
    ) -> redis.Redis:
        """
        Create a standard Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            decode_responses: Whether to decode responses
            ssl: Whether to use SSL
            ssl_ca_certs: Path to CA certificates file
            
        Returns:
            Redis client
        """
        connection_kwargs = {
            'host': host,
            'port': port,
            'db': db,
            'decode_responses': decode_responses
        }
        
        if password:
            connection_kwargs['password'] = password
            
        if ssl:
            connection_kwargs['ssl'] = True
            if ssl_ca_certs:
                connection_kwargs['ssl_ca_certs'] = ssl_ca_certs
                
        return redis.Redis(**connection_kwargs)
    
    @staticmethod
    def is_cluster(client: redis.Redis) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check if a Redis client is connected to a cluster.
        
        Args:
            client: Redis client
            
        Returns:
            Tuple containing:
                - is_cluster: Whether the client is connected to a cluster
                - nodes: List of cluster nodes
        """
        try:
            logger.debug(f"Checking if Redis instance is part of a cluster...")
            slots_info = client.execute_command('CLUSTER SLOTS')
            
            if slots_info and isinstance(slots_info, list) and len(slots_info) > 0:
                nodes = []
                
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
                            node = {"host": master_host, "port": master_port}
                            if node not in nodes:
                                nodes.append(node)
                                logger.debug(f"Found cluster node: {master_host}:{master_port} (master)")
                
                return True, nodes
            
            return False, []
        except Exception as e:
            logger.debug(f"Not a cluster or error checking cluster status: {str(e)}")
            return False, []
    
    @staticmethod
    def create_cluster_client(
        nodes: List[Dict[str, Any]],
        password: Optional[str] = None,
        decode_responses: bool = False,
        ssl: bool = False,
        ssl_ca_certs: Optional[str] = None
    ) -> RedisCluster:
        """
        Create a Redis cluster client.
        
        Args:
            nodes: List of cluster nodes
            password: Redis password
            decode_responses: Whether to decode responses
            ssl: Whether to use SSL
            ssl_ca_certs: Path to CA certificates file
            
        Returns:
            Redis cluster client
        """
        if not nodes:
            raise ValueError("No cluster nodes provided")
            
        # Use the first node as the startup node
        first_node = nodes[0]
        
        connection_kwargs = {
            'host': first_node['host'],
            'port': first_node['port'],
            'decode_responses': decode_responses
        }
        
        if password:
            connection_kwargs['password'] = password
            
        if ssl:
            connection_kwargs['ssl'] = True
            if ssl_ca_certs:
                connection_kwargs['ssl_ca_certs'] = ssl_ca_certs
                
        return RedisCluster(**connection_kwargs)
    
    @staticmethod
    def get_redis_info(client: Union[redis.Redis, RedisCluster]) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Args:
            client: Redis client
            
        Returns:
            Dictionary of Redis server information
        """
        try:
            info = client.info()
            return {
                'redis_version': info.get('redis_version', 'unknown'),
                'redis_mode': info.get('redis_mode', 'unknown'),
                'os': info.get('os', 'unknown'),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'connected_clients': info.get('connected_clients', 'unknown'),
                'uptime_in_days': info.get('uptime_in_days', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {str(e)}")
            return {'error': str(e)}
            
    @staticmethod
    def format_redis_value(value: Any) -> str:
        """
        Format a Redis value for display.
        
        Args:
            value: Redis value
            
        Returns:
            Formatted value string
        """
        if value is None:
            return "(nil)"
            
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                return f"(binary data, {len(value)} bytes)"
                
        if isinstance(value, (list, tuple)):
            return "\n".join([RedisConnectionHelper.format_redis_value(item) for item in value])
            
        if isinstance(value, dict):
            return "\n".join([f"{k}: {RedisConnectionHelper.format_redis_value(v)}" for k, v in value.items()])
            
        return str(value)
