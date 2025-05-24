import unittest
from unittest.mock import patch
import sys
import os

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from azureaiproxy.cli import main
import azureaiproxy.cli as cli_module


class TestLoggingArgs(unittest.TestCase):
    
    def setUp(self):
        # Reset global variables before each test
        cli_module.LOG_HEADERS = False
        cli_module.LOG_BODIES = False
    
    @patch('sys.argv', ['cli.py', '--port', '8001'])
    @patch('azureaiproxy.cli.web')
    @patch('azureaiproxy.cli.asyncio')
    def test_default_logging_disabled(self, mock_asyncio, mock_web):
        """Test that logging is disabled by default"""
        with patch('azureaiproxy.cli.logger'):
            try:
                main()
            except SystemExit:
                pass
        
        self.assertFalse(cli_module.LOG_HEADERS)
        self.assertFalse(cli_module.LOG_BODIES)
    
    @patch('sys.argv', ['cli.py', '--port', '8002', '--log-headers'])
    @patch('azureaiproxy.cli.web')
    @patch('azureaiproxy.cli.asyncio')
    def test_headers_logging_enabled(self, mock_asyncio, mock_web):
        """Test that header logging can be enabled"""
        with patch('azureaiproxy.cli.logger'):
            try:
                main()
            except SystemExit:
                pass
        
        self.assertTrue(cli_module.LOG_HEADERS)
        self.assertFalse(cli_module.LOG_BODIES)
    
    @patch('sys.argv', ['cli.py', '--port', '8003', '--log-bodies'])
    @patch('azureaiproxy.cli.web')
    @patch('azureaiproxy.cli.asyncio')
    def test_bodies_logging_enabled(self, mock_asyncio, mock_web):
        """Test that body logging can be enabled"""
        with patch('azureaiproxy.cli.logger'):
            try:
                main()
            except SystemExit:
                pass
        
        self.assertFalse(cli_module.LOG_HEADERS)
        self.assertTrue(cli_module.LOG_BODIES)
    
    @patch('sys.argv', ['cli.py', '--port', '8004', '--log-headers', '--log-bodies'])
    @patch('azureaiproxy.cli.web')
    @patch('azureaiproxy.cli.asyncio')
    def test_both_logging_enabled(self, mock_asyncio, mock_web):
        """Test that both header and body logging can be enabled"""
        with patch('azureaiproxy.cli.logger'):
            try:
                main()
            except SystemExit:
                pass
        
        self.assertTrue(cli_module.LOG_HEADERS)
        self.assertTrue(cli_module.LOG_BODIES)


if __name__ == '__main__':
    unittest.main()