import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

class StateManager:
    """
    Singleton class for managing state across all extensions.
    Ensures all extensions have a consistent view of the state.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Skip initialization if already initialized
        if getattr(self, '_initialized', False):
            return

        # Get state file path from configuration if available
        try:
            from .config import config
            state_file_path = config.get('general', 'state_file')
            if state_file_path:
                # Ensure the directory exists
                state_file = os.path.expanduser(state_file_path)
                state_dir = os.path.dirname(state_file)
                if state_dir and not os.path.exists(state_dir):
                    os.makedirs(state_dir, exist_ok=True)
                self.state_file = state_file
            else:
                self.state_file = os.path.expanduser("~/.redis-shell")
        except (ImportError, AttributeError):
            # Fall back to default if config is not available
            self.state_file = os.path.expanduser("~/.redis-shell")

        self._state = self._load_state()

        # Initialize command history if it doesn't exist
        if 'command_history' not in self._state:
            self._state['command_history'] = []

        # Mark as initialized
        self._initialized = True

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def refresh_state(self):
        """Refresh the state from disk."""
        # Preserve command_history if it exists in memory but not on disk
        old_history = self._state.get('command_history', []) if hasattr(self, '_state') else []

        self._state = self._load_state()

        # Restore command_history if it was lost during refresh
        if 'command_history' not in self._state and old_history:
            self._state['command_history'] = old_history
        elif 'command_history' not in self._state:
            self._state['command_history'] = []

    def _save_state(self):
        """Save state to file."""
        # Ensure the directory exists
        state_dir = os.path.dirname(self.state_file)
        if state_dir and not os.path.exists(state_dir):
            os.makedirs(state_dir, exist_ok=True)

        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2)

        f.close()

    def get_extension_state(self, extension: str) -> Dict[str, Any]:
        """
        Get state for an extension.

        This method refreshes the state from disk before reading to ensure
        we always have the latest state.
        """
        # Refresh state from disk before reading
        self.refresh_state()
        return self._state.get(extension, {})

    def set_extension_state(self, extension: str, state: Dict[str, Any]):
        """Set state for an extension."""
        self._state[extension] = state
        self._save_state()

    def clear_extension_state(self, extension: str):
        """Clear state for an extension."""
        if extension in self._state:
            del self._state[extension]
            self._save_state()

    def clear_all(self):
        """Clear all state."""
        self._state = {}
        self._save_state()

    def add_command_to_history(self, command: str, max_history: int = 100):
        """Add a command to the history.

        Args:
            command: The command to add to history
            max_history: Maximum number of commands to keep in history
        """
        # Don't add empty commands or duplicates of the most recent command
        if (
            not command
            or command.startswith('/history')
            or (
                self._state['command_history']
                and self._state['command_history'][-1] == command
            )
        ):
            return

        # Add the command to history
        self._state['command_history'].append(command)

        # Trim history if it exceeds max_history
        if len(self._state['command_history']) > max_history:
            self._state['command_history'] = self._state['command_history'][-max_history:]

        # Save state
        self._save_state()

    def get_command_history(self) -> List[str]:
        """Get the command history.

        Returns:
            List[str]: The command history
        """
        return self._state.get('command_history', [])

    def save_to_disk(self):
        """Explicitly save the current state to disk."""
        self._save_state()
