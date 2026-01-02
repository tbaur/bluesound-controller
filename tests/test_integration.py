"""
Integration tests for Bluesound Controller.
"""
import pytest
import json
import os
import time
from unittest.mock import patch, MagicMock

from controller import BluesoundController
from cli import BluesoundCLI
from models import PlayerStatus


class TestIntegration:
    """Integration tests."""
    
    @pytest.fixture
    def controller(self, temp_config_dir):
        """Create controller for integration tests."""
        with patch('controller.CACHE_FILE', os.path.join(temp_config_dir, "cache.json")), \
             patch('controller.UNIFI_CACHE_FILE', os.path.join(temp_config_dir, "unifi.json")):
            return BluesoundController()
    
    @pytest.fixture
    def cli(self, controller):
        """Create CLI for integration tests."""
        return BluesoundCLI(controller)
    
    @patch('controller.BluesoundController._discover_mdns')
    @patch('controller.BluesoundController._discover_lsdp')
    def test_full_discovery_flow(self, mock_lsdp, mock_mdns, controller, temp_config_dir):
        """Test full device discovery flow."""
        # Mock discovery methods to return IPs
        mock_mdns.return_value = ['192.168.1.1']
        mock_lsdp.return_value = []
        
        # Mock cache to not exist
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            controller.discover(force_refresh=True)
        
        assert len(controller.ips) > 0
        assert '192.168.1.1' in controller.ips
    
    @patch('controller.Network.get')
    def test_status_command_flow(self, mock_network, controller, cli):
        """Test status command flow."""
        controller.ips = ['192.168.1.1']
        
        # Mock device info responses
        sync_xml = b'<sync name="Test Speaker" modelName="Node"/>'
        status_xml = b'<status><volume>50</volume><state>play</state></status>'
        mock_network.side_effect = [sync_xml, status_xml, b'<html>Uptime: 1 day</html>', None]
        
        # Should not raise exception
        cli.status()
    
    def test_volume_validation_in_cli(self, controller, cli):
        """Test volume validation in CLI."""
        from argparse import Namespace
        
        controller.ips = ['192.168.1.1']
        
        # Mock device info
        with patch.object(controller, 'get_device_info') as mock_info:
            mock_info.return_value = PlayerStatus(ip='192.168.1.1', name='Test', volume=50)
            
            args = Namespace(cmd='150', target='all')  # Invalid volume
            
            with patch('cli.Network.get'):
                # Should handle invalid volume gracefully
                cli.volume(args)
    
    def test_ip_validation_throughout_stack(self, controller):
        """Test that IP validation works throughout the stack."""
        # Invalid IP should be rejected
        status = controller.get_device_info("127.0.0.1")
        assert status.status == "invalid"
        
        # Valid IP should work (with mocked network)
        with patch('controller.Network.get') as mock_network:
            mock_network.return_value = b'<sync name="Test"/>'
            status = controller.get_device_info("192.168.1.1")
            assert status.ip == "192.168.1.1"

