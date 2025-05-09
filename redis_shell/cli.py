import click
import redis
from typing import Optional

class RedisCLI:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def get(self, key: str) -> Optional[str]:
        value = self.redis.get(key)
        return value.decode('utf-8') if value else None

    def set(self, key: str, value: str) -> bool:
        return bool(self.redis.set(key, value))

    def delete(self, key: str) -> bool:
        return bool(self.redis.delete(key))

@click.group()
def main():
    """Redis Shell - An enhanced Redis CLI interface."""
    pass

@main.command()
@click.option('--host', '-h', default='localhost', help='Redis host')
@click.option('--port', '-p', default=6379, help='Redis port')
@click.option('--db', '-d', default=0, help='Redis database number')
@click.argument('key')
def get(host: str, port: int, db: int, key: str):
    """Get the value of a key."""
    try:
        cli = RedisCLI(host, port, db)
        value = cli.get(key)
        if value:
            click.echo(value)
        else:
            click.echo('(nil)')
    except redis.ConnectionError:
        click.echo('Error: Could not connect to Redis server')

@main.command()
@click.option('--host', '-h', default='localhost', help='Redis host')
@click.option('--port', '-p', default=6379, help='Redis port')
@click.option('--db', '-d', default=0, help='Redis database number')
@click.argument('key')
@click.argument('value')
def set(host: str, port: int, db: int, key: str, value: str):
    """Set key to hold the string value."""
    try:
        cli = RedisCLI(host, port, db)
        if cli.set(key, value):
            click.echo('OK')
        else:
            click.echo('Error: Failed to set value')
    except redis.ConnectionError:
        click.echo('Error: Could not connect to Redis server')

@main.command()
@click.option('--host', '-h', default='localhost', help='Redis host')
@click.option('--port', '-p', default=6379, help='Redis port')
@click.option('--db', '-d', default=0, help='Redis database number')
@click.argument('key')
def delete(host: str, port: int, db: int, key: str):
    """Delete a key."""
    try:
        cli = RedisCLI(host, port, db)
        if cli.delete(key):
            click.echo('OK')
        else:
            click.echo('Error: Key not found')
    except redis.ConnectionError:
        click.echo('Error: Could not connect to Redis server')

if __name__ == '__main__':
    main()
