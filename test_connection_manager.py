#!/usr/bin/env python3
"""
Test script for the connection manager in redis-shell.
This script tests the basic functionality of the connection manager.
"""

import unittest
from unittest.mock import patch, MagicMock
from redis_shell.connection_manager import ConnectionManager

class TestConnectionManager(unittest.TestCase):
    def setUp(self):
        # Create a fresh connection manager for each test
        # Since it's a singleton, we need to reset its state
        ConnectionManager._instance = None
        self.manager = ConnectionManager()
    
    def test_singleton(self):
        """Test that ConnectionManager is a singleton."""
        manager1 = ConnectionManager()
        manager2 = ConnectionManager()
        self.assertIs(manager1, manager2)
    
    def test_add_connection(self):
        """Test adding a connection."""
        # Add a connection
        connection_info = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        }
        result = self.manager.add_connection('1', connection_info)
        self.assertTrue(result)
        
        # Verify the connection was added
        connections = self.manager.get_connections()
        self.assertEqual(len(connections), 1)
        self.assertIn('1', connections)
        self.assertEqual(connections['1'], connection_info)
        
        # Verify it's set as the current connection
        self.assertEqual(self.manager.get_current_connection_id(), '1')
    
    def test_add_duplicate_connection(self):
        """Test adding a duplicate connection."""
        # Add a connection
        connection_info = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        }
        self.manager.add_connection('1', connection_info)
        
        # Try to add a duplicate
        result = self.manager.add_connection('1', connection_info)
        self.assertFalse(result)
    
    def test_remove_connection(self):
        """Test removing a connection."""
        # Add connections
        self.manager.add_connection('1', {'host': 'localhost', 'port': 6379})
        self.manager.add_connection('2', {'host': 'localhost', 'port': 6380})
        
        # Remove a connection
        result = self.manager.remove_connection('1')
        self.assertTrue(result)
        
        # Verify the connection was removed
        connections = self.manager.get_connections()
        self.assertEqual(len(connections), 1)
        self.assertNotIn('1', connections)
        self.assertIn('2', connections)
        
        # Verify the current connection was updated
        self.assertEqual(self.manager.get_current_connection_id(), '2')
    
    def test_remove_nonexistent_connection(self):
        """Test removing a nonexistent connection."""
        result = self.manager.remove_connection('999')
        self.assertFalse(result)
    
    def test_get_connection_info(self):
        """Test getting connection info."""
        # Add a connection
        connection_info = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        }
        self.manager.add_connection('1', connection_info)
        
        # Get connection info
        info = self.manager.get_connection_info('1')
        self.assertEqual(info, connection_info)
        
        # Get current connection info
        info = self.manager.get_connection_info()
        self.assertEqual(info, connection_info)
        
        # Get nonexistent connection info
        info = self.manager.get_connection_info('999')
        self.assertIsNone(info)
    
    def test_set_current_connection_id(self):
        """Test setting the current connection ID."""
        # Add connections
        self.manager.add_connection('1', {'host': 'localhost', 'port': 6379})
        self.manager.add_connection('2', {'host': 'localhost', 'port': 6380})
        
        # Set current connection
        result = self.manager.set_current_connection_id('2')
        self.assertTrue(result)
        self.assertEqual(self.manager.get_current_connection_id(), '2')
        
        # Try to set a nonexistent connection
        result = self.manager.set_current_connection_id('999')
        self.assertFalse(result)
        self.assertEqual(self.manager.get_current_connection_id(), '2')
    
    @patch('redis.Redis')
    def test_get_redis_client(self, mock_redis):
        """Test getting a Redis client."""
        # Mock Redis client
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        # Add a connection
        self.manager.add_connection('1', {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        })
        
        # Get Redis client
        client = self.manager.get_redis_client('1')
        self.assertIsNotNone(client)
        
        # Get current Redis client
        client = self.manager.get_redis_client()
        self.assertIsNotNone(client)
        
        # Get nonexistent Redis client
        client = self.manager.get_redis_client('999')
        self.assertIsNone(client)

if __name__ == '__main__':
    unittest.main()
