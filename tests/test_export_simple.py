#!/usr/bin/env python3

import redis
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/mortensi/workspace/redis-shell')

from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager

def test_export():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)

    # Clear any existing test data
    print("Clearing existing test data...")
    for key in r.scan_iter(match='test:*'):
        r.delete(key)

    # Add some test data
    print("Adding test data...")
    r.set('test:key1', 'hello world')
    r.set('test:key2', 'another value')
    r.hset('test:hash', 'field1', 'value1')
    r.hset('test:hash', 'field2', 'value2')
    r.lpush('test:list', 'item1', 'item2', 'item3')

    # Create DataCommands instance and bypass connection manager
    data_commands = DataCommands()

    # Create a mock CLI object with the Redis connection
    class MockCLI:
        def __init__(self, redis_client):
            self.redis = redis_client
            self.host = 'localhost'
            self.port = 6379

    # Set the CLI object so the export can use it as fallback
    data_commands._cli = MockCLI(r)

    # Test the export
    print("Testing export...")
    result = data_commands._export(['--folder', '/tmp', '--pattern', 'test:*'])
    print(f"Export result: {result}")

    # Check if export file was created
    import glob
    export_files = sorted(glob.glob('/tmp/redis-export-*.txt'), key=os.path.getmtime, reverse=True)
    if export_files:
        latest_file = export_files[0]
        print(f"Latest export file: {latest_file}")
        with open(latest_file, 'r') as f:
            content = f.read()
            print(f"Export file content:\n{content}")
    else:
        print("No export file found!")

if __name__ == '__main__':
    test_export()
