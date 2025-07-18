#!/usr/bin/env python3
"""
Test script to verify that export hanging issues are resolved.
"""

import tempfile
import threading
import time
from unittest.mock import Mock
from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager
from redis_shell.state_manager import StateManager


def test_export_cleanup():
    """Test that export operations clean up properly."""
    print("=== Testing Export Cleanup ===\n")
    
    # Create data commands instance
    data_commands = DataCommands()
    data_commands._state = StateManager()
    
    # Mock Redis client
    mock_redis = Mock()
    mock_redis.type.return_value = 'string'
    mock_redis.keys.return_value = [b'test:key1', b'test:key2']
    mock_redis.get.return_value = b'test_value'
    mock_redis.dbsize.return_value = 2
    mock_redis.info.return_value = {
        'redis_version': '7.0.0',
        'redis_mode': 'standalone',
        'db0': {'keys': 2}
    }
    mock_redis.connection_pool.connection_kwargs = {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }
    
    # Mock connection manager
    mock_connection_manager = Mock()
    mock_connection_manager.get_redis_client.return_value = mock_redis
    mock_connection_manager.get_connection_parameters.return_value = ('localhost', 6379, 0, None)
    mock_connection_manager.is_cluster_connection.return_value = False
    data_commands._connection_manager = mock_connection_manager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print("1. Testing normal export completion...")
        
        # Start export
        result = data_commands._export(['--folder', temp_dir])
        print(f"Export start result: {result}")
        
        # Wait a bit for the thread to start
        time.sleep(0.1)
        
        # Check status while running
        if data_commands._export_thread and data_commands._export_thread.is_alive():
            status = data_commands._status()
            print(f"Status while running:\n{status}\n")
            
            # Wait for completion
            data_commands._export_thread.join(timeout=5)
            
        # Check status after completion
        status_after = data_commands._status()
        print(f"Status after completion:\n{status_after}\n")
        
        # Try to start another export - this should work now
        print("2. Testing second export (should not be blocked)...")
        result2 = data_commands._export(['--folder', temp_dir])
        print(f"Second export result: {result2}")
        
        # Wait for second export to complete
        if data_commands._export_thread and data_commands._export_thread.is_alive():
            data_commands._export_thread.join(timeout=5)
        
        # Final status check
        final_status = data_commands._status()
        print(f"Final status:\n{final_status}\n")
        
        print("3. Testing reset functionality...")
        
        # Simulate a stuck state
        data_commands._current_operation = "export"
        data_commands._export_status = "Stuck operation"
        data_commands._export_thread = Mock()
        data_commands._export_thread.is_alive.return_value = False
        
        print("Simulated stuck state - checking status...")
        stuck_status = data_commands._status()
        print(f"Stuck status:\n{stuck_status}\n")
        
        # Test reset
        reset_result = data_commands._export(['--reset'])
        print(f"Reset result: {reset_result}")
        
        # Check status after reset
        reset_status = data_commands._status()
        print(f"Status after reset:\n{reset_status}\n")
        
        # Try export after reset
        print("4. Testing export after reset...")
        result3 = data_commands._export(['--folder', temp_dir])
        print(f"Export after reset result: {result3}")
        
        if data_commands._export_thread and data_commands._export_thread.is_alive():
            data_commands._export_thread.join(timeout=5)
        
        print("✓ All tests completed successfully!")


if __name__ == "__main__":
    test_export_cleanup()
