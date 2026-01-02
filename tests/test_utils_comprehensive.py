"""
Comprehensive tests for utils module.
"""
import pytest
import os
import json
from unittest.mock import patch, mock_open

from utils import format_bytes, format_rate, format_uptime, atomic_write, setup_logging


class TestFormatBytesComprehensive:
    """Comprehensive byte formatting tests."""
    
    def test_format_bytes_zero(self):
        """Test formatting zero bytes."""
        result = format_bytes(0)
        assert result == "0.00 B" or result == "0B"  # Accept either format
    
    def test_format_bytes_negative(self):
        """Test formatting negative bytes."""
        # format_bytes doesn't clamp negative values, it just formats them
        result = format_bytes(-1)
        assert "-1.00 B" in result or "0B" in result
    
    def test_format_bytes_large(self):
        """Test formatting very large values."""
        result = format_bytes(999999999999)
        assert "GB" in result
        assert "931" in result
    
    def test_format_bytes_precise(self):
        """Test precise byte formatting."""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1048576) == "1.00 MB"
        assert format_bytes(1073741824) == "1.00 GB"


class TestFormatRateComprehensive:
    """Comprehensive rate formatting tests."""
    
    def test_format_rate_zero(self):
        """Test formatting zero rate."""
        assert format_rate(0) == "0 bps"
    
    def test_format_rate_negative(self):
        """Test formatting negative rate."""
        # format_rate converts bytes to bits, so -1 byte = -8 bits
        assert format_rate(-1) == "-8 bps"
    
    def test_format_rate_large(self):
        """Test formatting very large rates."""
        # 999999999 bytes = 7999999992 bits ≈ 8000 Mbps
        result = format_rate(999999999)
        assert "Mbps" in result
        assert "8000" in result
    
    def test_format_rate_precise(self):
        """Test precise rate formatting."""
        # format_rate converts bytes to bits (multiplies by 8)
        assert format_rate(1000) == "8 Kbps"  # 1000 bytes = 8000 bits = 8 Kbps
        assert format_rate(1000000) == "8.00 Mbps"  # 1000000 bytes = 8000000 bits = 8 Mbps


class TestFormatUptimeComprehensive:
    """Comprehensive uptime formatting tests."""
    
    def test_format_uptime_zero(self):
        """Test formatting zero uptime."""
        assert format_uptime(0) == "0m"
    
    def test_format_uptime_seconds(self):
        """Test formatting seconds."""
        assert format_uptime(30) == "0m"
        assert format_uptime(90) == "1m"
    
    def test_format_uptime_large(self):
        """Test formatting very large uptime."""
        assert format_uptime(2592000) == "30d 0h"  # 30 days
    
    def test_format_uptime_invalid_type(self):
        """Test formatting invalid input."""
        assert format_uptime("invalid") == "N/A"
        assert format_uptime(None) == "N/A"


class TestAtomicWriteComprehensive:
    """Comprehensive atomic write tests."""
    
    def test_atomic_write_success(self, tmp_path):
        """Test successful atomic write."""
        filepath = str(tmp_path / "test.json")
        data = {"test": "value"}
        
        atomic_write(filepath, data)
        
        assert os.path.exists(filepath)
        with open(filepath, 'r') as f:
            result = json.load(f)
        assert result == data
    
    def test_atomic_write_overwrite(self, tmp_path):
        """Test atomic write overwrites existing file."""
        filepath = str(tmp_path / "test.json")
        data1 = {"old": "data"}
        data2 = {"new": "data"}
        
        atomic_write(filepath, data1)
        atomic_write(filepath, data2)
        
        with open(filepath, 'r') as f:
            result = json.load(f)
        assert result == data2
    
    @patch('builtins.open')
    @patch('os.replace')
    def test_atomic_write_handles_oserror(self, mock_replace, mock_open):
        """Test atomic write handles OSError."""
        mock_open.side_effect = OSError("Permission denied")
        filepath = "/tmp/test.json"
        data = {"test": "value"}
        
        # Should not raise exception
        atomic_write(filepath, data)
    
    @patch('builtins.open')
    @patch('os.replace')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_atomic_write_cleanup_on_error(self, mock_remove, mock_exists, mock_replace, mock_open):
        """Test atomic write cleans up temp file on error."""
        mock_open.return_value.__enter__.side_effect = OSError("Write failed")
        mock_exists.return_value = True
        
        filepath = "/tmp/test.json"
        data = {"test": "value"}
        
        atomic_write(filepath, data)
        mock_remove.assert_called()


class TestSetupLogging:
    """Test logging setup."""
    
    def test_setup_logging_debug(self):
        """Test logging setup with debug enabled."""
        logger = setup_logging(debug=True)
        assert logger.level == 10  # DEBUG
    
    def test_setup_logging_normal(self):
        """Test logging setup without debug."""
        logger = setup_logging(debug=False)
        assert logger.level == 30  # WARNING
    
    def test_setup_logging_handlers(self):
        """Test logging setup creates handlers."""
        logger = setup_logging(debug=False)
        assert len(logger.handlers) >= 1

