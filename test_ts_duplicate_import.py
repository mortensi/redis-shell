#!/usr/bin/env python3

import redis
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/mortensi/workspace/redis-shell')

from redis_shell.extensions.data.commands import DataCommands

def test_duplicate_import():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Clear any existing test data
    print("Clearing existing test data...")
    for key in r.scan_iter(match='test_dup:*'):
        r.delete(key)
    
    # Create a TimeSeries with BLOCK duplicate policy (the problematic scenario)
    print("Creating TimeSeries with BLOCK duplicate policy...")
    try:
        r.execute_command('TS.CREATE', 'test_dup:ts1', 'DUPLICATE_POLICY', 'BLOCK')
        r.execute_command('TS.ADD', 'test_dup:ts1', 1000, 10.5)
        r.execute_command('TS.ADD', 'test_dup:ts1', 2000, 20.3)
        print("TimeSeries with BLOCK policy created successfully")
    except Exception as e:
        print(f"Error creating TimeSeries: {e}")
        return
    
    # Create DataCommands instance
    data_commands = DataCommands()
    
    # Create a mock CLI object with the Redis connection
    class MockCLI:
        def __init__(self, redis_client):
            self.redis = redis_client
            self.host = 'localhost'
            self.port = 6379
    
    data_commands._cli = MockCLI(r)
    
    # Export the TimeSeries
    print("Exporting TimeSeries...")
    result = data_commands._export(['--folder', '/tmp', '--pattern', 'test_dup:*'])
    print(f"Export result: {result}")
    
    # Find the export file
    import glob
    export_files = sorted(glob.glob('/tmp/redis-export-*.txt'), key=os.path.getmtime, reverse=True)
    if not export_files:
        print("No export file found!")
        return
    
    latest_file = export_files[0]
    print(f"Export file: {latest_file}")
    
    with open(latest_file, 'r') as f:
        content = f.read()
        print(f"Export content:\n{content}")
    
    # Now try to import it back (this should work because we use DUPLICATE_POLICY LAST)
    print("Testing import (should work with DUPLICATE_POLICY LAST)...")
    import_result = data_commands._import(['--file', latest_file])
    print(f"Import result: {import_result}")
    
    # Verify the data
    print("Verifying data after import...")
    try:
        ts_data = r.execute_command('TS.RANGE', 'test_dup:ts1', '-', '+')
        print(f"TimeSeries data: {ts_data}")
        
        # Check the duplicate policy
        ts_info = r.execute_command('TS.INFO', 'test_dup:ts1')
        print(f"TimeSeries info: {ts_info}")
    except Exception as e:
        print(f"Error verifying data: {e}")

if __name__ == '__main__':
    test_duplicate_import()
