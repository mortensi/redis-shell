import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from redis_shell.extensions.data.commands import DataCommands
from redis_shell.state_manager import StateManager


class TestDataExtension:
    """Test the data extension functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.data_commands = DataCommands()
        self.data_commands._state = StateManager()
        
    def test_tsdb_export_functionality(self):
        """Test that TSDB-TYPE keys are properly exported."""
        # Mock Redis client
        mock_redis = Mock()

        # Mock basic Redis methods
        mock_redis.type.return_value = 'TSDB-TYPE'
        mock_redis.keys.return_value = [b'test:temperature']
        mock_redis.dbsize.return_value = 1
        mock_redis.info.return_value = {
            'redis_version': '7.0.0',
            'redis_mode': 'standalone',
            'db0': {'keys': 1}
        }
        mock_redis.connection_pool.connection_kwargs = {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }

        # Mock TS.INFO response (Redis Time Series info format)
        mock_ts_info = [
            b'totalSamples', 3,
            b'memoryUsage', 4184,
            b'firstTimestamp', 1642680000000,
            b'lastTimestamp', 1642680120000,
            b'retentionTime', 86400000,  # 24 hours in milliseconds
            b'chunkCount', 1,
            b'chunkSize', 4096,
            b'chunkType', b'compressed',
            b'duplicatePolicy', b'',
            b'labels', [b'sensor', b'temperature', b'location', b'room1']
        ]

        # Mock TS.RANGE response (timestamp, value pairs)
        mock_ts_data = [
            [1642680000000, b'23.5'],
            [1642680060000, b'24.1'],
            [1642680120000, b'23.8']
        ]

        # Configure mock responses
        mock_redis.execute_command.side_effect = lambda cmd, *args: {
            ('TS.INFO', b'test:temperature'): mock_ts_info,
            ('TS.RANGE', b'test:temperature', '-', '+'): mock_ts_data
        }.get((cmd, *args), None)
        
        # Mock connection manager
        mock_connection_manager = Mock()
        mock_connection_manager.get_redis_client.return_value = mock_redis
        mock_connection_manager.get_connection_parameters.return_value = ('localhost', 6379, 0, None)
        mock_connection_manager.is_cluster_connection.return_value = False
        self.data_commands._connection_manager = mock_connection_manager
        
        # Create a temporary directory for export
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test export directly using the thread function
            self.data_commands._export_thread_func('*', temp_dir, False)

            # Find the exported file
            export_files = [f for f in os.listdir(temp_dir) if f.startswith('redis-export-')]
            assert len(export_files) == 1

            # Read the exported file
            export_file_path = os.path.join(temp_dir, export_files[0])
            with open(export_file_path, 'r') as f:
                content = f.read()

            # Verify the content contains time series commands
            assert 'TS.CREATE "test:temperature"' in content
            assert 'RETENTION 86400000' in content
            assert 'LABELS sensor temperature location room1' in content
            assert 'TS.ADD "test:temperature" 1642680000000 23.5' in content
            assert 'TS.ADD "test:temperature" 1642680060000 24.1' in content
            assert 'TS.ADD "test:temperature" 1642680120000 23.8' in content
            
    def test_tsdb_import_functionality(self):
        """Test that time series commands are properly imported."""
        # Mock Redis client
        mock_redis = Mock()
        
        # Mock connection manager
        mock_connection_manager = Mock()
        mock_connection_manager.get_redis_client.return_value = mock_redis
        mock_connection_manager.get_connection_parameters.return_value = ('localhost', 6379, 0, None)
        mock_connection_manager.is_cluster_connection.return_value = False
        self.data_commands._connection_manager = mock_connection_manager
        
        # Create a temporary file with time series commands
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write('TS.CREATE "test:temperature" RETENTION 86400000 LABELS sensor temperature location room1\n')
            temp_file.write('TS.ADD "test:temperature" 1642680000000 23.5\n')
            temp_file.write('TS.ADD "test:temperature" 1642680060000 24.1\n')
            temp_file.write('TS.ADD "test:temperature" 1642680120000 23.8\n')
            temp_file_path = temp_file.name
        
        try:
            # Test import
            result = self.data_commands._import(['--file', temp_file_path])
            
            # Check that import was successful
            assert "Import completed" in result
            assert "4 commands executed successfully" in result
            
            # Verify that the correct commands were executed
            expected_calls = [
                ('TS.CREATE', 'test:temperature', 'RETENTION', '86400000', 'LABELS', 'sensor', 'temperature', 'location', 'room1'),
                ('TS.ADD', 'test:temperature', '1642680000000', '23.5'),
                ('TS.ADD', 'test:temperature', '1642680060000', '24.1'),
                ('TS.ADD', 'test:temperature', '1642680120000', '23.8')
            ]
            
            # Check that execute_command was called with the right arguments
            assert mock_redis.execute_command.call_count == 4
            for i, expected_call in enumerate(expected_calls):
                actual_call = mock_redis.execute_command.call_args_list[i]
                assert actual_call[0] == expected_call
                
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
    def test_unsupported_type_handling(self):
        """Test that unsupported types are handled gracefully."""
        # Mock Redis client
        mock_redis = Mock()

        # Mock basic Redis methods
        mock_redis.type.return_value = 'UNKNOWN-TYPE'
        mock_redis.keys.return_value = [b'test:unknown']
        mock_redis.dbsize.return_value = 1
        mock_redis.info.return_value = {
            'redis_version': '7.0.0',
            'redis_mode': 'standalone',
            'db0': {'keys': 1}
        }
        mock_redis.connection_pool.connection_kwargs = {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }
        
        # Mock connection manager
        mock_connection_manager = Mock()
        mock_connection_manager.get_redis_client.return_value = mock_redis
        mock_connection_manager.get_connection_parameters.return_value = ('localhost', 6379, 0, None)
        mock_connection_manager.is_cluster_connection.return_value = False
        self.data_commands._connection_manager = mock_connection_manager
        
        # Create a temporary directory for export
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test export directly using the thread function
            self.data_commands._export_thread_func('*', temp_dir, False)

            # Find the exported file
            export_files = [f for f in os.listdir(temp_dir) if f.startswith('redis-export-')]
            assert len(export_files) == 1

            # Read the exported file
            export_file_path = os.path.join(temp_dir, export_files[0])
            with open(export_file_path, 'r') as f:
                content = f.read()

            # Verify the content contains the unsupported type comment
            assert '# Unsupported type UNKNOWN-TYPE for key "test:unknown"' in content
