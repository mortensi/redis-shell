import click
import redis
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
            '/shell': 'Switch to shell mode',
            '/resp': 'Switch to RESP mode',
            '/clear': 'Clear screen',
            '/exit': 'Exit shell',
            '/help': 'Show help message',
            '/history': 'Show command history'
        }

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        text = document.text_before_cursor

        # Show shell commands
        if not text or text.startswith('/'):
            # Show built-in commands
            for cmd, desc in self.shell_commands.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc
                    )

            # Show extension commands in shell mode
            if self.cli._in_shell_mode:
                for cmd, desc in self.cli.extension_manager.get_completions(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc
                    )
            # No Redis commands autocompletion

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

        self.mode = 'shell'  # Default mode
        self.style = Style.from_dict({
            'prompt': '#00ff00 bold',
            'mode': '#ff0000 bold',
        })
        self.extension_manager = ExtensionManager(cli=self)  # Pass self to ExtensionManager
        self.completer = RedisCompleter(self)

        # Create an in-memory history object and populate it from the state manager
        self.history = InMemoryHistory()
        for cmd in self.state_manager.get_command_history():
            self.history.append_string(cmd)

        # Create the prompt session with history
        self.session = PromptSession(completer=self.completer, history=self.history)
        self._in_shell_mode = True  # Track shell mode internally

    def get_prompt(self):
        """Get the prompt string."""
        return f" {self.host}:{self.port} {self.mode}> "

    def execute_command(self, command: str, *args) -> Any:
        """Execute a Redis command."""
        return self.redis.execute_command(command, *args)

    def handle_shell_command(self, command: str, args: List[str]) -> Optional[str]:
        """Handle shell mode commands."""
        if command == '/resp':
            self.mode = 'resp'
            self._in_shell_mode = False
            return 'Switched to RESP mode. Use Redis commands directly.'
        elif command == '/shell':
            self.mode = 'shell'
            self._in_shell_mode = True
            return 'Switched to shell mode.'
        elif command == '/clear':
            clear()
            return None
        elif command == '/exit':
            sys.exit(0)
        elif command == '/history':
            # Handle history command
            if args and args[0] == 'clear':
                # Clear history
                self.state_manager._state['command_history'] = []
                self.state_manager._save_state()
                self.history = InMemoryHistory()  # Reset in-memory history
                self.session = PromptSession(completer=self.completer, history=self.history)  # Recreate session
                return 'Command history cleared.'
            else:
                # Show history
                history = self.state_manager.get_command_history()
                if not history:
                    return 'No command history available.'

                # Format history with line numbers
                result = 'Command history:\n'
                for i, cmd in enumerate(history, 1):
                    result += f"{i:3d}: {cmd}\n"

                result += "\nUse '/history clear' to clear history."
                return result
        elif command == '/help':
            help_text = '''
Available commands:
  /shell   - Switch to shell mode (only extension commands are available)
  /resp    - Switch to RESP mode (all Redis commands are available)
  /clear   - Clear screen
  /exit    - Exit the shell
  /help    - Show this help message
  /history - Show command history (use '/history clear' to clear history)

Note: In shell mode, only commands from loaded extensions are available.
      In RESP mode, all Redis commands are available directly.
'''
            # Add extension commands
            for namespace, ext in self.extension_manager.extensions.items():
                help_text += f"\n{namespace} Commands:\n"
                for cmd in ext['definition']['commands']:
                    help_text += f"  {cmd['usage']} - {cmd['description']}\n"
            return help_text

        # Check if this is an extension command
        if self._in_shell_mode:
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

                # Handle shell commands (they work in both modes)
                if command.startswith('/'):
                    result = self.handle_shell_command(command.lower(), args)
                    if result:
                        click.echo(result)
                    continue

                # Handle legacy extension commands in shell mode
                if self._in_shell_mode:
                    # Try to handle it as a legacy extension command
                    result = self.extension_manager.handle_command(command.lower(), args)
                    if result is not None:
                        click.echo(result)
                        continue

                # In shell mode, validate commands before execution
                if self._in_shell_mode:
                    # If we get here, it's not a shell command or extension command
                    # In shell mode, we should only allow known/valid commands
                    result = f"(error) Unknown command '{command}'. In shell mode, only extension commands are available. Type '/help' for available commands or use '/resp' to switch to RESP mode for direct Redis commands."
                # In RESP mode, pass all commands directly to Redis
                else:
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
    cli.start_interactive()

if __name__ == '__main__':
    main()
