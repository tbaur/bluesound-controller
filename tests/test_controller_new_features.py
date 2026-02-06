"""
Tests for new controller features (playback, queue, inputs, etc.).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from controller import BluesoundController
from models import PlayerStatus
from constants import BLUOS_PORT


class TestPlaybackControls:
    """Test playback control methods."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            ctl.ips = ["192.168.1.100"]
            return ctl
    
    @patch('controller.Network')
    def test_play(self, mock_network, controller):
        """Test play command."""
        mock_network.get.return_value = b"OK"
        result = controller.play("192.168.1.100")
        assert result is True
        mock_network.get.assert_called_once()
        call_url = mock_network.get.call_args[0][0]
        assert f"http://192.168.1.100:{BLUOS_PORT}/Play" in call_url
    
    @patch('controller.Network')
    def test_pause_device(self, mock_network, controller):
        """Test pause command."""
        mock_network.get.return_value = b"OK"
        result = controller.pause_device("192.168.1.100")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "/Pause" in call_url
    
    @patch('controller.Network')
    def test_stop(self, mock_network, controller):
        """Test stop command."""
        mock_network.get.return_value = b"OK"
        result = controller.stop("192.168.1.100")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "/Stop" in call_url
    
    @patch('controller.Network')
    def test_skip(self, mock_network, controller):
        """Test skip command."""
        mock_network.get.return_value = b"OK"
        result = controller.skip("192.168.1.100")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "/Skip" in call_url
    
    @patch('controller.Network')
    def test_previous(self, mock_network, controller):
        """Test previous command."""
        mock_network.get.return_value = b"OK"
        result = controller.previous("192.168.1.100")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "/Back" in call_url
    
    def test_play_invalid_ip(self, controller):
        """Test play with invalid IP."""
        result = controller.play("invalid")
        assert result is False


class TestQueueManagement:
    """Test queue management methods."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            return ctl
    
    @patch('controller.Network')
    def test_get_queue(self, mock_network, controller):
        """Test getting queue."""
        xml_content = b"""<?xml version="1.0"?>
        <queue>
            <item>
                <title>Test Song</title>
                <artist>Test Artist</artist>
                <album>Test Album</album>
            </item>
        </queue>"""
        mock_network.get.return_value = xml_content
        
        with patch.object(controller, '_safe_parse_xml') as mock_parse:
            mock_root = MagicMock()
            mock_item = MagicMock()
            mock_item.findtext.side_effect = lambda x, default='': {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'image': '',
                'service': ''
            }.get(x, default)
            mock_root.findall.return_value = [mock_item]
            mock_parse.return_value = mock_root
            
            result = controller.get_queue("192.168.1.100")
            assert result is not None
            assert result['count'] == 1
    
    @patch('controller.Network')
    def test_clear_queue(self, mock_network, controller):
        """Test clearing queue."""
        mock_network.get.return_value = b"OK"
        result = controller.clear_queue("192.168.1.100")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "clear=1" in call_url
    
    @patch('controller.Network')
    def test_move_queue_item(self, mock_network, controller):
        """Test moving queue item."""
        mock_network.get.return_value = b"OK"
        result = controller.move_queue_item("192.168.1.100", 3, 1)
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "move=3" in call_url
        assert "to=1" in call_url


class TestInputManagement:
    """Test input management methods."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            return ctl
    
    @patch('controller.Network')
    def test_get_inputs(self, mock_network, controller):
        """Test getting inputs."""
        xml_content = b"""<?xml version="1.0"?>
        <inputs>
            <input selected="1">
                <name>Bluetooth</name>
                <type>bluetooth</type>
            </input>
        </inputs>"""
        mock_network.get.return_value = xml_content
        
        with patch.object(controller, '_safe_parse_xml') as mock_parse:
            mock_root = MagicMock()
            mock_input = MagicMock()
            mock_input.findtext.side_effect = lambda x, default='': {
                'name': 'Bluetooth',
                'type': 'bluetooth'
            }.get(x, default)
            mock_input.get.return_value = '1'
            mock_root.findall.return_value = [mock_input]
            mock_parse.return_value = mock_root
            
            result = controller.get_inputs("192.168.1.100")
            assert result is not None
            assert len(result) == 1
            assert result[0]['name'] == 'Bluetooth'
    
    @patch('controller.Network')
    def test_set_input(self, mock_network, controller):
        """Test setting input."""
        mock_network.get.return_value = b"OK"
        result = controller.set_input("192.168.1.100", "Bluetooth")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "AudioInput" in call_url


class TestBluetoothControl:
    """Test Bluetooth mode control."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            return ctl
    
    @patch('controller.Network')
    def test_get_bluetooth_mode(self, mock_network, controller):
        """Test getting Bluetooth mode."""
        xml_content = b"""<?xml version="1.0"?>
        <audioModes>
            <bluetoothAutoplay>1</bluetoothAutoplay>
        </audioModes>"""
        mock_network.get.return_value = xml_content
        
        with patch.object(controller, '_safe_parse_xml') as mock_parse:
            mock_root = MagicMock()
            mock_root.findtext.return_value = '1'
            mock_parse.return_value = mock_root
            
            result = controller.get_bluetooth_mode("192.168.1.100")
            assert result == "Automatic"
    
    @patch('controller.Network')
    def test_set_bluetooth_mode(self, mock_network, controller):
        """Test setting Bluetooth mode."""
        mock_network.get.return_value = b"OK"
        result = controller.set_bluetooth_mode("192.168.1.100", 1)
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "bluetoothAutoplay=1" in call_url
    
    def test_set_bluetooth_mode_invalid(self, controller):
        """Test setting invalid Bluetooth mode."""
        result = controller.set_bluetooth_mode("192.168.1.100", 99)
        assert result is False


class TestPresetManagement:
    """Test preset management."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            return ctl
    
    @patch('controller.Network')
    def test_get_presets(self, mock_network, controller):
        """Test getting presets."""
        xml_content = b"""<?xml version="1.0"?>
        <presets>
            <preset id="1">
                <name>Preset 1</name>
            </preset>
        </presets>"""
        mock_network.get.return_value = xml_content
        
        with patch.object(controller, '_safe_parse_xml') as mock_parse:
            mock_root = MagicMock()
            mock_preset = MagicMock()
            mock_preset.get.return_value = '1'
            mock_preset.findtext.return_value = 'Preset 1'
            mock_root.findall.return_value = [mock_preset]
            mock_parse.return_value = mock_root
            
            result = controller.get_presets("192.168.1.100")
            assert result is not None
            assert len(result) == 1
    
    @patch('controller.Network')
    def test_play_preset(self, mock_network, controller):
        """Test playing preset."""
        mock_network.get.return_value = b"OK"
        result = controller.play_preset("192.168.1.100", 1)
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "Preset?id=1" in call_url


class TestSyncGroups:
    """Test sync group management."""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        with patch('controller.Config'):
            ctl = BluesoundController()
            return ctl
    
    @patch('controller.Network')
    def test_add_sync_slave(self, mock_network, controller):
        """Test adding sync slave."""
        mock_network.get.return_value = b"OK"
        result = controller.add_sync_slave("192.168.1.100", "192.168.1.101")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "Sync?slave=" in call_url
    
    @patch('controller.Network')
    def test_remove_sync_slave(self, mock_network, controller):
        """Test removing sync slave."""
        mock_network.get.return_value = b"OK"
        result = controller.remove_sync_slave("192.168.1.100", "192.168.1.101")
        assert result is True
        call_url = mock_network.get.call_args[0][0]
        assert "Sync?remove=" in call_url

