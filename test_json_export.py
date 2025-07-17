#!/usr/bin/env python3

import redis
import sys
import os
import json

# Add the project root to the path
sys.path.insert(0, '/Users/mortensi/workspace/redis-shell')

from redis_shell.extensions.data.commands import DataCommands

def test_json_export():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Clear any existing test data
    print("Clearing existing test data...")
    for key in r.scan_iter(match='json_test:*'):
        r.delete(key)
    
    # Add some JSON test data (similar to the problematic one)
    print("Adding JSON test data...")
    try:
        test_data = {
            "name": "SignalR",
            "url": "https://dotnet.microsoft.com/en-us/apps/aspnet/signalr",
            "repository": "https://github.com/SignalR/SignalR",
            "description": "ASP.NET SignalR is a library for ASP.NET developers that makes it incredibly simple to add real-time web functionality to your applications. What is \"real-time web\" functionality? It's the ability to have your server-side code push content to the connected clients as it happens, in real-time.",
            "notes": "",
            "updated_at": 1720737988,
            "created_at": 1720371405,
            "github_stars": 9203,
            "logo": " https://storage.googleapis.com/assets-prod-learn-redis-com/signalr-logo.png ",
            "so_questions": 9752,
            "slogan": "Library for ASP.NET developers that makes it incredibly simple to add real-time web functionality to your applications",
            "so_tag": "signalr",
            "usecase": ["cache", "lock", "session"],
            "language": ["csharp"],
            "score": 0.05093783274808725
        }
        
        # Set JSON data
        r.json().set('json_test:signalr', '$', test_data)
        
        # Add another simpler JSON for comparison
        simple_data = {"key": "value", "number": 42, "array": [1, 2, 3]}
        r.json().set('json_test:simple', '$', simple_data)
        
        print("JSON data added successfully")
    except Exception as e:
        print(f"Error adding JSON data (Redis might not have JSON module): {e}")
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
    
    # Export the JSON data
    print("Testing JSON export...")
    result = data_commands._export(['--folder', '/tmp', '--pattern', 'json_test:*'])
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
    
    # Clear the original data
    print("Clearing original JSON data...")
    for key in r.scan_iter(match='json_test:*'):
        r.delete(key)
    
    # Import the data back
    print("Testing JSON import...")
    import_result = data_commands._import(['--file', latest_file])
    print(f"Import result: {import_result}")
    
    # Verify the imported data
    print("Verifying imported JSON data...")
    try:
        imported_signalr = r.json().get('json_test:signalr')
        imported_simple = r.json().get('json_test:simple')
        
        print(f"Imported SignalR data: {json.dumps(imported_signalr, indent=2)}")
        print(f"Imported simple data: {imported_simple}")
        
        # Compare with original
        print(f"Data matches original: {imported_signalr == test_data}")
        
    except Exception as e:
        print(f"Error verifying imported data: {e}")

if __name__ == '__main__':
    test_json_export()
