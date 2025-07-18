#!/usr/bin/env python3
"""
Test script to simulate a stuck export scenario and test recovery.
"""

import sys
import os
import threading
import time
from unittest.mock import Mock, patch
sys.path.insert(0, os.path.abspath('.'))

from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager
from redis_shell.state_manager import StateManager


def test_stuck_export_scenario():
    """Test a scenario where export gets stuck and recovery methods."""
    print("=== Testing Stuck Export Scenario ===\n")
    
    # Create data commands instance
    data_commands = DataCommands()
    
    print("1. Simulating a stuck export state...")
    
    # Simulate a stuck thread (create a mock thread that appears alive but is actually stuck)
    mock_thread = Mock()
    mock_thread.is_alive.return_value = True
    mock_thread.daemon = True
    
    # Set the stuck state manually
    data_commands._export_thread = mock_thread
    data_commands._current_operation = "export"
    data_commands._export_status = "Export operation stuck..."
    
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _export_thread.is_alive(): {data_commands._export_thread.is_alive()}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    
    print("\n2. Trying to start new export (should be blocked)...")
    result = data_commands._export(['--folder', '/tmp'])
    print(f"Result: {result}")
    
    print("\n3. Checking status...")
    status = data_commands._status()
    print(f"Status:\n{status}")
    
    print("\n4. Trying normal reset...")
    reset_result = data_commands._export(['--reset'])
    print(f"Reset result: {reset_result}")
    
    print("\n5. State after normal reset:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    
    print("\n6. Trying export after normal reset...")
    result2 = data_commands._export(['--folder', '/tmp'])
    print(f"Result: {result2}")
    
    # If still blocked, simulate the really stuck scenario
    if "already running" in result2:
        print("\n7. Still blocked! Simulating really stuck thread...")
        
        # Create another stuck thread
        mock_thread2 = Mock()
        mock_thread2.is_alive.return_value = True
        mock_thread2.daemon = True
        
        data_commands._export_thread = mock_thread2
        data_commands._current_operation = "export"
        data_commands._export_status = "Really stuck export..."
        
        print("\n8. Trying force reset...")
        force_reset_result = data_commands._export(['--force-reset'])
        print(f"Force reset result: {force_reset_result}")
        
        print("\n9. State after force reset:")
        print(f"   _export_thread: {data_commands._export_thread}")
        print(f"   _current_operation: {data_commands._current_operation}")
        print(f"   _export_status: {data_commands._export_status}")
        
        print("\n10. Trying export after force reset...")
        result3 = data_commands._export(['--folder', '/tmp'])
        print(f"Result: {result3}")
    
    print("\n=== Test Complete ===")


def test_real_hanging_scenario():
    """Test with a real hanging thread scenario."""
    print("\n=== Testing Real Hanging Thread Scenario ===\n")
    
    data_commands = DataCommands()
    
    # Create a thread that will actually hang
    def hanging_function():
        print("Thread started and will hang...")
        time.sleep(1000)  # Simulate a hanging operation
    
    print("1. Creating a real hanging thread...")
    hanging_thread = threading.Thread(target=hanging_function)
    hanging_thread.daemon = True
    hanging_thread.start()
    
    # Set this as the export thread
    data_commands._export_thread = hanging_thread
    data_commands._current_operation = "export"
    data_commands._export_status = "Hanging export operation..."
    
    print(f"   Thread is alive: {hanging_thread.is_alive()}")
    print(f"   Thread is daemon: {hanging_thread.daemon}")
    
    print("\n2. Trying to start new export (should be blocked)...")
    result = data_commands._export(['--folder', '/tmp'])
    print(f"Result: {result}")
    
    print("\n3. Trying force reset to abandon hanging thread...")
    force_reset_result = data_commands._export(['--force-reset'])
    print(f"Force reset result: {force_reset_result}")
    
    print("\n4. State after force reset:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    
    print("\n5. Trying export after abandoning hanging thread...")
    # Mock the connection for this test
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
    
    result2 = data_commands._export(['--folder', '/tmp'])
    print(f"Result: {result2}")
    
    # Wait a bit for the new export to complete
    if data_commands._export_thread:
        data_commands._export_thread.join(timeout=5)
    
    print(f"\nHanging thread still alive: {hanging_thread.is_alive()}")
    print("Note: The hanging thread is abandoned but continues running as a daemon")
    
    print("\n=== Real Hanging Test Complete ===")


if __name__ == "__main__":
    test_stuck_export_scenario()
    test_real_hanging_scenario()
