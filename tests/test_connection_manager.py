"""
Tests for the connection manager.

This module contains tests for the connection manager.
"""

import pytest
import redis
from redis_shell.connection_manager import ConnectionManager


def test_add_connection():
    """Test adding a connection."""
    manager = ConnectionManager()
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Check if the connection was added
    connections = manager.get_connections()
    assert '1' in connections
    assert connections['1']['host'] == 'localhost'
    assert connections['1']['port'] == 6379
    assert connections['1']['db'] == 0
    assert connections['1']['password'] is None


def test_get_connection():
    """Test getting a connection."""
    manager = ConnectionManager()
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Get the connection
    connection = manager.get_connection('1')
    assert connection is not None
    assert connection['host'] == 'localhost'
    assert connection['port'] == 6379
    assert connection['db'] == 0
    assert connection['password'] is None
    
    # Try to get a non-existent connection
    connection = manager.get_connection('2')
    assert connection is None


def test_remove_connection():
    """Test removing a connection."""
    manager = ConnectionManager()
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Remove the connection
    manager.remove_connection('1')
    
    # Check if the connection was removed
    connections = manager.get_connections()
    assert '1' not in connections


def test_set_current_connection_id():
    """Test setting the current connection ID."""
    manager = ConnectionManager()
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Set the current connection ID
    manager.set_current_connection_id('1')
    
    # Check if the current connection ID was set
    assert manager.get_current_connection_id() == '1'
    
    # Try to set a non-existent connection ID
    with pytest.raises(ValueError):
        manager.set_current_connection_id('2')


def test_get_connection_parameters():
    """Test getting connection parameters."""
    manager = ConnectionManager()
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Set the current connection ID
    manager.set_current_connection_id('1')
    
    # Get the connection parameters
    host, port, db, password = manager.get_connection_parameters()
    assert host == 'localhost'
    assert port == 6379
    assert db == 0
    assert password is None
    
    # Try to get connection parameters without a current connection
    manager._current_connection_id = None
    with pytest.raises(ValueError):
        manager.get_connection_parameters()


def test_get_redis_client(monkeypatch):
    """Test getting a Redis client."""
    manager = ConnectionManager()
    
    # Mock the Redis client
    class MockRedis:
        def __init__(self, host, port, db, password):
            self.host = host
            self.port = port
            self.db = db
            self.password = password
    
    # Patch the Redis class
    monkeypatch.setattr(redis, 'Redis', MockRedis)
    
    # Add a connection
    manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    
    # Set the current connection ID
    manager.set_current_connection_id('1')
    
    # Get the Redis client
    client = manager.get_redis_client()
    assert client is not None
    assert client.host == 'localhost'
    assert client.port == 6379
    assert client.db == 0
    assert client.password is None
    
    # Try to get a Redis client without a current connection
    manager._current_connection_id = None
    client = manager.get_redis_client()
    assert client is None
