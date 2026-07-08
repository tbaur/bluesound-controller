"""
Additional CLI tests for coverage.
"""
import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import as_completed

from cli import BluesoundCLI
from controller import BluesoundController
from models import PlayerStatus
from constants import MAX_WORKERS_DISCOVERY


class TestCLICoverage:
    """Additional CLI tests for better coverage."""
    
    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        ctl = BluesoundController()
        return BluesoundCLI(ctl)
    
    def test_status_no_ips(self, cli):
        """Test status with no IPs."""
        cli.ctl.ips = []
        with patch('builtins.print') as mock_print:
            cli.status()
            mock_print.assert_called()
            assert "No IPs found" in str(mock_print.call_args)
    
    def test_status_pattern_no_match(self, cli):
        """Test status with pattern that matches nothing."""
        cli.ctl.ips = ['192.168.1.100']
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'sync_unifi', return_value="SUCCESS:1"):
                    with patch('builtins.print') as mock_print:
                        cli.status(pattern="NonExistent")
                        assert "No devices matched pattern" in str(mock_print.call_args)
    
    def test_stop_command(self, cli):
        """Test stop command."""
        args = MagicMock()
        args.target = None
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'stop', return_value=True):
                    with patch('builtins.print'):
                        cli.stop(args)
    
    def test_skip_command(self, cli):
        """Test skip command."""
        args = MagicMock()
        args.target = None
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'skip', return_value=True):
                    with patch('builtins.print'):
                        cli.skip(args)
    
    def test_previous_command(self, cli):
        """Test previous command."""
        args = MagicMock()
        args.target = None
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'previous', return_value=True):
                    with patch('builtins.print'):
                        cli.previous(args)
    
    def test_toggle_command(self, cli):
        """Test toggle command."""
        args = MagicMock()
        args.target = None
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'pause_device', return_value=True):
                    with patch.object(cli.ctl, 'play', return_value=True):
                        with patch('builtins.print'):
                            cli.toggle(args)
    
    def test_sync_create_master_not_found(self, cli):
        """Test sync create with master not found."""
        cli.ctl.ips = ['192.168.1.100']
        args = MagicMock()
        args.action = 'create'
        args.master = 'NonExistent'
        args.slaves = None
        
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('builtins.print') as mock_print:
                    cli.sync(args)
                    assert "not found" in str(mock_print.call_args).lower()
    
    def test_sync_create_with_slaves(self, cli):
        """Test sync create with slaves."""
        cli.ctl.ips = ['192.168.1.100', '192.168.1.101']
        args = MagicMock()
        args.action = 'create'
        args.master = 'Test Speaker'
        args.slaves = 'Test Speaker 2'
        
        mock_future1 = MagicMock()
        mock_future1.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        mock_future2 = MagicMock()
        mock_future2.result.return_value = PlayerStatus(ip="192.168.1.101", name="Test Speaker 2")
        
        with patch('cli.as_completed', return_value=[mock_future1, mock_future2]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.side_effect = [mock_future1, mock_future2]
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'add_sync_slave', return_value=True):
                    with patch('builtins.print'):
                        cli.sync(args)
    
    def test_sync_create_slave_not_found(self, cli):
        """Test sync create with slave not found."""
        cli.ctl.ips = ['192.168.1.100']
        args = MagicMock()
        args.action = 'create'
        args.master = 'Test Speaker'
        args.slaves = 'NonExistent'
        
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('builtins.print') as mock_print:
                    cli.sync(args)
                    # Check all print calls for "not found" message
                    # Check each call's arguments for the message
                    found_message = False
                    for call in mock_print.call_args_list:
                        # call.args[0] is the first argument to print()
                        if call.args and len(call.args) > 0:
                            message = str(call.args[0])
                            if "not found" in message.lower():
                                found_message = True
                                break
                    assert found_message, "Expected 'not found' message in print calls"
    
    def test_sync_break(self, cli):
        """Test sync break."""
        cli.ctl.ips = ['192.168.1.100', '192.168.1.101']
        args = MagicMock()
        args.action = 'break'
        args.target = None
        args.master = None
        
        primary = PlayerStatus(
            ip="192.168.1.100",
            name="Living Room",
            slaves=["192.168.1.101"],
        )
        slave = PlayerStatus(ip="192.168.1.101", name="Kitchen", master="192.168.1.100")
        
        mock_future1 = MagicMock()
        mock_future1.result.return_value = primary
        mock_future2 = MagicMock()
        mock_future2.result.return_value = slave
        
        with patch('cli.as_completed', return_value=[mock_future1, mock_future2]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.side_effect = [mock_future1, mock_future2]
                mock_executor_class.return_value = mock_executor
                
                with patch.object(cli.ctl, 'remove_sync_slave', return_value=True) as mock_remove:
                    with patch('builtins.print'):
                        cli.sync(args)
                    mock_remove.assert_called_once_with("192.168.1.100", "192.168.1.101")
    
    def test_sync_break_with_master_arg(self, cli):
        """Test sync break accepts device name in master positional arg."""
        primary = PlayerStatus(ip="192.168.1.100", name="Living Room", slaves=["192.168.1.101"])
        slave = PlayerStatus(ip="192.168.1.101", name="Kitchen", master="192.168.1.100")

        args = MagicMock()
        args.action = 'break'
        args.target = None
        args.master = 'Kitchen'

        with patch.object(cli, '_get_matching_devices', side_effect=[[primary, slave], [slave]]):
            with patch.object(cli.ctl, 'remove_sync_slave', return_value=True) as mock_remove:
                with patch('builtins.print'):
                    cli.sync(args)
                mock_remove.assert_called_once_with("192.168.1.100", "192.168.1.101")

    def test_sync_list_no_ips(self, cli):
        """Test sync list warns when no devices discovered."""
        cli.ctl.ips = []
        args = MagicMock()
        args.action = 'list'

        with patch('builtins.print') as mock_print:
            cli.sync(args)
            assert "No IPs found" in str(mock_print.call_args)

    def test_format_status_row_aligns_source(self, cli):
        """Status row keeps Source in the right-hand column."""
        row = cli._format_status_row("★ PRIMARY ", 10, "Source: TidalConnect")
        assert "Vol: 10%             |  Source: TidalConnect" in row

    def test_format_sync_line_primary_shows_count_only(self, cli):
        """Primary sync line shows slave count, not names."""
        primary = PlayerStatus(
            ip="172.16.10.174",
            name="Living Room Speakers",
            slaves=["172.16.10.88", "172.16.10.86", "172.16.10.48"],
        )
        line = cli._format_sync_line(primary, [primary])
        assert line == "Sync:   3 slaves"

    def test_format_sync_line_for_slave_uses_name(self, cli):
        """Slaves should reference the primary by name, not IP."""
        devices = [
            PlayerStatus(ip="172.16.10.174", name="Living Room Speakers"),
            PlayerStatus(ip="172.16.10.88", name="Kitchen Speakers", master="172.16.10.174"),
        ]
        line = cli._format_sync_line(devices[1], devices)
        assert "Following" in line
        assert "Living Room Speakers" in line
        assert "172.16.10.174" not in line

    def test_sync_break_no_match(self, cli):
        """Test sync break with no matching devices."""
        cli.ctl.ips = ['192.168.1.100']
        args = MagicMock()
        args.action = 'break'
        args.target = 'NonExistent'
        args.master = None
        
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('builtins.print') as mock_print:
                    cli.sync(args)
                    assert "No matching devices" in str(mock_print.call_args)
    
    def test_sync_list(self, cli):
        """Test sync list."""
        cli.ctl.ips = ['192.168.1.100', '192.168.1.101']
        args = MagicMock()
        args.action = 'list'
        
        mock_future1 = MagicMock()
        mock_future1.result.return_value = PlayerStatus(
            ip="192.168.1.100",
            name="Living Room",
            group="Living Room+Kitchen",
            slaves=["192.168.1.101"],
        )
        mock_future2 = MagicMock()
        mock_future2.result.return_value = PlayerStatus(ip="192.168.1.101", name="Kitchen", master="192.168.1.100")
        
        with patch('cli.as_completed', return_value=[mock_future1, mock_future2]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.side_effect = [mock_future1, mock_future2]
                mock_executor_class.return_value = mock_executor
                
                with patch('builtins.print'):
                    cli.sync(args)
    
    def test_sync_list_standalone(self, cli):
        """Test sync list with standalone devices."""
        cli.ctl.ips = ['192.168.1.100']
        args = MagicMock()
        args.action = 'list'
        
        mock_future = MagicMock()
        mock_future.result.return_value = PlayerStatus(ip="192.168.1.100", name="Test Speaker")
        
        with patch('cli.as_completed', return_value=[mock_future]):
            with patch('cli.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor.__enter__ = MagicMock(return_value=mock_executor)
                mock_executor.__exit__ = MagicMock(return_value=False)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('builtins.print'):
                    cli.sync(args)

