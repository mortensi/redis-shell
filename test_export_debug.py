#!/usr/bin/env python3
"""
Test script to debug export issues with real Redis connection.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager
from redis_shell.state_manager import StateManager


def test_export_with_debug():
    """Test export with debug output."""
    print("=== Testing Export with Debug ===\n")
    
    # Create data commands instance (simulating what Redis Shell does)
    data_commands = DataCommands()
    
    # Set up connection manager (you'll need to adjust these for your Redis instance)
    connection_manager = ConnectionManager()
    
    # Add your Redis connection details here - using localhost for testing
    connection_manager.add_connection('test', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    connection_manager.set_current_connection_id('test')
    
    data_commands._connection_manager = connection_manager
    
    print("1. Initial state:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    
    print("\n2. Attempting export...")
    try:
        result = data_commands._export(['--folder', '/tmp'])
        print(f"Export result: {result}")
    except Exception as e:
        print(f"Export error: {e}")
    
    print("\n3. State after export attempt:")
    print(f"   _export_thread: {data_commands._export_thread}")
    if data_commands._export_thread:
        print(f"   _export_thread.is_alive(): {data_commands._export_thread.is_alive()}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    
    print("\n4. Status output:")
    status = data_commands._status()
    print(status)
    
    print("\n5. Trying reset...")
    reset_result = data_commands._export(['--reset'])
    print(f"Reset result: {reset_result}")
    
    print("\n6. Trying force reset...")
    force_reset_result = data_commands._export(['--force-reset'])
    print(f"Force reset result: {force_reset_result}")
    
    print("\n7. Final state:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    
    print("\n8. Trying export again after reset...")
    try:
        result2 = data_commands._export(['--folder', '/tmp'])
        print(f"Second export result: {result2}")
    except Exception as e:
        print(f"Second export error: {e}")


if __name__ == "__main__":
    test_export_with_debug()
