import os
import json
import sys
import importlib.util
from typing import Dict, Any, Optional, List, Tuple
from importlib import import_module
from ..connection_manager import ConnectionManager
from ..config import config as app_config

class ExtensionManager:
    def __init__(self, cli=None):
        self.extensions: Dict[str, Any] = {}
        self.available_commands: List[str] = []  # Track all available commands
        self.cli = cli  # Store reference to CLI instance
        self.connection_manager = ConnectionManager()  # Initialize connection manager
        self._load_extensions()

    def _load_extensions(self):
        """Load all extensions from multiple directories:
        1. Built-in extensions from the package
        2. System extensions from the system_extension_dir
        3. User extensions from the extension_dir
        """
        # Load built-in extensions from the package
        extensions_dir = os.path.dirname(__file__)
        self._load_built_in_extensions(extensions_dir)

        # Load system extensions from system_extension_dir
        system_ext_dir = app_config.get('extensions', 'system_extension_dir')
        if system_ext_dir:
            system_ext_dir = os.path.expanduser(system_ext_dir)
            if os.path.exists(system_ext_dir):
                self._load_external_extensions(system_ext_dir)

        # Load user extensions from extension_dir
        user_ext_dir = app_config.get('extensions', 'extension_dir')
        if user_ext_dir:
            user_ext_dir = os.path.expanduser(user_ext_dir)
            if os.path.exists(user_ext_dir):
                self._load_external_extensions(user_ext_dir)

    def _load_built_in_extensions(self, extensions_dir):
        """Load built-in extensions from the package."""
        for ext_name in os.listdir(extensions_dir):
            ext_path = os.path.join(extensions_dir, ext_name)
            if os.path.isdir(ext_path) and not ext_name.startswith('_'):
                self._load_built_in_extension(ext_name, ext_path)

    def _load_external_extensions(self, extensions_dir):
        """Load external extensions from a directory."""
        if not os.path.exists(extensions_dir):
            return

        for ext_name in os.listdir(extensions_dir):
            ext_path = os.path.join(extensions_dir, ext_name)
            if os.path.isdir(ext_path) and not ext_name.startswith('_'):
                self._load_external_extension(ext_name, ext_path)

    def _load_built_in_extension(self, name: str, path: str):
        """Load a single built-in extension from the package."""
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
            print(f"Error loading built-in extension {name}: {str(e)}")

    def _load_external_extension(self, name: str, path: str):
        """Load a single external extension from a directory."""
        json_path = os.path.join(path, 'extension.json')
        if not os.path.exists(json_path):
            return

        # Load extension definition
        with open(json_path) as f:
            definition = json.load(f)

        # Import commands module
        try:
            # Use importlib.util to load the module from a file path
            commands_py_path = os.path.join(path, 'commands.py')
            if not os.path.exists(commands_py_path):
                print(f"Error loading external extension {name}: commands.py not found")
                return

            # Create a unique module name to avoid conflicts
            module_name = f"redis_shell_ext_{name}"

            # Load the module from the file path
            spec = importlib.util.spec_from_file_location(module_name, commands_py_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Get the commands class
            commands_class_name = f"{name.capitalize()}Commands"
            if not hasattr(module, commands_class_name):
                print(f"Error loading external extension {name}: {commands_class_name} class not found")
                return

            commands_class = getattr(module, commands_class_name)

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
            print(f"Error loading external extension {name}: {str(e)}")

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

            # Find the command definition
            if namespace in self.extensions:
                for cmd in self.extensions[namespace]['definition']['commands']:
                    if cmd['name'] == cmd_name:
                        # Check if the command has options defined
                        if 'options' in cmd:
                            # Track which options have already been provided
                            provided_options = set()
                            i = 0
                            while i < len(rest) - 1:
                                if rest[i].startswith('--'):
                                    provided_options.add(rest[i])
                                    # Skip the option value if it exists
                                    if i + 1 < len(rest) - 1 and not rest[i + 1].startswith('--'):
                                        i += 1
                                i += 1

                            # Get the partial option or value
                            partial_text = rest[-1] if rest else ""

                            # If the partial text starts with --, it's an option
                            if partial_text.startswith('--'):
                                # Complete options that haven't been provided yet
                                for option in cmd['options']:
                                    option_name = option['name']
                                    # Only suggest options that haven't been provided and match the partial text
                                    if option_name not in provided_options and option_name.startswith(partial_text):
                                        result.append((option_name, option['description']))

                            # If the previous item is an option with completion, provide completions for its value
                            elif len(rest) >= 2 and rest[-2].startswith('--'):
                                option_name = rest[-2]
                                # Find the option definition
                                for option in cmd['options']:
                                    if option['name'] == option_name and 'completion' in option:
                                        # Get the completion function
                                        completion_name = option['completion']
                                        if 'completions' in self.extensions[namespace]['definition']:
                                            completion_def = self.extensions[namespace]['definition']['completions'].get(completion_name)
                                            if completion_def and completion_def['type'] == 'function':
                                                # Call the completion function
                                                func_name = completion_def['function']
                                                if hasattr(self.extensions[namespace]['commands'], func_name):
                                                    completion_func = getattr(self.extensions[namespace]['commands'], func_name)
                                                    # Get completions for the value
                                                    completions = completion_func(partial_text)
                                                    for comp in completions:
                                                        # Ensure we're returning valid completions
                                                        if isinstance(comp, str):
                                                            # For file paths, we want to return the full path
                                                            # not just the basename, to avoid duplication
                                                            result.append((comp, ""))

                            # If we have all required options and no partial text, suggest the next option
                            elif not partial_text:
                                # Check which required options are missing
                                missing_required = []
                                for option in cmd['options']:
                                    if option.get('required', False) and option['name'] not in provided_options:
                                        missing_required.append(option)

                                # If there are missing required options, suggest them
                                if missing_required:
                                    for option in missing_required:
                                        result.append((option['name'], option['description']))
                                # Otherwise, suggest all remaining options
                                else:
                                    for option in cmd['options']:
                                        if option['name'] not in provided_options:
                                            result.append((option['name'], option['description']))

        return result

    def is_extension_command(self, command: str) -> bool:
        """Check if a command is provided by an extension."""
        return command in self.available_commands
