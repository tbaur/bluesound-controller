"""
Tests for network module.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from urllib.error import URLError, HTTPError

from network import Network


class TestNetwork:
    """Test Network class."""
    
    @patch('urllib.request.urlopen')
    def test_successful_get_request(self, mock_urlopen):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"test response"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result == b"test response"
        mock_urlopen.assert_called_once()
    
    @patch('urllib.request.urlopen')
    def test_successful_post_request(self, mock_urlopen):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"post response"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = Network.post("http://192.168.1.1/test", data={"key": "value"})
        
        assert result == b"post response"
        mock_urlopen.assert_called_once()
    
    @patch('utils.time.sleep')
    @patch('urllib.request.urlopen')
    def test_handles_timeout(self, mock_urlopen, _mock_sleep):
        """Test handling of timeout."""
        mock_urlopen.side_effect = TimeoutError()
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result is None
    
    @patch('utils.time.sleep')
    @patch('urllib.request.urlopen')
    def test_handles_connection_error(self, mock_urlopen, _mock_sleep):
        """Test handling of connection error."""
        mock_urlopen.side_effect = ConnectionError()
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result is None
    
    @patch('utils.time.sleep')
    @patch('urllib.request.urlopen')
    def test_handles_http_error(self, mock_urlopen, _mock_sleep):
        """Test handling of HTTP error."""
        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result is None
    
    @patch('utils.time.sleep')
    @patch('urllib.request.urlopen')
    def test_handles_url_error(self, mock_urlopen, _mock_sleep):
        """Test handling of URL error."""
        mock_urlopen.side_effect = URLError("Connection refused")
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result is None
    
    def test_rejects_invalid_url_scheme(self):
        """Test that invalid URL schemes are rejected."""
        result = Network.get("file:///etc/passwd")
        assert result is None
        
        result = Network.get("javascript:alert(1)")
        assert result is None
    
    @patch('urllib.request.urlopen')
    def test_enforces_size_limit(self, mock_urlopen):
        """Test that size limit is enforced."""
        from constants import MAX_XML_SIZE
        mock_response = MagicMock()
        mock_response.read.return_value = b"x" * (MAX_XML_SIZE + 1)
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = Network.get("http://192.168.1.1/test")
        
        assert result is None
    
    @patch('urllib.request.urlopen')
    def test_custom_timeout(self, mock_urlopen):
        """Test custom timeout."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"response"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        Network.get("http://192.168.1.1/test", timeout=10)
        
        call_args = mock_urlopen.call_args
        assert 'timeout' in call_args.kwargs
        assert call_args.kwargs['timeout'] == 10

