"""
Improved CLI module for redis-shell (part 2).

This module contains the ShellUI and RedisCLI classes for the improved CLI implementation.
"""

import click
import redis
from typing import Optional, Any, List, Dict, Tuple
import sys
import os
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
from .cli_improved import CommandProcessor, RedisCompleter

# Set up logging
logger = logging.getLogger(__name__)


class ShellUI:
    """User interface for the Redis shell."""
    
    def __init__(self, command_processor, state_manager, connection_manager):
        """
        Initialize the shell UI.
        
        Args:
            command_processor: Command processor instance
            state_manager: State manager instance
            connection_manager: Connection manager instance
        """
        self.command_processor = command_processor
        self.state_manager = state_manager
        self.connection_manager = connection_manager
        
        # Set up prompt styling
        self.style = Style.from_dict({
            'prompt': '#00ff00 bold',
        })
        
        # Create an in-memory history object and populate it from the state manager
        self.history = InMemoryHistory()
        for cmd in self.state_manager.get_command_history():
            self.history.append_string(cmd)
            
        # Create the prompt session with history
        self.session = PromptSession(history=self.history)
        
    def get_prompt(self) -> str:
        """
        Get the prompt string.
        
        Returns:
            Prompt string
        """
        host, port, _, _ = self.connection_manager.get_connection_parameters()
        return f" {host}:{port}> "
        
    def start_interactive(self):
        """Start the interactive shell."""
        print("Connected to Redis. Type '/help' for available commands.")
        print("Commands starting with '/' are shell commands, all other commands are passed directly to Redis.")
        
        while True:
            try:
                # Get input with styled prompt
                command_line = self.session.prompt(self.get_prompt(), style=self.style)
                
                # Save command to history if not empty
                if command_line.strip():
                    self.state_manager.add_command_to_history(command_line.strip())
                    
                # Process the command
                handled, result = self.command_processor.process_command(command_line)
                
                # Display the result
                if result:
                    click.echo(result)
                    
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except RedisShellException as e:
                click.echo(format_exception(e))
                logger.error(f"RedisShellException: {str(e)}")
            except Exception as e:
                click.echo(f"Error: {str(e)}")
                logger.error(f"Unhandled exception: {str(e)}", exc_info=True)


class RedisCLI:
    """Main Redis CLI class."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Initialize the Redis CLI.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
        """
        # Set up logging
        setup_logging(level='info')
        
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
            
        # Initialize the extension manager
        self.extension_manager = ExtensionManager(cli=self)
        
        # Initialize the command processor
        self.command_processor = CommandProcessor(
            connection_manager=self.connection_manager,
            extension_manager=self.extension_manager
        )
        
        # Initialize the completer
        self.completer = RedisCompleter(self)
        
        # Initialize the shell UI
        self.shell_ui = ShellUI(
            command_processor=self.command_processor,
            state_manager=self.state_manager,
            connection_manager=self.connection_manager
        )
        
    def start_interactive(self):
        """Start the interactive shell."""
        try:
            # Check if Redis is reachable
            redis_client = self.connection_manager.get_redis_client()
            if redis_client:
                try:
                    redis_client.ping()
                except redis.RedisError as e:
                    logger.error(f"Error connecting to Redis: {str(e)}")
                    click.echo(f"Warning: Could not connect to Redis: {str(e)}")
                    click.echo("Starting shell anyway. Use '/connection create' to create a new connection.")
            else:
                click.echo("Warning: No Redis connection available.")
                click.echo("Use '/connection create' to create a new connection.")
                
            # Start the interactive shell
            self.shell_ui.start_interactive()
        except Exception as e:
            logger.error(f"Error starting interactive shell: {str(e)}", exc_info=True)
            click.echo(f"Error starting interactive shell: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point."""
    cli = RedisCLI()
    cli.start_interactive()


if __name__ == '__main__':
    main()
