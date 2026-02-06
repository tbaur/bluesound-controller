"""
Tests for LSDP discovery module.
"""
import pytest
import socket
from unittest.mock import Mock, patch, MagicMock

from lsdp import LSDPDiscovery, LSDPDevice, LSDP_PORT, CLASS_BLUOS_PLAYER


class TestLSDPDiscovery:
    """Test LSDP discovery functionality."""
    
    def test_lsdp_device_creation(self):
        """Test LSDPDevice dataclass."""
        device = LSDPDevice(
            node_id="aa:bb:cc:dd:ee:ff",
            ip="192.168.1.100",
            class_id=CLASS_BLUOS_PLAYER,
            txt_records={"name": "Test Speaker"}
        )
        assert device.node_id == "aa:bb:cc:dd:ee:ff"
        assert device.ip == "192.168.1.100"
        assert device.class_id == CLASS_BLUOS_PLAYER
        assert device.txt_records["name"] == "Test Speaker"
    
    @patch('lsdp.time.sleep')
    @patch('socket.socket')
    def test_discover_no_devices(self, mock_socket, _mock_sleep):
        """Test discovery with no devices found."""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.recvfrom.side_effect = socket.timeout()
        
        discovery = LSDPDiscovery(timeout=1)
        result = discovery.discover()
        
        assert result == []
        mock_sock.sendto.assert_called()
    
    @patch('lsdp.time.sleep')
    @patch('socket.socket')
    def test_discover_with_devices(self, mock_socket, _mock_sleep):
        """Test discovery with devices."""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        # Mock valid LSDP announce packet
        packet = b'\x06LSDP\x01'  # Header
        packet += b'\x0A\x41'  # Announce message
        packet += b'\x06aa:bb:cc'  # Node ID
        packet += b'\x04\xc0\xa8\x01\x64'  # IPv4 address (192.168.1.100)
        packet += b'\x01'  # Count
        packet += b'\x00\x01'  # Class ID (BluOS Player)
        packet += b'\x00'  # TXT count
        
        mock_sock.recvfrom.return_value = (packet, ('192.168.1.100', LSDP_PORT))
        
        discovery = LSDPDiscovery(timeout=1)
        result = discovery.discover()
        
        assert isinstance(result, list)
    
    def test_build_query_packet(self):
        """Test query packet building."""
        discovery = LSDPDiscovery()
        packet = discovery._build_query_packet([CLASS_BLUOS_PLAYER])
        
        assert packet[0] == 6  # Header length
        assert packet[1:5] == b'LSDP'  # Magic word
        assert packet[5] == 1  # Version
        assert packet[6] > 0  # Message length
    
    def test_parse_packet_invalid_magic(self):
        """Test parsing packet with invalid magic word."""
        discovery = LSDPDiscovery()
        invalid_packet = b'\x06INVALID\x01'
        discovery._parse_packet(invalid_packet, "192.168.1.100")
        assert len(discovery.discovered_devices) == 0
    
    def test_parse_packet_too_short(self):
        """Test parsing packet that's too short."""
        discovery = LSDPDiscovery()
        short_packet = b'\x05LSDP'
        discovery._parse_packet(short_packet, "192.168.1.100")
        assert len(discovery.discovered_devices) == 0

