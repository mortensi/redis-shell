import os
import json
import sys
import importlib.util
from typing import Dict, Any, Optional, List, Tuple
from redis_shell.connection_manager import ConnectionManager
from redis_shell.config import config as app_config

class ExtensionManager:
    def __init__(self, cli=None):
        self.extensions: Dict[str, Any] = {}
        self.available_commands: List[str] = []  # Track all available commands
        self.cli = cli  # Store reference to CLI instance

        # Use the CLI's connection manager if available, otherwise create a new one
        if cli and hasattr(cli, 'connection_manager'):
            self.connection_manager = cli.connection_manager
        else:
            self.connection_manager = ConnectionManager()

        self._load_extensions()

    def _load_extensions(self):
        """Load all extensions from two directories:
        1. Built-in extensions from the package
        2. User extensions from ~/.config/redis-shell/extensions
        """
        # Load built-in extensions from the package
        built_in_dir = os.path.dirname(__file__) + "/extensions"
        self._load_extensions_from_dir(built_in_dir, is_built_in=True)

        # Load user extensions from extension_dir
        user_ext_dir = app_config.get('extensions', 'extension_dir')

        # Update extension_dir if it's not set to the new path
        if user_ext_dir != "~/.config/redis-shell/extensions":
            # Update to the new path
            new_ext_dir = "~/.config/redis-shell/extensions"
            app_config.set('extensions', 'extension_dir', new_ext_dir)
            user_ext_dir = new_ext_dir
            app_config.save_config()

        # Expand the user directory path
        user_ext_dir = os.path.expanduser(user_ext_dir)

        # Create the directory if it doesn't exist
        if not os.path.exists(user_ext_dir):
            try:
                os.makedirs(user_ext_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating user extensions directory: {str(e)}")

        # Load extensions from the user directory
        self._load_extensions_from_dir(user_ext_dir, is_built_in=False)

    def _load_extensions_from_dir(self, extensions_dir, is_built_in=False):
        """Load extensions from a directory.

        Args:
            extensions_dir: Directory containing extensions
            is_built_in: Whether these are built-in extensions
        """
        if not os.path.exists(extensions_dir):
            return

        for ext_name in os.listdir(extensions_dir):
            ext_path = os.path.join(extensions_dir, ext_name)
            if os.path.isdir(ext_path) and not ext_name.startswith('_'):
                self._load_extension(ext_name, ext_path, is_built_in)

    def _load_extension(self, name: str, path: str, is_built_in: bool):
        """Load a single extension from a directory.

        Args:
            name: Extension name
            path: Extension path
            is_built_in: Whether this is a built-in extension
        """
        ext_type = "built-in" if is_built_in else "user"
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
                print(f"Error loading {ext_type} extension {name}: commands.py not found")
                return

            # Create a unique module name to avoid conflicts
            module_name = f"redis_shell.extensions.{name}"

            # Load the module from the file path
            spec = importlib.util.spec_from_file_location(module_name, commands_py_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Get the commands class
            commands_class_name = f"{name.capitalize()}Commands"
            if not hasattr(module, commands_class_name):
                print(f"Error loading {ext_type} extension {name}: {commands_class_name} class not found")
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

        except Exception as e:
            print(f"Error loading {ext_type} extension {name}: {str(e)}")

    def handle_command(self, command: str, args: list) -> Optional[str]:
        """Handle a command if it belongs to an extension."""
        result = None

        # Check if this is a direct namespace command (e.g., /cluster)
        if command in self.extensions:
            # If no arguments are provided, show available subcommands
            if not args:
                ext_def = self.extensions[command]['definition']
                result = f"{command} commands:\n"

                # Add each command with its description
                for cmd in ext_def.get('commands', []):
                    usage = cmd.get('usage', f"{command} {cmd['name']}")
                    description = cmd.get('description', '')
                    result += f"  {usage} - {description}\n"

                # Add a note about how to get more help
                result += f"\nRun '{command} <command>' to execute a specific command."
            else:
                # Normal case: pass the first arg as the command and the rest as args
                result = self.extensions[command]['commands'].handle_command(args[0], args[1:])

        # Special handling for connection commands to ensure state is saved
        if result is not None and command == '/connection' and args and args[0] == 'create' and self.cli:
            # After a connection is created, ensure it's saved to the CLI's state manager
            print("Saving connection state after /connection create")

            # Get the connections from the connection manager
            connections = self.connection_manager.get_connections()
            current_id = self.connection_manager.get_current_connection_id()

            # Update the CLI's state manager
            if hasattr(self.cli, 'state_manager'):
                connection_state = self.cli.state_manager.get_extension_state('connection')
                if not connection_state:
                    connection_state = {}

                # Update connections in state
                connection_state['connections'] = connections
                connection_state['current_connection_id'] = current_id

                # Save the updated state
                self.cli.state_manager.set_extension_state('connection', connection_state)

                # Force save to disk
                self.cli.state_manager.save_to_disk()

                print(f"Saved {len(connections)} connections to CLI's state manager")

        return result

    def get_completions(self, text: str) -> List[Tuple[str, str]]:
        """Get completions that match the input text."""
        result = []

        # Check if we have a namespace followed by a space (e.g., "/cluster ")
        if ' ' in text and text.strip().startswith('/') and len(text.strip().split()) == 1:
            # Extract the namespace (remove trailing spaces)
            namespace = text.strip()

            # If this is a valid namespace, show all its commands
            if namespace in self.extensions:
                for cmd in self.extensions[namespace]['definition']['commands']:
                    result.append((f"{namespace} {cmd['name']}", cmd['description']))
                return result

        # Split the input text into parts
        parts = text.split()

        # If we have just the namespace or partial namespace
        if len(parts) <= 1:
            # If it's just a slash or a partial namespace, only show namespaces
            if text == '/' or (text.startswith('/') and ' ' not in text):
                for namespace, ext in self.extensions.items():
                    if namespace.startswith(text):
                        # Get a description from the extension definition if available
                        description = ext['definition'].get('description', '')
                        result.append((namespace, description))
            # Otherwise, complete namespaces with commands
            else:
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
