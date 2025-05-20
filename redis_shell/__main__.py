"""
Main entry point for redis-shell.

This module contains the main entry point for redis-shell.
"""

import click
import os
import sys
import logging
from typing import Optional
from .cli import RedisCLI
from .utils.logging_utils import setup_logging
from .config import config as app_config


@click.command()
@click.option('--host', '-h', default=None, help='Redis host')
@click.option('--port', '-p', default=None, type=int, help='Redis port')
@click.option('--db', '-n', default=None, type=int, help='Redis database number')
@click.option('--username', '-u', default=None, help='Redis username')
@click.option('--password', '-a', default=None, help='Redis password')
@click.option('--config-file', '-c', default=None, help='Path to configuration file')
@click.option('--log-level', '-l', default=None, help='Log level (debug, info, warning, error, critical)')
@click.option('--log-file', '-f', default=None, help='Path to log file')
@click.option('--command', '-x', default=None, help='Command to execute')
@click.option('--ssl', is_flag=True, help='Enable SSL/TLS connection')
@click.option('--ssl-ca-certs', default=None, help='Path to CA certificate file')
@click.option('--ssl-ca-path', default=None, help='Path to CA certificates directory')
@click.option('--ssl-keyfile', default=None, help='Path to private key file')
@click.option('--ssl-certfile', default=None, help='Path to certificate file')
@click.option('--ssl-cert-reqs', default=None,
              type=click.Choice(['none', 'optional', 'required']),
              help='Certificate requirements (none, optional, required)')
@click.option('--version', '-v', is_flag=True, help='Show version and exit')
def main(
    host: Optional[str],
    port: Optional[int],
    db: Optional[int],
    username: Optional[str],
    password: Optional[str],
    config_file: Optional[str],
    log_level: Optional[str],
    log_file: Optional[str],
    command: Optional[str],
    ssl: bool,
    ssl_ca_certs: Optional[str],
    ssl_ca_path: Optional[str],
    ssl_keyfile: Optional[str],
    ssl_certfile: Optional[str],
    ssl_cert_reqs: Optional[str],
    version: bool
):
    """Redis Shell - Interactive Redis CLI with extensions."""
    # Show version and exit
    if version:
        from . import __version__
        click.echo(f"Redis Shell v{__version__}")
        sys.exit(0)

    # Set custom config file if provided
    if config_file:
        os.environ['REDIS_SHELL_CONFIG'] = config_file
        # Reload config with the new file
        app_config.config_file = os.path.expanduser(config_file)
        app_config._load_config()

    # Set up logging
    if log_level:
        app_config.set('general', 'log_level', log_level)
    if log_file:
        app_config.set('general', 'log_file', log_file)

    log_level = app_config.get('general', 'log_level', 'info')
    log_file = app_config.get('general', 'log_file')

    logger = setup_logging(level=log_level, log_file=log_file)

    # Get Redis connection parameters
    if host:
        app_config.set('redis', 'default_host', host)
    if port:
        app_config.set('redis', 'default_port', port)
    if db:
        app_config.set('redis', 'default_db', db)
    if username:
        app_config.set('redis', 'default_username', username)
    if password:
        app_config.set('redis', 'default_password', password)

    # Set SSL parameters if provided
    if ssl:
        app_config.set('redis', 'ssl', ssl)
    if ssl_ca_certs:
        app_config.set('redis', 'ssl_ca_certs', ssl_ca_certs)
    if ssl_ca_path:
        app_config.set('redis', 'ssl_ca_path', ssl_ca_path)
    if ssl_keyfile:
        app_config.set('redis', 'ssl_keyfile', ssl_keyfile)
    if ssl_certfile:
        app_config.set('redis', 'ssl_certfile', ssl_certfile)
    if ssl_cert_reqs:
        app_config.set('redis', 'ssl_cert_reqs', ssl_cert_reqs)

    # Get all connection parameters from config
    host = app_config.get('redis', 'default_host', '127.0.0.1')
    port = app_config.get('redis', 'default_port', 6379)
    db = app_config.get('redis', 'default_db', 0)
    username = app_config.get('redis', 'default_username', 'default')
    password = app_config.get('redis', 'default_password', '')
    use_ssl = app_config.get('redis', 'ssl', False)
    ssl_ca_certs = app_config.get('redis', 'ssl_ca_certs')
    ssl_ca_path = app_config.get('redis', 'ssl_ca_path')
    ssl_keyfile = app_config.get('redis', 'ssl_keyfile')
    ssl_certfile = app_config.get('redis', 'ssl_certfile')
    ssl_cert_reqs = app_config.get('redis', 'ssl_cert_reqs', 'required')

    # Create the CLI with all connection parameters
    cli = RedisCLI(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        ssl=use_ssl,
        ssl_ca_certs=ssl_ca_certs,
        ssl_ca_path=ssl_ca_path,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=ssl_cert_reqs
    )

    # Execute a command and exit
    if command:
        # Split the command and arguments
        parts = command.strip().split()
        if parts:
            cmd, *args = parts

            # Handle shell commands (starting with /)
            if cmd.startswith('/'):
                result = cli.handle_shell_command(cmd.lower(), args)
                if result:
                    click.echo(result)
            else:
                # Try to execute as a Redis command
                try:
                    result = cli.execute_command(cmd, *args)
                    if result:
                        click.echo(result)
                except Exception as e:
                    click.echo(f"Error: {str(e)}")
        sys.exit(0)

    # Start the interactive shell
    try:
        # Display welcome message
        from . import __version__
        click.echo(f"Welcome to Redis Shell v{__version__}")
        click.echo("Connected to Redis. Type '/help' for available commands.")
        click.echo("Commands starting with '/' are shell commands, all other commands are passed directly to Redis.")

        cli.start_interactive()
    except KeyboardInterrupt:
        click.echo("\nExiting...")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        click.echo(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
