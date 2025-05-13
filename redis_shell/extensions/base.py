"""
Base extension class for redis-shell.

This module contains the base Extension class that all extensions should inherit from.
"""

from typing import Optional, Dict, Any, List, Union, Callable
import logging
import json
import os
import importlib.util
import sys
from ..utils.logging_utils import ExtensionError

logger = logging.getLogger(__name__)


class Extension:
    """Base class for redis-shell extensions."""

    def __init__(self, name: str, cli=None):
        """
        Initialize the extension.

        Args:
            name: Extension name
            cli: CLI instance
        """
        self.name = name
        self.cli = cli
        self.commands = {}
        self.completions = {}
        self.definition = {}

    def initialize(self) -> None:
        """Initialize the extension. Called after loading."""
        pass

    def shutdown(self) -> None:
        """Shutdown the extension. Called before unloading."""
        pass

    def handle_command(self, cmd: str, args: List[str]) -> Optional[str]:
        """
        Handle a command.

        Args:
            cmd: Command name
            args: Command arguments

        Returns:
            Command result or None
        """
        raise NotImplementedError("Subclasses must implement handle_command")

    def get_completions(self, text: str) -> List[str]:
        """
        Get completions for the given text.

        Args:
            text: The text to complete

        Returns:
            List of completions
        """
        return []

    def get_help(self) -> str:
        """
        Get help text for the extension.

        Returns:
            Help text
        """
        if not self.definition:
            return f"No help available for extension '{self.name}'"

        help_text = [f"Help for extension '{self.name}'"]

        if 'description' in self.definition:
            help_text.append(f"\n{self.definition['description']}")

        if 'commands' in self.definition:
            help_text.append("\nCommands:")
            for cmd in self.definition['commands']:
                cmd_help = f"  /{self.name} {cmd['name']}"
                if 'description' in cmd:
                    cmd_help += f" - {cmd['description']}"
                help_text.append(cmd_help)

                if 'options' in cmd:
                    for option in cmd['options']:
                        option_help = f"    {option['name']}"
                        if 'description' in option:
                            option_help += f" - {option['description']}"
                        help_text.append(option_help)

        return "\n".join(help_text)


def load_extension(extension_path: str, cli=None) -> Dict[str, Any]:
    """
    Load an extension from the given path.

    Args:
        extension_path: Path to the extension directory
        cli: CLI instance

    Returns:
        Dictionary containing the extension definition and commands
    """
    extension_name = os.path.basename(extension_path)

    # Check if the extension directory exists
    if not os.path.isdir(extension_path):
        raise ExtensionError(f"Extension directory not found: {extension_path}")

    # Check if the extension.json file exists
    extension_json_path = os.path.join(extension_path, "extension.json")
    if not os.path.isfile(extension_json_path):
        raise ExtensionError(f"Extension definition file not found: {extension_json_path}")

    # Load the extension definition
    try:
        with open(extension_json_path, 'r') as f:
            definition = json.load(f)
    except Exception as e:
        raise ExtensionError(f"Error loading extension definition: {str(e)}")

    # Check extension version compatibility
    if 'version' in definition:
        from redis_shell import __version__ as shell_version
        extension_version = definition['version']

        # Check if the extension version is compatible with the shell version
        if 'min_shell_version' in definition:
            min_shell_version = definition['min_shell_version']
            if shell_version < min_shell_version:
                raise ExtensionError(
                    f"Extension '{extension_name}' requires Redis Shell v{min_shell_version} or later "
                    f"(current version: v{shell_version})"
                )

        # Check if the extension version is compatible with the shell version
        if 'max_shell_version' in definition:
            max_shell_version = definition['max_shell_version']
            if shell_version > max_shell_version:
                raise ExtensionError(
                    f"Extension '{extension_name}' is not compatible with Redis Shell v{shell_version} "
                    f"(maximum supported version: v{max_shell_version})"
                )

    # Check extension dependencies
    if 'dependencies' in definition:
        dependencies = definition['dependencies']

        # Check if the required extensions are available
        for dependency in dependencies:
            dependency_name = dependency['name']
            dependency_path = os.path.join(os.path.dirname(extension_path), dependency_name)

            if not os.path.isdir(dependency_path):
                raise ExtensionError(
                    f"Extension '{extension_name}' depends on extension '{dependency_name}', "
                    f"but it is not installed"
                )

            # Check if the dependency version is compatible
            if 'version' in dependency:
                dependency_json_path = os.path.join(dependency_path, "extension.json")
                if not os.path.isfile(dependency_json_path):
                    raise ExtensionError(
                        f"Extension '{dependency_name}' definition file not found: {dependency_json_path}"
                    )

                try:
                    with open(dependency_json_path, 'r') as f:
                        dependency_definition = json.load(f)
                except Exception as e:
                    raise ExtensionError(f"Error loading dependency definition: {str(e)}")

                if 'version' not in dependency_definition:
                    raise ExtensionError(
                        f"Extension '{dependency_name}' does not specify a version"
                    )

                dependency_version = dependency_definition['version']
                required_version = dependency['version']

                # Check if the dependency version is compatible
                if dependency_version != required_version:
                    raise ExtensionError(
                        f"Extension '{extension_name}' requires '{dependency_name}' v{required_version}, "
                        f"but v{dependency_version} is installed"
                    )

    # Check if the commands.py file exists
    commands_py_path = os.path.join(extension_path, "commands.py")
    if not os.path.isfile(commands_py_path):
        raise ExtensionError(f"Extension commands file not found: {commands_py_path}")

    # Load the commands module
    try:
        spec = importlib.util.spec_from_file_location(
            f"redis_shell.extensions.{extension_name}.commands",
            commands_py_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # Get the commands class
        commands_class_name = definition.get('commands_class', 'Commands')
        if not hasattr(module, commands_class_name):
            raise ExtensionError(f"Commands class '{commands_class_name}' not found in {commands_py_path}")

        commands_class = getattr(module, commands_class_name)
        commands = commands_class(cli)

        return {
            'name': extension_name,
            'definition': definition,
            'commands': commands
        }
    except Exception as e:
        raise ExtensionError(f"Error loading extension commands: {str(e)}")
