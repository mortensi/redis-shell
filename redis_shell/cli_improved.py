"""
Improved CLI module for redis-shell.

This module contains the improved CLI implementation with better error handling,
dependency injection, and modular design.
"""

import click
import redis
import os
from typing import Optional, Any, List, Dict, Tuple
import sys
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from .extensions import ExtensionManager
from .connection_manager import ConnectionManager
from .state import StateManager
from .utils.logging_utils import setup_logging, format_exception, RedisShellException, CommandError
from .utils.command_utils import CommandParser, CommandFormatter

# Set up logging
logger = logging.getLogger(__name__)


class RedisCompleter(Completer):
    """Completer for Redis commands"""
    def __init__(self, cli):
        self.cli = cli
        # Shell commands (always available)
        self.shell_commands = {
            '/clear': 'Clear screen',
            '/exit': 'Exit shell',
            '/help': 'Show help message',
            '/history': 'Show command history'
        }

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        text = document.text_before_cursor
        cursor_position = document.cursor_position

        # Handle history command completions
        if text.startswith('/history '):
            parts = text.split()
            if len(parts) == 2 and not parts[1]:  # Just '/history '
                # Suggest 'clear' and history numbers
                yield Completion('clear', start_position=0, display_meta='Clear command history')

                # Get history and suggest numbers
                history = self.cli.state_manager.get_command_history()
                if history:
                    for i, cmd in enumerate(history, 1):
                        # Only show first 10 history items in completion
                        if i <= 10:
                            yield Completion(
                                str(i),
                                start_position=0,
                                display_meta=f'Run: {cmd}'
                            )
            return

        # Handle file path completions for commands like "/data import --file /path/to/file"
        parts = text.split()
        if len(parts) >= 4 and parts[0].startswith('/') and parts[1].lower() == 'import' and parts[2] == '--file':
            # Get the partial file path
            if len(parts) == 4:
                partial_path = parts[3]
            else:
                # If there are more parts, the file path might contain spaces
                # In this case, we need to find where the file path starts
                file_path_start = text.find('--file') + len('--file')
                while file_path_start < len(text) and text[file_path_start].isspace():
                    file_path_start += 1
                partial_path = text[file_path_start:]

            # Get completions from the extension manager
            namespace = parts[0].lower()
            cmd_name = parts[1].lower()

            # Find the command definition
            for namespace_key, ext in self.cli.extension_manager.extensions.items():
                if namespace_key.lower() == namespace:
                    for cmd in ext['definition']['commands']:
                        if cmd['name'].lower() == cmd_name:
                            # Find the file option
                            for option in cmd.get('options', []):
                                if option['name'] == '--file' and 'completion' in option:
                                    # Get the completion function
                                    completion_name = option['completion']
                                    if 'completions' in ext['definition']:
                                        completion_def = ext['definition']['completions'].get(completion_name)
                                        if completion_def and completion_def['type'] == 'function':
                                            # Call the completion function
                                            func_name = completion_def['function']
                                            if hasattr(ext['commands'], func_name):
                                                completion_func = getattr(ext['commands'], func_name)
                                                # Get completions for the file path
                                                completions = completion_func(partial_path)

                                                # Find where the partial path starts in the text
                                                path_start = text.rfind(partial_path)
                                                if path_start == -1:  # If not found, use a safe default
                                                    path_start = cursor_position - len(partial_path)

                                                for comp in completions:
                                                    # Calculate start_position relative to cursor
                                                    # This ensures we replace just the partial path, not the whole command
                                                    start_position = path_start - cursor_position
                                                    # Ensure start_position is never positive
                                                    start_position = min(0, start_position)

                                                    yield Completion(
                                                        comp,
                                                        start_position=start_position,
                                                        display_meta=""
                                                    )
                                    break
                            break
                    break
            return

        # Handle extension command completions
        # If we have a namespace and command, but no dash yet (e.g., "/data import")
        if len(parts) == 2 and parts[0].startswith('/') and not parts[1].startswith('-'):
            namespace = parts[0].lower()
            cmd_name = parts[1].lower()

            # Find the command definition
            for namespace_key, ext in self.cli.extension_manager.extensions.items():
                if namespace_key.lower() == namespace:
                    for cmd in ext['definition']['commands']:
                        if cmd['name'].lower() == cmd_name:
                            # If the command has required options, suggest them
                            if 'options' in cmd:
                                for option in cmd['options']:
                                    if option.get('required', False):
                                        yield Completion(
                                            option['name'] + ' ',
                                            start_position=0,
                                            display_meta=option['description']
                                        )
                            break
                    break

        # Show shell commands and extension commands
        if not text or text.startswith('/'):
            # Show built-in commands
            for cmd, desc in self.shell_commands.items():
                if cmd.startswith(text):
                    # Ensure start_position is never positive
                    start_position = min(0, -len(text))
                    yield Completion(
                        cmd,
                        start_position=start_position,
                        display_meta=desc
                    )

            # Show extension commands
            for cmd, desc in self.cli.extension_manager.get_completions(text):
                # Ensure start_position is never positive
                start_position = min(0, -len(text))
                yield Completion(
                    cmd,
                    start_position=start_position,
                    display_meta=desc
                )


class CommandProcessor:
    """Processes and executes commands."""

    def __init__(self, connection_manager, extension_manager):
        """
        Initialize the command processor.

        Args:
            connection_manager: Connection manager instance
            extension_manager: Extension manager instance
        """
        self.connection_manager = connection_manager
        self.extension_manager = extension_manager
        self.command_parser = CommandParser()

    def execute_redis_command(self, command: str, *args) -> Any:
        """
        Execute a Redis command.

        Args:
            command: Redis command
            *args: Command arguments

        Returns:
            Command result

        Raises:
            redis.RedisError: If the command fails
        """
        redis_client = self.connection_manager.get_redis_client()
        if not redis_client:
            raise CommandError("No active Redis connection")

        return redis_client.execute_command(command, *args)

    def process_command(self, command_line: str) -> Tuple[bool, Optional[str]]:
        """
        Process a command line.

        Args:
            command_line: Command line to process

        Returns:
            Tuple containing:
                - handled: Whether the command was handled
                - result: Command result or None
        """
        # Split the command and arguments
        parts = command_line.strip().split()
        if not parts:
            return True, None

        command, *args = parts

        # Handle shell commands (starting with /)
        if command.startswith('/'):
            # Extract the namespace and command
            if command == '/':
                return True, "Invalid command: '/'"

            namespace = command[1:].split(' ')[0]

            # Handle built-in commands
            if namespace == 'clear':
                clear()
                return True, None
            elif namespace == 'exit':
                sys.exit(0)
            elif namespace == 'help':
                return True, self._get_help_text()
            elif namespace == 'history':
                return True, self._handle_history_command(args)

            # Handle extension commands
            result = self.extension_manager.handle_command(namespace, args)
            if result is not None:
                # Handle special connection switching response
                if result.startswith('SWITCH_CONNECTION:'):
                    # Format: SWITCH_CONNECTION:host:port:db:password
                    parts = result.split(':')
                    if len(parts) >= 5:
                        host = parts[1]
                        port = int(parts[2])
                        return True, f"Switched to connection {host}:{port}"
                return True, result

            return True, f"Unknown command: '{command}'"

        # If not a shell command or extension command, pass directly to Redis
        try:
            result = self.execute_redis_command(command, *args)
            return True, self._format_redis_result(result)
        except redis.RedisError as e:
            return True, f"(error) {str(e)}"
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return True, f"Error: {str(e)}"

    def _handle_history_command(self, args: List[str]) -> str:
        """
        Handle history command.

        Args:
            args: Command arguments

        Returns:
            Command result
        """
        # TODO: Implement history command handling
        return "History command not implemented yet"

    def _get_help_text(self) -> str:
        """
        Get help text.

        Returns:
            Help text
        """
        help_text = '''
Available commands:
  /clear   - Clear screen
  /exit    - Exit the shell
  /help    - Show this help message
  /history - Show command history
             Use '/history clear' to clear history
             Use '/history <number>' to run a specific command from history

Note: Commands starting with '/' are extension commands.
      All other commands are passed directly to Redis.
'''
        # Add extension commands
        for namespace, ext in self.extension_manager.extensions.items():
            help_text += f"\n{namespace} Commands:\n"
            for cmd in ext['definition']['commands']:
                help_text += f"  {cmd['usage']} - {cmd['description']}\n"
        return help_text

    def _format_redis_result(self, result: Any) -> str:
        """
        Format a Redis result for display.

        Args:
            result: Redis result

        Returns:
            Formatted result string
        """
        if result is None:
            return "(nil)"

        if isinstance(result, (list, tuple)):
            return '\n'.join([str(item) for item in result])

        return str(result)
