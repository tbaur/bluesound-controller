"""
Additional tests for controller discovery methods.
"""
import pytest
import os
import time
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock, mock_open

from controller import BluesoundController
from constants import DISCOVERY_MDNS, DISCOVERY_LSDP, DISCOVERY_BOTH, CACHE_FILE


class TestDiscoveryMethods:
    """Test discovery method implementations."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            ctl.ips = []
            return ctl
    
    def test_discover_mdns_method(self, controller):
        """Test discovery with mDNS method."""
        controller.config.get = lambda key, default=None: {
            'DISCOVERY_METHOD': 'mdns',
            'DISCOVERY_TIMEOUT': '5'
        }.get(key, default)
        
        with patch.object(controller, '_load_discovery_cache', return_value=False):
            with patch.object(controller, '_discover_mdns', return_value=['192.168.1.100']) as mock_mdns:
                with patch.object(controller, '_discover_lsdp') as mock_lsdp:
                    controller.discover(force_refresh=True)
                    
                    mock_mdns.assert_called_once()
                    mock_lsdp.assert_not_called()
    
    def test_discover_lsdp_method(self, controller):
        """Test discovery with LSDP method."""
        controller.config.get = lambda key, default=None: {
            'DISCOVERY_METHOD': 'lsdp',
            'DISCOVERY_TIMEOUT': '5'
        }.get(key, default)
        
        with patch.object(controller, '_load_discovery_cache', return_value=False):
            with patch.object(controller, '_discover_mdns') as mock_mdns:
                with patch.object(controller, '_discover_lsdp', return_value=['192.168.1.100']) as mock_lsdp:
                    controller.discover(force_refresh=True)
                    
                    mock_lsdp.assert_called_once()
                    mock_mdns.assert_not_called()
    
    def test_discover_both_method(self, controller):
        """Test discovery with both methods."""
        controller.config.get = lambda key, default=None: {
            'DISCOVERY_METHOD': 'both',
            'DISCOVERY_TIMEOUT': '5'
        }.get(key, default)
        
        with patch.object(controller, '_load_discovery_cache', return_value=False):
            with patch.object(controller, '_discover_mdns', return_value=['192.168.1.100']) as mock_mdns:
                with patch.object(controller, '_discover_lsdp') as mock_lsdp:
                    controller.discover(force_refresh=True)
                    
                    mock_mdns.assert_called_once()
                    # LSDP should not be called if mDNS succeeds
                    mock_lsdp.assert_not_called()
    
    def test_discover_both_fallback(self, controller):
        """Test discovery with both methods, fallback to LSDP."""
        controller.config.get = lambda key, default=None: {
            'DISCOVERY_METHOD': 'both',
            'DISCOVERY_TIMEOUT': '5'
        }.get(key, default)
        
        with patch.object(controller, '_load_discovery_cache', return_value=False):
            with patch.object(controller, '_discover_mdns', return_value=[]) as mock_mdns:
                with patch.object(controller, '_discover_lsdp', return_value=['192.168.1.100']) as mock_lsdp:
                    controller.discover(force_refresh=True)
                    
                    mock_mdns.assert_called_once()
                    mock_lsdp.assert_called_once()
    
    @patch('controller.subprocess.run')
    @patch('controller.subprocess.check_output')
    def test_discover_mdns_implementation(self, mock_check, mock_run, controller):
        """Test mDNS discovery implementation."""
        mock_run.return_value = None
        mock_check.return_value = "ip_address: 192.168.1.100\n"
        mock_file = mock_open(read_data="SRV 0 0 11000 speaker.local.\n")
        with patch('builtins.open', mock_file):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    result = controller._discover_mdns(5)
                    assert isinstance(result, list)
    
    @patch('controller.subprocess.check_output')
    def test_resolve_hosts(self, mock_check, controller):
        """Test hostname resolution."""
        mock_check.return_value = "ip_address: 192.168.1.100\n"
        hosts = {'speaker.local'}
        result = controller._resolve_hosts(hosts)
        assert '192.168.1.100' in result
    
    @patch('controller.subprocess.check_output')
    def test_resolve_hosts_invalid(self, mock_check, controller):
        """Test hostname resolution with invalid hostname."""
        import subprocess
        mock_check.side_effect = subprocess.CalledProcessError(1, 'cmd')
        hosts = {'invalid-host.local'}
        result = controller._resolve_hosts(hosts)
        assert len(result) == 0
    
    @patch('controller.subprocess.run')
    def test_run_dns_sd(self, mock_run, controller):
        """Test dns-sd command execution."""
        mock_run.return_value = None
        mock_file = mock_open(read_data="SRV 0 0 11000 speaker.local.\n")
        with patch('builtins.open', mock_file):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    result = controller._run_dns_sd('_musc._tcp', 5)
                    assert isinstance(result, str)
    
    @patch('controller.subprocess.run')
    def test_run_dns_sd_timeout(self, mock_run, controller):
        """Test dns-sd command with timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('dns-sd', 5)
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    result = controller._run_dns_sd('_musc._tcp', 5)
                    assert result == ""
    
    def test_discover_validates_ips(self, controller):
        """Test that discovery validates IPs."""
        controller.config.get = lambda key, default=None: {
            'DISCOVERY_METHOD': 'mdns',
            'DISCOVERY_TIMEOUT': '5'
        }.get(key, default)
        
        with patch.object(controller, '_load_discovery_cache', return_value=False):
            with patch.object(controller, '_discover_mdns', return_value=['127.0.0.1', '192.168.1.100']):
                controller.discover(force_refresh=True)
                # Should filter out 127.0.0.1 (loopback)
                assert '127.0.0.1' not in controller.ips
                if '192.168.1.100' in controller.ips:
                    assert len(controller.ips) >= 1

