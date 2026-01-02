"""
Tests for utils module.
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open

from utils import format_bytes, format_rate, format_uptime, atomic_write


class TestFormatBytes:
    """Test format_bytes function."""
    
    def test_bytes(self):
        """Test byte formatting."""
        assert format_bytes(512) == "512.00 B"
        assert format_bytes(1023) == "1023.00 B"
    
    def test_kilobytes(self):
        """Test kilobyte formatting."""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1536) == "1.50 KB"
    
    def test_megabytes(self):
        """Test megabyte formatting."""
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(2.5 * 1024 * 1024) == "2.50 MB"
    
    def test_gigabytes(self):
        """Test gigabyte formatting."""
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_terabytes(self):
        """Test terabyte formatting."""
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.00 TB"


class TestFormatRate:
    """Test format_rate function."""
    
    def test_bps(self):
        """Test bits per second formatting."""
        assert format_rate(100) == "800 bps"  # 100 bytes = 800 bits
        assert format_rate(0) == "0 bps"
    
    def test_kbps(self):
        """Test kilobits per second formatting."""
        assert format_rate(1000) == "8 Kbps"  # 1000 bytes = 8000 bits = 8 Kbps
        assert format_rate(1250) == "10 Kbps"
    
    def test_mbps(self):
        """Test megabits per second formatting."""
        assert format_rate(125000) == "1.00 Mbps"  # 125000 bytes = 1 Mbps
        assert format_rate(250000) == "2.00 Mbps"


class TestFormatUptime:
    """Test format_uptime function."""
    
    def test_minutes(self):
        """Test minute formatting."""
        assert format_uptime(0) == "0m"
        assert format_uptime(30) == "0m"
        assert format_uptime(60) == "1m"
        assert format_uptime(90) == "1m"
    
    def test_hours(self):
        """Test hour formatting."""
        assert format_uptime(3600) == "1h 0m"
        assert format_uptime(3660) == "1h 1m"
        assert format_uptime(7200) == "2h 0m"
    
    def test_days(self):
        """Test day formatting."""
        assert format_uptime(86400) == "1d 0h"
        assert format_uptime(90000) == "1d 1h"
        assert format_uptime(172800) == "2d 0h"
    
    def test_invalid_input(self):
        """Test handling of invalid input."""
        assert format_uptime("invalid") == "N/A"
        assert format_uptime(None) == "N/A"
        assert format_uptime(-1) == "0m"


class TestAtomicWrite:
    """Test atomic_write function."""
    
    def test_writes_file(self, temp_config_dir):
        """Test that file is written atomically."""
        test_file = os.path.join(temp_config_dir, "test.json")
        test_data = {"key": "value", "number": 42}
        
        atomic_write(test_file, test_data)
        
        assert os.path.exists(test_file)
        with open(test_file, 'r') as f:
            loaded = json.load(f)
        assert loaded == test_data
    
    def test_atomic_operation(self, temp_config_dir):
        """Test that write is atomic (no partial files)."""
        test_file = os.path.join(temp_config_dir, "test.json")
        test_data = {"key": "value"}
        
        atomic_write(test_file, test_data)
        
        # Should not have .tmp file after completion
        assert not os.path.exists(f"{test_file}.tmp")
        assert os.path.exists(test_file)
    
    def test_handles_errors(self, temp_config_dir):
        """Test error handling."""
        # Write to non-existent directory should fail gracefully
        invalid_file = os.path.join(temp_config_dir, "nonexistent", "test.json")
        test_data = {"key": "value"}
        
        # Should not raise exception
        atomic_write(invalid_file, test_data)
        
        # File should not exist
        assert not os.path.exists(invalid_file)

