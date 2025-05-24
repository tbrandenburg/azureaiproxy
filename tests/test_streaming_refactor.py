import unittest
from unittest.mock import patch, AsyncMock
import asyncio
import json
import sys
import os

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from azureaiproxy.cli import _process_stream_line, _process_data_line, _process_regular_line, _process_stream_done_line
import azureaiproxy.cli as cli_module


class TestStreamingRefactor(unittest.TestCase):

    def setUp(self):
        # Reset global variables before each test
        cli_module.LOG_HEADERS = False
        cli_module.LOG_BODIES = False

    async def test_process_stream_done_line(self):
        """Test that stream done line is processed correctly"""
        mock_response = AsyncMock()

        result = await _process_stream_done_line(mock_response)

        mock_response.write.assert_called_once_with(b"data: [DONE]\n\n")
        mock_response.write_eof.assert_called_once()
        self.assertEqual(result, mock_response)

    async def test_process_data_line_valid_json(self):
        """Test processing valid JSON data line"""
        mock_response = AsyncMock()
        payload = {"choices": [{"delta": {"content": "test"}}]}
        payload_str = json.dumps(payload)

        await _process_data_line(mock_response, payload_str)

        mock_response.write.assert_called_once()
        written_data = mock_response.write.call_args[0][0].decode('utf-8')
        self.assertTrue(written_data.startswith("data: "))
        self.assertTrue("test" in written_data)

    async def test_process_data_line_empty_choices(self):
        """Test processing data line with empty choices"""
        mock_response = AsyncMock()
        payload = {"choices": []}
        payload_str = json.dumps(payload)

        await _process_data_line(mock_response, payload_str)

        # Should not write anything for empty choices
        mock_response.write.assert_not_called()

    async def test_process_data_line_invalid_json(self):
        """Test processing invalid JSON data line"""
        mock_response = AsyncMock()
        invalid_json = "invalid json"

        with patch('azureaiproxy.cli.logger') as mock_logger:
            await _process_data_line(mock_response, invalid_json)

        mock_logger.error.assert_called_once()
        mock_response.write.assert_called_once()
        written_data = mock_response.write.call_args[0][0].decode('utf-8')
        self.assertTrue("[ERROR]" in written_data)

    async def test_process_regular_line(self):
        """Test processing regular line"""
        mock_response = AsyncMock()
        test_line = "test line"

        await _process_regular_line(mock_response, test_line)

        mock_response.write.assert_called_once()
        written_data = mock_response.write.call_args[0][0].decode('utf-8')
        self.assertEqual(written_data, "test line\n\n")

    async def test_process_stream_line_done(self):
        """Test processing done line through main processor"""
        mock_response = AsyncMock()

        result = await _process_stream_line(mock_response, "data: [DONE]")

        self.assertEqual(result, mock_response)
        mock_response.write.assert_called_with(b"data: [DONE]\n\n")

    async def test_process_stream_line_data(self):
        """Test processing data line through main processor"""
        mock_response = AsyncMock()
        payload = {"choices": [{"delta": {"content": "test"}}]}
        line = f"data: {json.dumps(payload)}"

        result = await _process_stream_line(mock_response, line)

        self.assertIsNone(result)
        mock_response.write.assert_called_once()

    async def test_process_stream_line_regular(self):
        """Test processing regular line through main processor"""
        mock_response = AsyncMock()

        result = await _process_stream_line(mock_response, "regular line")

        self.assertIsNone(result)
        mock_response.write.assert_called_once()

    async def test_process_stream_line_empty(self):
        """Test processing empty line"""
        mock_response = AsyncMock()

        result = await _process_stream_line(mock_response, "")

        self.assertIsNone(result)
        mock_response.write.assert_not_called()

    def test_logging_enabled_data_line(self):
        """Test that body logging works for data lines"""
        cli_module.LOG_BODIES = True

        async def run_test():
            mock_response = AsyncMock()
            payload = {"choices": [{"delta": {"content": "test"}}]}
            payload_str = json.dumps(payload)

            with patch('azureaiproxy.cli.logger') as mock_logger:
                await _process_data_line(mock_response, payload_str)

            mock_logger.debug.assert_called_once()
            debug_call_args = mock_logger.debug.call_args[0][0]
            self.assertTrue("Azure stream chunk:" in debug_call_args)

        asyncio.run(run_test())

    def test_logging_enabled_regular_line(self):
        """Test that body logging works for regular lines"""
        cli_module.LOG_BODIES = True

        async def run_test():
            mock_response = AsyncMock()

            with patch('azureaiproxy.cli.logger') as mock_logger:
                await _process_regular_line(mock_response, "test line")

            mock_logger.debug.assert_called_once()
            debug_call_args = mock_logger.debug.call_args[0][0]
            self.assertTrue("Azure stream line:" in debug_call_args)

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
