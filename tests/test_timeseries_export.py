#!/usr/bin/env python3

import redis
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/mortensi/workspace/redis-shell')

from redis_shell.extensions.data.commands import DataCommands

def test_timeseries_export():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Clear any existing test data
    print("Clearing existing test data...")
    for key in r.scan_iter(match='ts:*'):
        r.delete(key)
    
    # Add some TimeSeries test data
    print("Adding TimeSeries test data...")
    try:
        # Create a time series
        r.execute_command('TS.CREATE', 'ts:test1')
        r.execute_command('TS.ADD', 'ts:test1', 1000, 10.5)
        r.execute_command('TS.ADD', 'ts:test1', 2000, 20.3)
        r.execute_command('TS.ADD', 'ts:test1', 3000, 30.7)
        
        # Create another time series with integer values
        r.execute_command('TS.CREATE', 'ts:test2')
        r.execute_command('TS.ADD', 'ts:test2', 1000, 100)
        r.execute_command('TS.ADD', 'ts:test2', 2000, 200)
        r.execute_command('TS.ADD', 'ts:test2', 3000, 300)
        
        print("TimeSeries data added successfully")
    except Exception as e:
        print(f"Error adding TimeSeries data (Redis might not have TimeSeries module): {e}")
        return
    
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
    print("Testing TimeSeries export...")
    result = data_commands._export(['--folder', '/tmp', '--pattern', 'ts:*'])
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
        
        # Test import
        print("\nTesting import...")
        
        # Clear the original data
        print("Clearing original TimeSeries data...")
        for key in r.scan_iter(match='ts:*'):
            r.delete(key)
        
        # Import the data back
        print("Starting import process...")
        import_result = data_commands._import(['--file', latest_file])
        print(f"Import result: {import_result}")

        # Also test manual command execution to see what's happening
        print("\nTesting manual command execution...")
        try:
            # Test a simple TS.CREATE command
            r.execute_command('TS.CREATE', 'ts:manual_test')
            print("Manual TS.CREATE succeeded")

            # Test a simple TS.ADD command
            r.execute_command('TS.ADD', 'ts:manual_test', 1000, 42.5)
            print("Manual TS.ADD succeeded")

            # Clean up
            r.delete('ts:manual_test')
        except Exception as e:
            print(f"Manual command failed: {e}")
        
        # Verify the data was imported correctly
        print("\nVerifying imported data...")
        try:
            ts1_data = r.execute_command('TS.RANGE', 'ts:test1', '-', '+')
            ts2_data = r.execute_command('TS.RANGE', 'ts:test2', '-', '+')
            print(f"ts:test1 data: {ts1_data}")
            print(f"ts:test2 data: {ts2_data}")
        except Exception as e:
            print(f"Error verifying imported data: {e}")
        
    else:
        print("No export file found!")

if __name__ == '__main__':
    test_timeseries_export()
