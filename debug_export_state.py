#!/usr/bin/env python3
"""
Debug script to check and fix export state issues.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager
from redis_shell.state_manager import StateManager


def debug_export_state():
    """Debug the current export state."""
    print("=== Debugging Export State ===\n")
    
    # Create data commands instance
    data_commands = DataCommands()
    
    print("1. Current state variables:")
    print(f"   _export_thread: {data_commands._export_thread}")
    if data_commands._export_thread:
        print(f"   _export_thread.is_alive(): {data_commands._export_thread.is_alive()}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    print(f"   _stop_event.is_set(): {data_commands._stop_event.is_set()}")
    
    print("\n2. Status method output:")
    status = data_commands._status()
    print(status)
    
    print("\n3. Attempting to reset state...")
    reset_result = data_commands._export(['--reset'])
    print(f"Reset result: {reset_result}")
    
    print("\n4. State after reset:")
    print(f"   _export_thread: {data_commands._export_thread}")
    print(f"   _current_operation: {data_commands._current_operation}")
    print(f"   _export_status: {data_commands._export_status}")
    print(f"   _stop_event.is_set(): {data_commands._stop_event.is_set()}")
    
    print("\n5. Status after reset:")
    status_after = data_commands._status()
    print(status_after)
    
    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    debug_export_state()
