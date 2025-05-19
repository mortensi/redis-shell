"""
Pytest configuration for redis-shell tests.

This module contains fixtures and configuration for redis-shell tests.
"""

import pytest
import os
import json
import tempfile
import redis
import fakeredis
from typing import Dict, Any, Optional, List, Union, Callable
import sys

# Add the parent directory to the path so we can import redis_shell
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from redis_shell.config import Config
from redis_shell.state_manager import StateManager
from redis_shell.connection_manager import ConnectionManager
from redis_shell.extensions import ExtensionManager


@pytest.fixture
def mock_config():
    """Fixture for a mock configuration."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_file = f.name
        json.dump({
            "general": {
                "history_size": 10,
                "log_level": "debug",
                "log_file": None,
                "state_file": None
            },
            "redis": {
                "default_host": "localhost",
                "default_port": 6379,
                "default_db": 0,
                "default_password": None,
                "timeout": 1,
                "decode_responses": False,
                "ssl": False,
                "ssl_ca_certs": None
            },
            "extensions": {
                "enabled": ["data", "connection", "cluster", "sentinel"],
                "extension_dir": None
            },
            "ui": {
                "prompt_style": "green",
                "error_style": "red",
                "warning_style": "yellow",
                "success_style": "green",
                "info_style": "blue"
            }
        }, f)

    # Create a Config instance with the temporary file
    config = Config()
    config.config_file = config_file
    config._load_config()

    yield config

    # Clean up
    os.unlink(config_file)


@pytest.fixture
def mock_state():
    """Fixture for a mock state manager."""
    # Create a temporary state file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = f.name
        json.dump({
            "command_history": ["GET key1", "SET key2 value2", "PING"],
            "connections": {
                "1": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "password": None
                }
            },
            "current_connection_id": "1"
        }, f)

    # Create a StateManager instance with the temporary file
    state = StateManager()
    state._state_file = state_file
    state._load_state()

    yield state

    # Clean up
    os.unlink(state_file)


@pytest.fixture
def mock_redis():
    """Fixture for a mock Redis server."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server)

    # Add some test data
    client.set('key1', 'value1')
    client.set('key2', 'value2')
    client.hset('hash1', 'field1', 'value1')
    client.hset('hash1', 'field2', 'value2')
    client.lpush('list1', 'item1', 'item2', 'item3')
    client.sadd('set1', 'member1', 'member2', 'member3')
    client.zadd('zset1', {'member1': 1, 'member2': 2, 'member3': 3})

    yield client


@pytest.fixture
def mock_connection_manager(mock_redis):
    """Fixture for a mock connection manager."""
    # Create a ConnectionManager instance
    connection_manager = ConnectionManager()

    # Add a test connection
    connection_manager.add_connection('1', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })

    # Set the current connection
    connection_manager.set_current_connection_id('1')

    # Mock the get_redis_client method to return the mock Redis client
    connection_manager.get_redis_client = lambda: mock_redis

    yield connection_manager


@pytest.fixture
def mock_extension_manager(mock_connection_manager):
    """Fixture for a mock extension manager."""
    # Create an ExtensionManager instance
    extension_manager = ExtensionManager()

    # Mock the extensions
    extension_manager.extensions = {
        '/data': {
            'name': 'data',
            'definition': {
                'commands': [
                    {
                        'name': 'export',
                        'description': 'Export Redis data to a file',
                        'usage': '/data export [--pattern PATTERN] [--folder FOLDER]'
                    },
                    {
                        'name': 'import',
                        'description': 'Import Redis data from a file',
                        'usage': '/data import --file FILE'
                    }
                ]
            },
            'commands': None
        },
        '/connection': {
            'name': 'connection',
            'definition': {
                'commands': [
                    {
                        'name': 'create',
                        'description': 'Create a new connection',
                        'usage': '/connection create [--host HOST] [--port PORT] [--db DB] [--password PASSWORD]'
                    },
                    {
                        'name': 'list',
                        'description': 'List all connections',
                        'usage': '/connection list'
                    },
                    {
                        'name': 'use',
                        'description': 'Use a connection',
                        'usage': '/connection use CONNECTION_ID'
                    },
                    {
                        'name': 'destroy',
                        'description': 'Destroy a connection',
                        'usage': '/connection destroy CONNECTION_ID'
                    }
                ]
            },
            'commands': None
        }
    }

    yield extension_manager
