#!/usr/bin/env python3
"""Tests for BluOS sync status parsing and group operations."""
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from controller import (
    BluesoundController,
    parse_bluos_host,
    parse_sync_status_root,
)
from models import PlayerStatus


class TestParseBluosHost:
    """Test BluOS host/IP parsing."""

    def test_plain_ip(self):
        assert parse_bluos_host("172.16.10.174") == "172.16.10.174"

    def test_ip_with_port(self):
        assert parse_bluos_host("172.16.10.174:11000") == "172.16.10.174"

    def test_empty(self):
        assert parse_bluos_host("") == ""
        assert parse_bluos_host(None) == ""


class TestParseSyncStatusRoot:
    """Test SyncStatus XML parsing."""

    def test_primary_with_group_and_slaves(self):
        root = ET.fromstring(
            b'<SyncStatus group="Living Room Speakers+Kitchen Speakers" name="Living Room Speakers">'
            b'<slave id="172.16.10.88" port="11000"/>'
            b"</SyncStatus>"
        )
        master, group, slaves = parse_sync_status_root(root)
        assert master == ""
        assert group == "Living Room Speakers+Kitchen Speakers"
        assert slaves == ["172.16.10.88"]

    def test_slave_with_master_child_element(self):
        root = ET.fromstring(
            b'<SyncStatus name="Kitchen Speakers">'
            b'<master port="11000">172.16.10.174</master>'
            b"</SyncStatus>"
        )
        master, group, slaves = parse_sync_status_root(root)
        assert master == "172.16.10.174"
        assert group == ""
        assert slaves == []

    def test_legacy_master_attribute(self):
        root = ET.fromstring(b'<sync name="Slave" master="192.168.1.100"/>')
        master, group, slaves = parse_sync_status_root(root)
        assert master == "192.168.1.100"
        assert group == ""
        assert slaves == []


class TestCollectSyncBreakOperations:
    """Test sync break operation planning."""

    @pytest.fixture
    def controller(self):
        with patch("controller.Config"):
            return BluesoundController()

    def test_break_all_from_primary(self, controller):
        devices = [
            PlayerStatus(
                ip="172.16.10.174",
                name="Living Room Speakers",
                group="Living Room Speakers+Kitchen Speakers",
                slaves=["172.16.10.88"],
            ),
            PlayerStatus(ip="172.16.10.88", name="Kitchen Speakers", master="172.16.10.174"),
        ]

        operations = controller.collect_sync_break_operations(devices)
        assert operations == [
            ("172.16.10.174", "172.16.10.88", "Kitchen Speakers from Living Room Speakers"),
        ]

    def test_break_single_slave_target(self, controller):
        devices = [
            PlayerStatus(ip="172.16.10.174", name="Living Room Speakers", slaves=["172.16.10.88"]),
            PlayerStatus(ip="172.16.10.88", name="Kitchen Speakers", master="172.16.10.174"),
        ]
        target = [devices[1]]

        operations = controller.collect_sync_break_operations(devices, target)
        assert operations == [
            ("172.16.10.174", "172.16.10.88", "Kitchen Speakers from Living Room Speakers"),
        ]

    def test_break_primary_target(self, controller):
        devices = [
            PlayerStatus(ip="172.16.10.174", name="Living Room Speakers", slaves=["172.16.10.88"]),
            PlayerStatus(ip="172.16.10.88", name="Kitchen Speakers", master="172.16.10.174"),
        ]
        target = [devices[0]]

        operations = controller.collect_sync_break_operations(devices, target)
        assert operations == [
            ("172.16.10.174", "172.16.10.88", "Kitchen Speakers from Living Room Speakers"),
        ]

    @patch("controller.Network.get")
    def test_get_device_info_reads_master_child(self, mock_network, controller):
        sync_xml = (
            b'<SyncStatus name="Kitchen Speakers">'
            b"<master>172.16.10.174:11000</master>"
            b"</SyncStatus>"
        )
        status_xml = b"<status><volume>20</volume><state>play</state></status>"
        mock_network.side_effect = [sync_xml, status_xml, None]

        status = controller.get_device_info("172.16.10.88")
        assert status.master == "172.16.10.174"
        assert status.group == ""
        assert status.slaves == []
