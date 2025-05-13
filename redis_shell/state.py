import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

class StateManager:
    def __init__(self):
        self.state_file = os.path.expanduser("~/.redis-shell")
        self._state = self._load_state()

        # Initialize command history if it doesn't exist
        if 'command_history' not in self._state:
            self._state['command_history'] = []

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_state(self):
        """Save state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2)

    def get_extension_state(self, extension: str) -> Dict[str, Any]:
        """Get state for an extension."""
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
        if not command or (self._state['command_history'] and self._state['command_history'][-1] == command):
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
