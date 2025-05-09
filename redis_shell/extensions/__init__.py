import os
import json
from typing import Dict, Any, Optional, List
from importlib import import_module

class ExtensionManager:
    def __init__(self):
        self.extensions: Dict[str, Any] = {}
        self._load_extensions()

    def _load_extensions(self):
        """Load all extensions from the extensions directory."""
        extensions_dir = os.path.dirname(__file__)
        for ext_name in os.listdir(extensions_dir):
            ext_path = os.path.join(extensions_dir, ext_name)
            if os.path.isdir(ext_path) and not ext_name.startswith('_'):
                self._load_extension(ext_name, ext_path)

    def _load_extension(self, name: str, path: str):
        """Load a single extension."""
        json_path = os.path.join(path, 'extension.json')
        if not os.path.exists(json_path):
            return

        # Load extension definition
        with open(json_path) as f:
            definition = json.load(f)

        # Import commands module
        try:
            module = import_module(f'.{name}.commands', package='redis_shell.extensions')
            commands_class = getattr(module, f"{name.capitalize()}Commands")
            
            # Store extension info
            self.extensions[definition['namespace']] = {
                'definition': definition,
                'commands': commands_class()
            }
        except Exception:
            pass

    def handle_command(self, command: str, args: list) -> Optional[str]:
        """Handle a command if it belongs to an extension."""
        if command in self.extensions:
            return self.extensions[command]['commands'].handle_command(args[0], args[1:])
        return None

    def get_completions(self, text: str) -> List[tuple]:
        """Get completions that match the input text."""
        result = []
        for namespace, ext in self.extensions.items():
            if not text or namespace.startswith(text):
                for cmd in ext['definition']['commands']:
                    result.append((f"{namespace} {cmd['name']}", cmd['description']))
        return result
