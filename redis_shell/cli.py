import click
import redis
from typing import Optional, Any, List, Dict
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from .extensions import ExtensionManager

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
            '/help': 'Show help message'
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
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.mode = 'shell'  # Default mode
        self.style = Style.from_dict({
            'prompt': '#00ff00 bold',
            'mode': '#ff0000 bold',
        })
        self.extension_manager = ExtensionManager()
        self.completer = RedisCompleter(self)
        self.session = PromptSession(completer=self.completer)
        self._in_shell_mode = True  # Track shell mode internally

    def execute_command(self, *args) -> Any:
        """Execute a raw Redis command using redis-py's execute_command method."""
        try:
            result = self.redis.execute_command(*args)
            if isinstance(result, bytes):
                return result.decode('utf-8')
            elif isinstance(result, list):
                return [item.decode('utf-8') if isinstance(item, bytes) else str(item) for item in result]
            return result
        except redis.RedisError as e:
            return f"(error) {str(e)}"

    def get_prompt(self) -> List[tuple]:
        """Get the styled prompt based on current mode."""
        mode_str = f"[{self.mode.upper()}]" if self.mode == 'resp' else ''
        return [
            ('class:mode', mode_str),
            ('class:prompt', f' redis> ')
        ]

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
        elif command == '/help':
            help_text = '''
Available commands:
  /shell - Switch to shell mode (structured commands)
  /resp  - Switch to RESP mode (raw Redis commands)
  /clear - Clear screen
  /exit  - Exit the shell
  /help  - Show this help message
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
                return result
        
        return None

    def start_interactive(self):
        """Start the interactive shell."""
        while True:
            try:
                # Get input with styled prompt
                command_line = self.session.prompt(self.get_prompt(), style=self.style)
                
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

                # Check for cluster commands in shell mode
                if self._in_shell_mode and command.lower() in ['deploycluster', 'stopcluster', 'clusterinfo']:
                    result = self.handle_shell_command(command.lower(), args)
                    if result:
                        click.echo(result)
                    continue

                # Execute Redis commands
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

@click.command()
@click.option('--host', '-h', default='localhost', help='Redis host')
@click.option('--port', '-p', default=6379, help='Redis port')
@click.option('--db', '-d', default=0, help='Redis database number')
def main(host: str, port: int, db: int):
    """Redis Shell - An enhanced Redis CLI interface with shell and RESP modes."""
    try:
        cli = RedisCLI(host=host, port=port, db=db)
        click.echo("Connected to Redis. Type '/help' for available commands.")
        cli.start_interactive()
    except redis.ConnectionError:
        click.echo('Error: Could not connect to Redis server')
    except Exception as e:
        click.echo(f'Error: {str(e)}')

if __name__ == '__main__':
    main()
