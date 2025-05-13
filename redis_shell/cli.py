import click
import redis
import os
from typing import Optional, Any, List, Dict
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from .extensions import ExtensionManager
from .connection_manager import ConnectionManager
from .state import StateManager

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

        # TODO: Add Redis commands autocompletion in the future

class RedisCLI:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        # Initialize the connection manager
        self.connection_manager = ConnectionManager()

        # Initialize the state manager for command history
        self.state_manager = StateManager()

        # Create a default connection if none exists
        if not self.connection_manager.get_connections():
            connection_info = {
                'host': host,
                'port': port,
                'db': db,
                'password': password
            }
            self.connection_manager.add_connection('1', connection_info)
            self.connection_manager.set_current_connection_id('1')

        # Get the current connection parameters
        self.host, self.port, db, password = self.connection_manager.get_connection_parameters()

        # Get or create the Redis client
        self.redis = self.connection_manager.get_redis_client()
        if not self.redis:
            self.redis = redis.Redis(host=self.host, port=self.port, db=db, password=password)

        self.style = Style.from_dict({
            'prompt': '#00ff00 bold',
        })
        self.extension_manager = ExtensionManager(cli=self)  # Pass self to ExtensionManager
        self.completer = RedisCompleter(self)

        # Create an in-memory history object and populate it from the state manager
        self.history = InMemoryHistory()
        for cmd in self.state_manager.get_command_history():
            self.history.append_string(cmd)

        # Create the prompt session with history
        self.session = PromptSession(completer=self.completer, history=self.history)

    def get_prompt(self):
        """Get the prompt string."""
        return f" {self.host}:{self.port}> "

    def execute_command(self, command: str, *args) -> Any:
        """Execute a Redis command."""
        return self.redis.execute_command(command, *args)

    def handle_shell_command(self, command: str, args: List[str]) -> Optional[str]:
        """Handle shell commands."""
        if command == '/clear':
            clear()
            return None
        elif command == '/exit':
            sys.exit(0)
        elif command == '/history':
            # Handle history command
            history = self.state_manager.get_command_history()

            # Clear history
            if args and args[0] == 'clear':
                self.state_manager._state['command_history'] = []
                self.state_manager._save_state()
                self.history = InMemoryHistory()  # Reset in-memory history
                self.session = PromptSession(completer=self.completer, history=self.history)  # Recreate session
                return 'Command history cleared.'

            # Run a specific command from history
            elif args and args[0].isdigit():
                index = int(args[0])
                if not history:
                    return 'No command history available.'
                if index < 1 or index > len(history):
                    return f'Invalid history index: {index}. Valid range is 1-{len(history)}.'

                # Get the command from history
                cmd = history[index - 1]
                print(f"Running command: {cmd}")

                # Split the command and arguments
                parts = cmd.strip().split()
                if not parts:
                    return 'Empty command in history.'

                command_to_run, *args_to_run = parts

                # Handle shell commands (starting with /)
                if command_to_run.startswith('/'):
                    result = self.handle_shell_command(command_to_run.lower(), args_to_run)
                    return result if result else f"Executed: {cmd}"

                # Handle legacy extension commands
                result = self.extension_manager.handle_command(command_to_run.lower(), args_to_run)
                if result is not None:
                    return result

                # If not a shell command or extension command, pass directly to Redis
                try:
                    result = self.execute_command(command_to_run, *args_to_run)
                    if isinstance(result, (list, tuple)):
                        formatted_result = '\n'.join([str(item) for item in result])
                        return f"Executed: {cmd}\n{formatted_result}"
                    else:
                        return f"Executed: {cmd}\n{result}"
                except redis.RedisError as e:
                    return f"Error executing '{cmd}': {str(e)}"

            # Show history
            else:
                if not history:
                    return 'No command history available.'

                # Format history with line numbers
                result = 'Command history:\n'
                for i, cmd in enumerate(history, 1):
                    result += f"{i:3d}: {cmd}\n"

                result += "\nUse '/history clear' to clear history."
                result += "\nUse '/history <number>' to run a specific command from history."
                return result
        elif command == '/help':
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

        # Check if this is an extension command
        result = self.extension_manager.handle_command(command, args)
        if result is not None:
            # Handle special connection switching response
            if result.startswith('SWITCH_CONNECTION:'):
                # Format: SWITCH_CONNECTION:host:port:db:password
                parts = result.split(':')
                if len(parts) >= 5:
                    host = parts[1]
                    port = int(parts[2])
                    # We don't need db and password here as the connection manager handles it

                    # The connection manager has already been updated by the connection extension
                    # Just update our local references
                    self.redis = self.connection_manager.get_redis_client()
                    self.host = host
                    self.port = port

                    return f"Switched to connection {host}:{port}"
            return result

        return None

    def start_interactive(self):
        """Start the interactive shell."""
        while True:
            try:
                # Get input with styled prompt
                command_line = self.session.prompt(self.get_prompt(), style=self.style)

                # Save command to history if not empty
                if command_line.strip():
                    self.state_manager.add_command_to_history(command_line.strip())

                # Split the command and arguments
                parts = command_line.strip().split()
                if not parts:
                    continue

                command, *args = parts

                # Handle shell commands (starting with /)
                if command.startswith('/'):
                    result = self.handle_shell_command(command.lower(), args)
                    if result:
                        click.echo(result)
                    continue

                # Handle legacy extension commands
                result = self.extension_manager.handle_command(command.lower(), args)
                if result is not None:
                    click.echo(result)
                    continue

                # If not a shell command or extension command, pass directly to Redis
                try:
                    result = self.execute_command(command, *args)
                except redis.RedisError as e:
                    result = f"(error) {str(e)}"

                # Format and display the result
                if result is not None:
                    if isinstance(result, (list, tuple)):
                        for item in result:
                            click.echo(item)
                    else:
                        click.echo(result)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                click.echo(f"Error: {str(e)}")

def main():
    """Main entry point."""
    cli = RedisCLI()
    print("Connected to Redis. Type '/help' for available commands.")
    print("Commands starting with '/' are shell commands, all other commands are passed directly to Redis.")
    cli.start_interactive()

if __name__ == '__main__':
    main()
