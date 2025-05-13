import os
import json
from typing import Dict, Any, Optional, List, Tuple
from importlib import import_module
from ..connection_manager import ConnectionManager

class ExtensionManager:
    def __init__(self, cli=None):
        self.extensions: Dict[str, Any] = {}
        self.available_commands: List[str] = []  # Track all available commands
        self.cli = cli  # Store reference to CLI instance
        self.connection_manager = ConnectionManager()  # Initialize connection manager
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
            # Pass CLI instance to commands class if it accepts it
            try:
                # Try to initialize with CLI instance
                commands_instance = commands_class(cli=self.cli)
            except TypeError:
                # Fall back to standard initialization if CLI parameter is not supported
                commands_instance = commands_class()

            self.extensions[definition['namespace']] = {
                'definition': definition,
                'commands': commands_instance
            }

            # Track all available commands from this extension
            if 'commands' in definition:
                for cmd in definition['commands']:
                    if 'name' in cmd:
                        # Add both the namespaced command and any legacy direct commands
                        self.available_commands.append(f"{definition['namespace']} {cmd['name']}")

                        # Some extensions might define legacy direct commands (without namespace)
                        if 'legacy_command' in cmd:
                            self.available_commands.append(cmd['legacy_command'])
        except Exception as e:
            print(f"Error loading extension {name}: {str(e)}")

    def handle_command(self, command: str, args: list) -> Optional[str]:
        """Handle a command if it belongs to an extension."""
        # Check if this is a direct namespace command (e.g., /cluster)
        if command in self.extensions:
            return self.extensions[command]['commands'].handle_command(args[0], args[1:])

        # Check if this is a legacy command (e.g., deploycluster)
        # We need to find which extension and command it maps to
        for namespace, ext in self.extensions.items():
            for cmd_def in ext['definition']['commands']:
                if 'legacy_command' in cmd_def and cmd_def['legacy_command'] == command:
                    # Found a legacy command, execute it through the extension
                    return ext['commands'].handle_command(cmd_def['name'], args)

        return None

    def get_completions(self, text: str) -> List[Tuple[str, str]]:
        """Get completions that match the input text."""
        result = []

        # Split the input text into parts
        parts = text.split()

        # If we have just the namespace or partial namespace
        if len(parts) <= 1:
            # Complete namespaces
            for namespace, ext in self.extensions.items():
                if not text or namespace.startswith(text):
                    for cmd in ext['definition']['commands']:
                        result.append((f"{namespace} {cmd['name']}", cmd['description']))

        # If we have namespace and command
        elif len(parts) == 2:
            namespace, partial_cmd = parts
            # Complete commands for the given namespace
            if namespace in self.extensions:
                for cmd in self.extensions[namespace]['definition']['commands']:
                    if cmd['name'].startswith(partial_cmd):
                        result.append((f"{namespace} {cmd['name']}", cmd['description']))

        # If we have namespace, command, and partial option
        elif len(parts) >= 3:
            namespace, cmd_name, *rest = parts
            partial_option = rest[-1] if rest else ""

            # Find the command definition
            if namespace in self.extensions:
                for cmd in self.extensions[namespace]['definition']['commands']:
                    if cmd['name'] == cmd_name:
                        # Check if the command has options defined
                        if 'options' in cmd:
                            # Complete options
                            for option in cmd['options']:
                                option_name = option['name']
                                if option_name.startswith(partial_option):
                                    result.append((option_name, option['description']))

                            # If the partial option matches an option with completion
                            for option in cmd['options']:
                                if option['name'] == partial_option and 'completion' in option:
                                    # Get the completion function
                                    completion_name = option['completion']
                                    if 'completions' in self.extensions[namespace]['definition']:
                                        completion_def = self.extensions[namespace]['definition']['completions'].get(completion_name)
                                        if completion_def and completion_def['type'] == 'function':
                                            # Call the completion function
                                            func_name = completion_def['function']
                                            if hasattr(self.extensions[namespace]['commands'], func_name):
                                                completion_func = getattr(self.extensions[namespace]['commands'], func_name)
                                                # Get completions for the next argument
                                                next_arg = "" if len(rest) <= 1 else rest[-1]
                                                completions = completion_func(next_arg)
                                                for comp in completions:
                                                    result.append((comp, ""))

        return result

    def is_extension_command(self, command: str) -> bool:
        """Check if a command is provided by an extension."""
        return command in self.available_commands
