"""
Tests for CLI multi-device support functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from cli import BluesoundCLI
from controller import BluesoundController
from models import PlayerStatus


class TestMultiDeviceSupport:
    """Test multi-device support in CLI commands."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance with multiple devices."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            ctl.ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
            return ctl
    
    @pytest.fixture
    def cli(self, controller):
        """Create CLI instance."""
        return BluesoundCLI(controller)
    
    @pytest.fixture
    def mock_devices(self):
        """Create mock device statuses."""
        return [
            PlayerStatus(ip="192.168.1.100", name="Living Room"),
            PlayerStatus(ip="192.168.1.101", name="Kitchen"),
            PlayerStatus(ip="192.168.1.102", name="Bedroom"),
        ]
    
    def test_get_matching_devices_all(self, cli, mock_devices):
        """Test getting all devices when no target specified."""
        with patch.object(cli.ctl, 'get_device_info') as mock_info:
            mock_info.side_effect = mock_devices
            devices = cli._get_matching_devices(None)
            assert len(devices) == 3
            assert all(d.name in ["Living Room", "Kitchen", "Bedroom"] for d in devices)
    
    def test_get_matching_devices_specific(self, cli, mock_devices):
        """Test getting specific device by exact name."""
        with patch.object(cli.ctl, 'get_device_info') as mock_info:
            mock_info.side_effect = mock_devices
            devices = cli._get_matching_devices("Living Room")
            assert len(devices) == 1
            assert devices[0].name == "Living Room"
    
    def test_get_matching_devices_pattern(self, cli, mock_devices):
        """Test getting devices by pattern match."""
        with patch.object(cli.ctl, 'get_device_info') as mock_info:
            mock_info.side_effect = mock_devices
            devices = cli._get_matching_devices("Room")
            assert len(devices) == 2
            device_names = [d.name for d in devices]
            assert "Living Room" in device_names
            assert "Bedroom" in device_names
            assert "Kitchen" not in device_names
    
    def test_get_matching_devices_no_match(self, cli, mock_devices):
        """Test getting devices with no match."""
        with patch.object(cli.ctl, 'get_device_info') as mock_info:
            mock_info.side_effect = mock_devices
            devices = cli._get_matching_devices("Office")
            assert len(devices) == 0
    
    @patch('cli.Network')
    def test_play_all_devices(self, mock_network, cli, mock_devices):
        """Test play command on all devices."""
        mock_network.get.return_value = b"OK"
        args = Namespace(target=None)
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'play', return_value=True) as mock_play:
                cli.play(args)
                assert mock_play.call_count == 3
    
    @patch('cli.Network')
    def test_play_specific_device(self, mock_network, cli, mock_devices):
        """Test play command on specific device."""
        mock_network.get.return_value = b"OK"
        args = Namespace(target="Living Room")
        matching = [d for d in mock_devices if d.name == "Living Room"]
        
        with patch.object(cli, '_get_matching_devices', return_value=matching):
            with patch.object(cli.ctl, 'play', return_value=True) as mock_play:
                cli.play(args)
                assert mock_play.call_count == 1
                mock_play.assert_called_with("192.168.1.100")
    
    @patch('cli.Network')
    def test_queue_clear_all_devices(self, mock_network, cli, mock_devices):
        """Test queue clear on all devices."""
        args = Namespace(target=None, action='clear', from_index=None, to_index=None)
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'clear_queue', return_value=True) as mock_clear:
                cli.queue(args)
                assert mock_clear.call_count == 3
    
    @patch('cli.Network')
    def test_inputs_set_all_devices(self, mock_network, cli, mock_devices):
        """Test setting input on all devices."""
        args = Namespace(target=None, input="Bluetooth")
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'set_input', return_value=True) as mock_set:
                cli.inputs(args)
                assert mock_set.call_count == 3
                # Verify all calls were with "Bluetooth"
                for call in mock_set.call_args_list:
                    assert call[0][1] == "Bluetooth"
    
    @patch('cli.Network')
    def test_bluetooth_set_all_devices(self, mock_network, cli, mock_devices):
        """Test setting Bluetooth mode on all devices."""
        args = Namespace(target=None, mode="auto")
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'set_bluetooth_mode', return_value=True) as mock_set:
                cli.bluetooth(args)
                assert mock_set.call_count == 3
                # Verify all calls were with mode 1 (auto)
                for call in mock_set.call_args_list:
                    assert call[0][1] == 1
    
    @patch('cli.Network')
    def test_presets_play_all_devices(self, mock_network, cli, mock_devices):
        """Test playing preset on all devices."""
        args = Namespace(target=None, preset_id=1)
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'play_preset', return_value=True) as mock_play:
                cli.presets(args)
                assert mock_play.call_count == 3
                # Verify all calls were with preset ID 1
                for call in mock_play.call_args_list:
                    assert call[0][1] == 1
    
    @patch('cli.Network')
    def test_reboot_with_target(self, mock_network, cli, mock_devices):
        """Test reboot with device target."""
        matching = [d for d in mock_devices if d.name == "Living Room"]
        args = Namespace(target="Living Room")
        
        with patch.object(cli, '_get_matching_devices', return_value=matching):
            with patch('builtins.input', return_value='y'):
                with patch('cli.Network.post', return_value=b"OK") as mock_post:
                    cli.reboot(args)
                    assert mock_post.call_count == 1
    
    def test_queue_show_all_devices(self, cli, mock_devices):
        """Test showing queue for all devices."""
        args = Namespace(target=None, action='show', from_index=None, to_index=None)
        
        queue_data = {
            'items': [
                {'title': 'Song 1', 'artist': 'Artist 1', 'album': 'Album 1'}
            ],
            'count': 1
        }
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'get_queue', return_value=queue_data):
                # Should not raise exception
                cli.queue(args)
    
    def test_inputs_list_all_devices(self, cli, mock_devices):
        """Test listing inputs for all devices."""
        args = Namespace(target=None, input=None)
        
        inputs_data = [
            {'name': 'Bluetooth', 'type': 'bluetooth', 'selected': True},
            {'name': 'Optical', 'type': 'optical', 'selected': False}
        ]
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'get_inputs', return_value=inputs_data):
                # Should not raise exception
                cli.inputs(args)
    
    def test_bluetooth_list_all_devices(self, cli, mock_devices):
        """Test listing Bluetooth mode for all devices."""
        args = Namespace(target=None, mode=None)
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'get_bluetooth_mode', return_value="Automatic"):
                # Should not raise exception
                cli.bluetooth(args)
    
    def test_presets_list_all_devices(self, cli, mock_devices):
        """Test listing presets for all devices."""
        args = Namespace(target=None, preset_id=None)
        
        presets_data = [
            {'id': '1', 'name': 'Preset 1', 'image': ''},
            {'id': '2', 'name': 'Preset 2', 'image': ''}
        ]
        
        with patch.object(cli, '_get_matching_devices', return_value=mock_devices):
            with patch.object(cli.ctl, 'get_presets', return_value=presets_data):
                # Should not raise exception
                cli.presets(args)

