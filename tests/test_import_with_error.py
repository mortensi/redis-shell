#!/usr/bin/env python3

import redis
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/mortensi/workspace/redis-shell')

from redis_shell.extensions.data.commands import DataCommands

def test_import_with_error():
    # Create a test file with some valid and some invalid commands
    test_file = '/tmp/test_import_with_errors.txt'
    
    with open(test_file, 'w') as f:
        f.write('SET "test:key1" "valid value"\n')
        f.write('SET "test:key2" "another valid value"\n')
        f.write('INVALID_COMMAND "test:key3" "this will fail"\n')
        f.write('SET "test:key4" "valid again"\n')
        f.write('TS.ADD "nonexistent:ts" 1000 42.5\n')  # This will fail if TS doesn't exist
        f.write('SET "test:key5" "final valid value"\n')
    
    print(f"Created test file: {test_file}")
    
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Clear any existing test data
    print("Clearing existing test data...")
    for key in r.scan_iter(match='test:*'):
        r.delete(key)
    
    # Create DataCommands instance
    data_commands = DataCommands()
    
    # Create a mock CLI object with the Redis connection
    class MockCLI:
        def __init__(self, redis_client):
            self.redis = redis_client
            self.host = 'localhost'
            self.port = 6379
    
    # Set the CLI object so the import can use it as fallback
    data_commands._cli = MockCLI(r)
    
    # Test the import
    print("Testing import with errors...")
    result = data_commands._import(['--file', test_file])
    print(f"Import result: {result}")
    
    # Verify what was actually imported
    print("\nVerifying imported data...")
    for key in r.scan_iter(match='test:*'):
        value = r.get(key)
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        print(f"  {key.decode('utf-8') if isinstance(key, bytes) else key}: {value}")
    
    # Clean up
    os.remove(test_file)
    print(f"\nCleaned up test file: {test_file}")

if __name__ == '__main__':
    test_import_with_error()
