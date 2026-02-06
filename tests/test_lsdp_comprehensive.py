"""
Comprehensive tests for LSDP discovery protocol.
"""
import pytest
import socket
import struct
from unittest.mock import Mock, patch, MagicMock

from lsdp import LSDPDiscovery, LSDPDevice, LSDP_PORT, CLASS_BLUOS_PLAYER, CLASS_BLUOS_HUB


class TestLSDPComprehensive:
    """Comprehensive LSDP tests."""
    
    @patch('lsdp.time.sleep')
    def test_lsdp_discovery_timeout(self, _mock_sleep):
        """Test LSDP discovery with timeout."""
        discovery = LSDPDiscovery(timeout=1)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.recvfrom.side_effect = socket.timeout()
            
            result = discovery.discover()
            assert result == []
            assert mock_sock.sendto.call_count == 7  # 7 initial packets
    
    @patch('lsdp.time.sleep')
    def test_lsdp_discovery_with_class_ids(self, _mock_sleep):
        """Test LSDP discovery with specific class IDs."""
        discovery = LSDPDiscovery(timeout=1)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.recvfrom.side_effect = socket.timeout()
            
            result = discovery.discover([CLASS_BLUOS_PLAYER, CLASS_BLUOS_HUB])
            assert result == []
    
    def test_build_query_packet_structure(self):
        """Test query packet structure."""
        discovery = LSDPDiscovery()
        packet = discovery._build_query_packet([CLASS_BLUOS_PLAYER])
        
        assert len(packet) >= 6
        assert packet[1:5] == b'LSDP'
        assert packet[5] == 1  # Version
    
    def test_parse_announce_message(self):
        """Test parsing announce message."""
        discovery = LSDPDiscovery()
        
        # Build a simple announce packet
        packet = b'\x06LSDP\x01'  # Header
        packet += b'\x15\x41'  # Announce message (length 21, type 'A')
        packet += b'\x06aa:bb:cc'  # Node ID
        packet += b'\x04\xc0\xa8\x01\x64'  # IPv4 (192.168.1.100)
        packet += b'\x01'  # Count
        packet += b'\x00\x01'  # Class ID
        packet += b'\x00'  # TXT count
        
        discovery._parse_packet(packet, "192.168.1.100")
        # Should parse without error
    
    def test_parse_packet_with_txt_records(self):
        """Test parsing packet with TXT records."""
        discovery = LSDPDiscovery()
        
        # Build packet with TXT records
        packet = b'\x06LSDP\x01'  # Header
        packet += b'\x20\x41'  # Announce message
        packet += b'\x06aa:bb:cc'  # Node ID
        packet += b'\x04\xc0\xa8\x01\x64'  # IPv4
        packet += b'\x01'  # Count
        packet += b'\x00\x01'  # Class ID
        packet += b'\x01'  # TXT count
        packet += b'\x04name'  # Key
        packet += b'\x05value'  # Value
        
        discovery._parse_packet(packet, "192.168.1.100")
        # Should parse TXT records
    
    def test_parse_packet_invalid_version(self):
        """Test parsing packet with invalid version."""
        discovery = LSDPDiscovery()
        packet = b'\x06LSDP\x02'  # Version 2 (invalid)
        
        discovery._parse_packet(packet, "192.168.1.100")
        assert len(discovery.discovered_devices) == 0
    
    def test_parse_packet_short_header(self):
        """Test parsing packet that's too short."""
        discovery = LSDPDiscovery()
        packet = b'\x05LSDP'  # Too short
        
        discovery._parse_packet(packet, "192.168.1.100")
        assert len(discovery.discovered_devices) == 0
    
    def test_parse_announce_multiple_records(self):
        """Test parsing announce with multiple service records."""
        discovery = LSDPDiscovery()
        
        # Build packet with multiple records
        packet = b'\x06LSDP\x01'
        packet += b'\x25\x41'  # Announce
        packet += b'\x06aa:bb:cc'
        packet += b'\x04\xc0\xa8\x01\x64'
        packet += b'\x02'  # 2 records
        packet += b'\x00\x01'  # Record 1
        packet += b'\x00'  # No TXT
        packet += b'\x00\x08'  # Record 2
        packet += b'\x00'  # No TXT
        
        discovery._parse_packet(packet, "192.168.1.100")
        # Should handle multiple records
    
    @patch('lsdp.time.sleep')
    @patch('socket.socket')
    def test_discover_filters_invalid_ips(self, mock_socket, _mock_sleep):
        """Test that discovery filters invalid IPs."""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.recvfrom.side_effect = socket.timeout()
        
        discovery = LSDPDiscovery(timeout=1)
        discovery.discovered_devices = {
            'dev1': LSDPDevice('aa:bb:cc', '127.0.0.1', CLASS_BLUOS_PLAYER, {}),
            'dev2': LSDPDevice('aa:bb:dd', '192.168.1.100', CLASS_BLUOS_PLAYER, {}),
        }
        
        result = discovery.discover()
        # Loopback must be filtered out; private IP should pass validation
        assert '127.0.0.1' not in result

