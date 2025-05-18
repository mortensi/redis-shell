#!/usr/bin/env python3
"""
Test script to verify that the StateManager is working correctly as a singleton.
"""

import os
import tempfile
import json
from redis_shell.state import StateManager

def test_singleton_behavior():
    """Test that multiple instances of StateManager are the same object."""
    # Create two instances of StateManager
    state1 = StateManager()
    state2 = StateManager()

    # Verify they are the same object
    assert state1 is state2

    # Verify they share the same state
    state1._state['test_key'] = 'test_value'
    assert state2._state['test_key'] == 'test_value'

    print("✅ StateManager singleton test passed!")

def test_state_persistence():
    """Test that state is persisted to disk and can be loaded."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Create a StateManager instance
        state = StateManager()

        # Override the state file path
        original_path = state.state_file
        state.state_file = temp_path

        # Set some state
        state._state = {'test_extension': {'key1': 'value1'}}
        state._save_state()

        # Create a new StateManager instance
        state2 = StateManager()
        state2.state_file = temp_path

        # Load the state from disk
        loaded_state = state2._load_state()

        # Verify the state was loaded correctly
        assert loaded_state == {'test_extension': {'key1': 'value1'}}

        # Restore the original state file path
        state.state_file = original_path
        state2.state_file = original_path

        print("✅ StateManager persistence test passed!")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# Thread safety test removed since we removed the lock

if __name__ == "__main__":
    print("Testing StateManager singleton behavior...")
    test_singleton_behavior()

    print("\nTesting StateManager persistence...")
    test_state_persistence()

    print("\nAll tests passed! The StateManager is working correctly as a singleton.")
