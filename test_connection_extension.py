#!/usr/bin/env python3
"""
Test script for the connection extension in redis-shell.
This script tests the basic functionality of the connection extension.
"""

import os
import unittest
from unittest.mock import patch
from redis_shell.extensions.connection.commands import ConnectionCommands

class TestConnectionExtension(unittest.TestCase):
    def setUp(self):
        # Create a temporary state file for testing
        self.temp_state_file = "/tmp/test_redis_shell_state"

        # Create a clean state file
        if os.path.exists(self.temp_state_file):
            os.remove(self.temp_state_file)

        # Create a mock state manager that uses an in-memory state
        class MockStateManager:
            def __init__(self):
                self._state = {}

            def get_extension_state(self, extension):
                return self._state.get(extension, {})

            def set_extension_state(self, extension, state):
                self._state[extension] = state

            def clear_extension_state(self, extension):
                if extension in self._state:
                    del self._state[extension]

        # Mock StateManager
        patcher = patch('redis_shell.extensions.connection.commands.StateManager')
        self.mock_state_manager = patcher.start()
        self.mock_state_manager.return_value = MockStateManager()
        self.addCleanup(patcher.stop)

        # Mock redis.Redis to avoid actual connections
        patcher2 = patch('redis_shell.extensions.connection.commands.redis.Redis')
        self.mock_redis = patcher2.start()
        self.mock_redis.return_value.ping.return_value = True
        self.addCleanup(patcher2.stop)

        # Create connection commands instance
        self.commands = ConnectionCommands()

    def tearDown(self):
        # Clean up the temporary state file
        if os.path.exists(self.temp_state_file):
            os.remove(self.temp_state_file)

    def test_create_connection(self):
        """Test creating a new connection."""
        result = self.commands._create(['--host', 'localhost', '--port', '6379'])
        self.assertIn("Connection created with ID: 1", result)

        # Check that the connection was saved
        self.assertEqual(len(self.commands._connections), 1)
        self.assertEqual(self.commands._connections['1']['host'], 'localhost')

    def test_connection_id_generation(self):
        """Test that connection IDs are generated correctly."""
        # Create first connection
        self.commands._create(['--host', 'localhost', '--port', '6379'])

        # Create second connection
        self.commands._create(['--host', 'localhost', '--port', '6380'])

        # Delete first connection
        self.commands._destroy(['1'])

        # Create another connection - should reuse ID 1
        result = self.commands._create(['--host', 'localhost', '--port', '6381'])
        self.assertIn("Connection created with ID: 1", result)

        # Verify connections
        self.assertEqual(len(self.commands._connections), 2)
        self.assertIn('1', self.commands._connections)
        self.assertIn('2', self.commands._connections)
        self.assertEqual(self.commands._connections['1']['port'], 6381)

    def test_list_connections(self):
        """Test listing connections."""
        # Create a connection first
        self.commands._create(['--host', 'localhost', '--port', '6379'])

        # List connections
        result = self.commands._list()
        self.assertIn("localhost", result)
        self.assertIn("6379", result)

    def test_use_connection(self):
        """Test switching to a connection."""
        # Create a connection first
        self.commands._create(['--host', 'localhost', '--port', '6379'])

        # Use the connection
        result = self.commands._use(['1'])
        self.assertTrue(result.startswith('SWITCH_CONNECTION:'))

        # Check that the current connection was updated
        self.assertEqual(self.commands._current_connection_id, '1')

    def test_destroy_connection(self):
        """Test removing a connection."""
        # Create a connection first
        self.commands._create(['--host', 'localhost', '--port', '6379'])

        # Destroy the connection
        result = self.commands._destroy(['1'])
        self.assertIn("Connection 1 removed", result)

        # Check that the connection was removed
        self.assertEqual(len(self.commands._connections), 0)

if __name__ == '__main__':
    unittest.main()
