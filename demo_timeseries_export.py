#!/usr/bin/env python3
"""
Demo script showing Redis Time Series export/import functionality.

This script demonstrates the new TSDB-TYPE support in the Redis Shell data extension.
"""

import redis
import tempfile
import os
from redis_shell.extensions.data.commands import DataCommands
from redis_shell.connection_manager import ConnectionManager
from redis_shell.state_manager import StateManager


def demo_timeseries_export():
    """Demonstrate time series export functionality."""
    print("=== Redis Time Series Export/Import Demo ===\n")
    
    # Create a Redis client (assumes Redis with TimeSeries module is running)
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        r.ping()
        print("✓ Connected to Redis")
    except Exception as e:
        print(f"✗ Could not connect to Redis: {e}")
        print("Please ensure Redis with TimeSeries module is running on localhost:6379")
        return
    
    # Check if TimeSeries module is available
    try:
        # Try to create a test time series
        test_key = "demo:temperature"
        r.execute_command('TS.CREATE', test_key, 'RETENTION', '3600000', 'LABELS', 'sensor', 'temp', 'location', 'demo')
        print("✓ TimeSeries module is available")
        
        # Add some sample data
        import time
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        
        for i in range(5):
            timestamp = current_time + (i * 60000)  # Every minute
            value = 20.0 + (i * 0.5)  # Temperature values: 20.0, 20.5, 21.0, 21.5, 22.0
            r.execute_command('TS.ADD', test_key, timestamp, value)
        
        print(f"✓ Added 5 data points to {test_key}")
        
        # Verify the data
        ts_info = r.execute_command('TS.INFO', test_key)
        print(f"✓ Time series info: {len(ts_info)} fields")
        
        ts_data = r.execute_command('TS.RANGE', test_key, '-', '+')
        print(f"✓ Time series contains {len(ts_data)} data points")
        
    except Exception as e:
        print(f"✗ TimeSeries module not available or error: {e}")
        print("Please install Redis with TimeSeries module")
        return
    
    # Set up the data commands with connection manager
    connection_manager = ConnectionManager()
    connection_manager.add_connection('demo', {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    })
    connection_manager.set_current_connection_id('demo')
    
    data_commands = DataCommands()
    data_commands._connection_manager = connection_manager
    data_commands._state = StateManager()
    
    # Export the time series data
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n--- Exporting time series data ---")
        print(f"Export directory: {temp_dir}")
        
        # Run the export
        data_commands._export_thread_func('demo:*', temp_dir, False)
        
        # Find the exported file
        export_files = [f for f in os.listdir(temp_dir) if f.startswith('redis-export-')]
        if export_files:
            export_file = os.path.join(temp_dir, export_files[0])
            print(f"✓ Export file created: {export_files[0]}")
            
            # Read and display the exported content
            with open(export_file, 'r') as f:
                content = f.read()
            
            print("\n--- Exported content ---")
            print(content)
            
            # Clean up the original data
            print("\n--- Cleaning up original data ---")
            r.delete(test_key)
            print(f"✓ Deleted original key: {test_key}")
            
            # Verify it's gone
            try:
                r.execute_command('TS.INFO', test_key)
                print("✗ Key still exists!")
            except:
                print("✓ Key successfully deleted")
            
            # Import the data back
            print("\n--- Importing data back ---")
            result = data_commands._import(['--file', export_file])
            print(f"Import result: {result}")
            
            # Verify the data is back
            try:
                ts_info_after = r.execute_command('TS.INFO', test_key)
                ts_data_after = r.execute_command('TS.RANGE', test_key, '-', '+')
                print(f"✓ Time series restored with {len(ts_data_after)} data points")
                
                # Compare original and restored data
                if len(ts_data) == len(ts_data_after):
                    print("✓ Data point count matches")
                    
                    # Check if data values match
                    data_matches = True
                    for orig, restored in zip(ts_data, ts_data_after):
                        if orig[0] != restored[0] or abs(float(orig[1]) - float(restored[1])) > 0.001:
                            data_matches = False
                            break
                    
                    if data_matches:
                        print("✓ All data points match perfectly")
                    else:
                        print("⚠ Some data points differ")
                else:
                    print(f"⚠ Data point count differs: {len(ts_data)} vs {len(ts_data_after)}")
                    
            except Exception as e:
                print(f"✗ Error verifying restored data: {e}")
            
        else:
            print("✗ No export file was created")
    
    # Clean up
    try:
        r.delete(test_key)
        print(f"\n✓ Cleaned up demo key: {test_key}")
    except:
        pass
    
    print("\n=== Demo completed ===")


if __name__ == "__main__":
    demo_timeseries_export()
