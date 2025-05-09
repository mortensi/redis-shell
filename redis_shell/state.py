import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class StateManager:
    def __init__(self):
        self.state_file = os.path.expanduser("~/.redis-shell")
        self._state = self._load_state()

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
