#!/usr/bin/env python3
"""
Test the emergency reset functionality.
"""

import sys
import os
import threading
import time
from unittest.mock import Mock
sys.path.insert(0, os.path.abspath('.'))

from redis_shell.extensions.data.commands import DataCommands


def test_emergency_reset():
    """Test the emergency reset functionality."""
    print("=== Testing Emergency Reset ===\n")
    
    data_commands = DataCommands()
    
    print("1. Creating a really stuck state...")
    
    # Create multiple mock threads to simulate a really messed up state
    mock_thread1 = Mock()
    mock_thread1.is_alive.return_value = True
    mock_thread1.daemon = True
    
    # Set multiple problematic state variables
    data_commands._export_thread = mock_thread1
    data_commands._current_operation = "export"
    data_commands._export_status = "Really stuck export..."
    
    # Add some state to the state manager
    data_commands._state.set_extension_state('data', {
        'stuck_export': True,
        'problematic_state': 'yes'
    })
    
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    print(f"   Extension state: {data_commands._state.get_extension_state('data')}")
    
    print("\n2. Trying normal reset (should work but let's see)...")
    reset_result = data_commands._export(['--reset'])
    print(f"Reset result: {reset_result}")
    
    print(f"   State after reset: {data_commands._current_operation}")
    
    # Simulate it's still stuck somehow
    if data_commands._current_operation is None:
        print("   Normal reset worked, but let's simulate it didn't...")
        data_commands._export_thread = mock_thread1
        data_commands._current_operation = "export"
        data_commands._export_status = "Still stuck somehow..."
    
    print("\n3. Trying emergency reset...")
    emergency_result = data_commands._export(['--emergency-reset'])
    print(f"Emergency reset result: {emergency_result}")
    
    print("\n4. State after emergency reset:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    print(f"   _stop_event: {data_commands._stop_event}")
    print(f"   Extension state: {data_commands._state.get_extension_state('data')}")
    
    print("\n5. Trying export after emergency reset...")
    # Mock connection for test
    mock_connection_manager = Mock()
    mock_redis = Mock()
    mock_redis.keys.return_value = [b'test']
    mock_redis.type.return_value = 'string'
    mock_redis.get.return_value = b'value'
    mock_redis.dbsize.return_value = 1
    mock_redis.info.return_value = {'redis_version': '7.0.0', 'redis_mode': 'standalone', 'db0': {'keys': 1}}
    mock_redis.connection_pool.connection_kwargs = {'host': 'localhost', 'port': 6379, 'db': 0}
    
    mock_connection_manager.get_redis_client.return_value = mock_redis
    mock_connection_manager.get_connection_parameters.return_value = ('localhost', 6379, 0, None)
    mock_connection_manager.is_cluster_connection.return_value = False
    
    data_commands._connection_manager = mock_connection_manager
    
    result = data_commands._export(['--folder', '/tmp'])
    print(f"Export result: {result}")
    
    # Wait for completion
    if data_commands._export_thread:
        data_commands._export_thread.join(timeout=5)
    
    print("\n=== Emergency Reset Test Complete ===")


if __name__ == "__main__":
    test_emergency_reset()
