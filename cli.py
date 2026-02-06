#!/usr/bin/env python3
"""
CLI interface for Bluesound Controller.

Copyright 2025 tbaur

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import subprocess
import json
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError

from constants import BOLD, RED, GREEN, YELLOW, BLUE, CYAN, RESET, DIM, BLUOS_PORT, MAX_WORKERS_DISCOVERY, MAX_WORKERS_STATUS
from models import PlayerStatus
from controller import BluesoundController
from network import Network
from utils import format_bytes, format_rate, format_uptime
from validators import validate_volume, sanitize_ip, validate_ip
from keychain import set_api_key, get_api_key, delete_api_key, has_api_key, is_macos

logger = logging.getLogger("Bluesound")

class BluesoundCLI:
    """Command-line interface for Bluesound Controller."""
    
    def __init__(self, ctl: BluesoundController):
        self.ctl = ctl
    
    def _get_matching_devices(self, target: Optional[str] = None) -> List[PlayerStatus]:
        """
        Get list of devices matching target pattern.
        
        Args:
            target: Device name pattern (None or empty = all devices)
            
        Returns:
            List of matching PlayerStatus objects
        """
        targets = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as ex:
            f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for f in as_completed(f_map):
                d = f.result()
                if d.name != 'Unknown':
                    if not target or target.lower() in d.name.lower():
                        targets.append(d)
        return targets
    
    def print_help(self) -> None:
        """Print help information."""
        bc = f"{GREEN}bluesound-controller{RESET}"

        print(f"\n{BOLD}Bluesound Controller{RESET}")
        print(f"{DIM}Command-line controller for Bluesound devices on macOS.{RESET}\n")

        print(f"{BOLD}Usage:{RESET}  {bc} <command> [options]\n")

        print(f"{BOLD}Discovery & Status:{RESET}")
        print(f"  {GREEN}discover{RESET}                       Find devices on the network")
        print(f"  {GREEN}status{RESET}   {DIM}[name]{RESET} {DIM}[--scan] [--json]{RESET}  Device status (filter by name)")
        print(f"  {GREEN}diagnose{RESET} {DIM}<name>{RESET}                  Detailed device diagnostics\n")

        print(f"{BOLD}Playback:{RESET}  {DIM}All commands take an optional [name] to target specific devices.{RESET}")
        print(f"  {GREEN}play{RESET}  {GREEN}pause{RESET}  {GREEN}stop{RESET}  {GREEN}skip{RESET}  {GREEN}previous{RESET}  {GREEN}toggle{RESET}\n")

        print(f"{BOLD}Volume:{RESET}")
        print(f"  {GREEN}volume{RESET}                             Show all volume levels")
        print(f"  {GREEN}volume{RESET} {DIM}<0-100>{RESET} {DIM}[name]{RESET}              Set volume")
        print(f"  {GREEN}volume{RESET} {DIM}+5|-5{RESET} {DIM}[name]{RESET}                Adjust relative")
        print(f"  {GREEN}volume{RESET} {DIM}mute|unmute|reset{RESET} {DIM}[name]{RESET}     Mute, unmute, or reset to safe level\n")

        print(f"{BOLD}Queue:{RESET}")
        print(f"  {GREEN}queue{RESET}   {DIM}[name]{RESET}                     Show queue")
        print(f"  {GREEN}queue{RESET}   {DIM}clear [name]{RESET}               Clear queue")
        print(f"  {GREEN}queue{RESET}   {DIM}move <from> <to> [name]{RESET}    Reorder tracks\n")

        print(f"{BOLD}Inputs & Bluetooth:{RESET}")
        print(f"  {GREEN}inputs{RESET}    {DIM}[name] [input]{RESET}            List or set audio input")
        print(f"  {GREEN}bluetooth{RESET} {DIM}[name] [mode]{RESET}             Get/set mode (manual, auto, guest, disable)\n")

        print(f"{BOLD}Presets & Sync:{RESET}")
        print(f"  {GREEN}presets{RESET}  {DIM}[name] [id]{RESET}               List or play a preset")
        print(f"  {GREEN}sync{RESET}    {DIM}create <master> <slaves>{RESET}   Create sync group")
        print(f"  {GREEN}sync{RESET}    {DIM}break [name]{RESET}               Break sync group")
        print(f"  {GREEN}sync{RESET}    {DIM}list{RESET}                       Show sync groups\n")

        print(f"{BOLD}System:{RESET}")
        print(f"  {GREEN}reboot{RESET}   {DIM}[name] [--soft]{RESET}           Reboot devices")
        print(f"  {GREEN}keychain{RESET} {DIM}set|get|delete{RESET}            Manage UniFi API key in macOS Keychain\n")

        print(f"{BOLD}Config:{RESET}  {DIM}~/.config/bluesound-controller/config.json{RESET}")
        print(f"{BOLD}Debug:{RESET}   {DIM}BLUESOUND_DEBUG=1 bluesound-controller <command>{RESET}\n")
    
    def discover(self) -> None:
        """Discover and list devices."""
        print(f"\n{BOLD}Discovered Devices:{RESET}")
        print("-" * 40)
        
        if not self.ctl.ips:
            print(f"{YELLOW}No devices found. Try running with --scan to force discovery.{RESET}")
            print("-" * 40)
            print()
            return
        
        results = {}
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as executor:
            future_to_ip = {executor.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for future in as_completed(future_to_ip):
                try:
                    d = future.result(timeout=5)  # Add timeout to prevent hanging
                    results[d.ip] = d.name
                except FutureTimeoutError:
                    ip = future_to_ip.get(future, 'unknown')
                    results[ip] = 'Timeout'
                except Exception as e:
                    ip = future_to_ip.get(future, 'unknown')
                    results[ip] = 'Error'
        
        for ip in self.ctl.ips:
            print(f"{CYAN}{ip}{RESET} - {BOLD}{results.get(ip, 'Unknown')}{RESET}")
        print("-" * 40)
        print()
    
    def status(self, pattern: Optional[str] = None, json_mode: bool = False):
        """Display device status."""
        if not self.ctl.ips:
            print(f"{RED}Error: No IPs found (Try --scan).{RESET}\n")
            return
        
        ustatus = self.ctl.sync_unifi()
        devices: List[PlayerStatus] = []
        
        max_workers = min(MAX_WORKERS_STATUS, len(self.ctl.ips)) if self.ctl.ips else MAX_WORKERS_STATUS
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for future in as_completed(future_to_ip):
                devices.append(future.result())
        
        devices.sort(key=lambda x: x.ip)
        
        if pattern:
            devices = [d for d in devices if pattern.lower() in d.name.lower()]
            if not devices:
                print(f"{RED}No devices matched pattern: '{pattern}'{RESET}\n")
                return
        
        if not json_mode:
            print()  # Leading newline for status output
            self._print_status_header(pattern, ustatus)
        
        self._print_device_status(devices, json_mode)
    
    def _print_status_header(self, pattern: Optional[str], ustatus: str) -> None:
        """Print status report header."""
        print(f"{BLUE}" + "="*80 + f"{RESET}")
        header_text = f"BLUOS NETWORK REPORT"
        if pattern:
            header_text += f" (Filter: {pattern})"
        print(f"{BOLD}  {header_text:<46} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{BLUE}" + "="*80 + f"{RESET}")
        if ustatus == "ERROR_FETCH":
            print(f"{YELLOW}⚠️  UniFi Error: No data received{RESET}")
        print("")
    
    def _print_device_status(self, devices: List[PlayerStatus], json_mode: bool) -> None:
        """Print device status information."""
        c_play = c_sync = c_idle = 0
        json_out = []
        
        for idx, d in enumerate(devices, 1):
            if d.name == 'Unknown':
                continue
            
            is_follower = bool(d.master)
            
            if is_follower:
                status_txt = f"{CYAN}🔗 SYNCED{RESET}  "
                c_sync += 1
            elif d.state in ['stream', 'play']:
                status_txt = f"{GREEN}▶ PLAYING{RESET}"
                c_play += 1
            elif d.state == 'connecting':
                status_txt = f"{YELLOW}⌛ BUFFER {RESET}"
                c_play += 1
            elif d.state == 'pause':
                status_txt = f"{YELLOW}⚠ PAUSED {RESET}"
                c_idle += 1
            else:
                status_txt = f"{DIM}■ STOPPED{RESET}"
                c_idle += 1
            
            if json_mode:
                json_out.append(asdict(d))
                continue
            
            conn_str = self._format_connection_string(d)
            print(f"[{BOLD}{idx}{RESET}] {BOLD}{d.name}{RESET}")
            print(f"    {DIM}" + "-"*76 + f"{RESET}")
            print(f"    Model: {d.full_model} | {BOLD}Uptime: {d.uptime}{RESET}")
            print(f"    IP:    {d.ip}  | {conn_str}")
            
            if d.unifi and d.unifi.uplink != 'Unknown':
                print(f"    Net:   ↓ {format_rate(d.unifi.down_rate)}  ↑ {format_rate(d.unifi.up_rate)}  (Total: {format_bytes(d.unifi.down_tot)} / {format_bytes(d.unifi.up_tot)})")
                print(f"    Link:  Connected to '{d.unifi.uplink}' ({d.unifi.port_info}) | Conn Time: {format_uptime(d.unifi.uptime)}")
            
            sys_line = f"System: FW {d.fw or 'N/A'}"
            if d.battery:
                sys_line += f"  | Battery: 🔋 {d.battery}%"
            
            print(f"    Status:{status_txt}  |  Vol: {d.volume}%             |  {'Synced to Leader' if is_follower else f'Source: {d.service}'}")
            print(f"    {sys_line}")
            print(f"    {DIM}" + "-"*76 + f"{RESET}")
            
            if not is_follower and d.state in ['stream', 'play', 'connecting']:
                print(f"    ♫ Track:  {CYAN}{d.track}{RESET}")
                print(f"    ♫ Artist: {d.artist}")
                print(f"    ♫ Album:  {d.album}")
            else:
                print(f"    {DIM}(Idle){RESET}")
            print(f"    {DIM}" + "-"*76 + f"{RESET}\n")
        
        if json_mode:
            print(json.dumps(json_out, indent=2))
        else:
            print(f"{BLUE}" + "="*80 + f"{RESET}")
            print(f"Summary: {BOLD}{len(devices)}{RESET} Found | {GREEN}{c_play}{RESET} Playing | {CYAN}{c_sync}{RESET} Synced | {DIM}{c_idle}{RESET} Idle")
            print(f"{BLUE}" + "="*80 + f"{RESET}")
            print()
    
    def _format_connection_string(self, d: PlayerStatus) -> str:
        """Format connection status string."""
        if d.unifi and d.unifi.is_wired:
            rssi = f" | Radio On: {d.db}dBm" if d.db else ""
            return f"{CYAN}[Ethernet]{RESET} {DIM}(UniFi Confirmed{rssi}){RESET}"
        elif d.db:
            try:
                db_val = int(float(d.db))
                if db_val >= -60:
                    col, lbl = GREEN, "(Excellent)"
                elif db_val >= -75:
                    col, lbl = YELLOW, "(Good)"
                else:
                    col, lbl = RED, "(WEAK)"
                return f"{col}RSSI: {db_val}dBm {lbl}{RESET}"
            except ValueError:
                return "RSSI: N/A"
        return f"{CYAN}[Ethernet]{RESET}"
    
    def volume(self, args) -> None:
        """Control device volume."""
        target = args.target if args.target != 'all' else None
        print(f"\n{BOLD}Volume Control: {args.target or 'all'}{RESET}")
        print("-" * 40)
        
        devices = self._get_matching_devices(target)
        for d in devices:
            cur = d.volume
            new_cmd = ""
            disp = ""
            
            if not args.cmd:
                print(f"[{BOLD}VOL {cur}%{RESET}] {d.name}")
                continue
            
            if args.cmd == 'mute':
                new_cmd = "mute=1"
                disp = f"{YELLOW}MUTED{RESET}"
            elif args.cmd == 'unmute':
                new_cmd = "mute=0"
                disp = f"{GREEN}UNMUTED{RESET}"
            elif args.cmd == 'reset':
                s = self.ctl.config.get('DEFAULT_SAFE_VOL', 14)
                new_cmd = f"level={s}"
                disp = f"{BLUE}RESET{RESET}"
            elif args.cmd.startswith('+'):
                try:
                    increment = int(args.cmd[1:])
                    n = validate_volume(cur + increment)
                    new_cmd = f"level={n}"
                    disp = f"{GREEN}VOL {n}%{RESET}"
                except (ValueError, TypeError):
                    print(f"{RED}Invalid volume increment: {args.cmd}{RESET}")
                    continue
            elif args.cmd.startswith('-'):
                try:
                    decrement = int(args.cmd[1:])
                    n = validate_volume(cur - decrement)
                    new_cmd = f"level={n}"
                    disp = f"{YELLOW}VOL {n}%{RESET}"
                except (ValueError, TypeError):
                    print(f"{RED}Invalid volume decrement: {args.cmd}{RESET}")
                    continue
            elif args.cmd.isdigit():
                try:
                    vol = validate_volume(int(args.cmd))
                    new_cmd = f"level={vol}"
                    disp = f"{GREEN}VOL {vol}%{RESET}"
                except (ValueError, TypeError):
                    print(f"{RED}Invalid volume: {args.cmd}{RESET}")
                    continue
            
            if new_cmd:
                sanitized_ip = sanitize_ip(d.ip)
                if sanitized_ip:
                    Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Volume?{new_cmd}", timeout=1)
                    print(f"[{disp}] {d.name}")
                else:
                    print(f"{RED}Invalid IP for {d.name}: {d.ip}{RESET}")
        print()
    
    def pause(self, args) -> None:
        """Pause players."""
        target = args.target
        print(f"\n{BOLD}Pausing Players...{RESET}")
        
        targets = self._get_matching_devices(target)
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            sanitized_ip = sanitize_ip(d.ip)
            if sanitized_ip:
                res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Pause", timeout=1)
                state = f"{GREEN}PAUSED{RESET}" if res is not None else f"{RED}ERROR{RESET}"
                print(f"[{state}] {d.name}")
            else:
                print(f"{RED}ERROR: Invalid IP for {d.name}: {d.ip}{RESET}")
        print()
    
    def reboot(self, args) -> None:
        """Reboot all or matching devices (hard reboot)."""
        target = getattr(args, 'target', None)
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        scope = f"'{target}'" if target else "ALL"
        print(f"\n{RED}{BOLD}WARNING: Reboot {scope} Bluesound devices?{RESET}")
        if input("Confirm (y/N): ").lower() != 'y':
            return
        
        print("-" * 40)
        for d in targets:
            sanitized_ip = sanitize_ip(d.ip)
            if not sanitized_ip:
                print(f"{RED}Invalid IP: {d.ip}{RESET}")
                continue
            print(f"Rebooting {d.name} ({sanitized_ip})... ", end='', flush=True)
            res = Network.post(f"http://{sanitized_ip}/reboot", data={"yes": "1"}, timeout=2)
            
            if res is not None:
                print(f"{GREEN}Sent{RESET}")
            else:
                print(f"{YELLOW}Sent (No Ack){RESET}")
        print()
    
    def soft_reboot(self, args) -> None:
        """Soft reboot all or matching devices."""
        target = getattr(args, 'target', None)
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        scope = f"'{target}'" if target else "ALL"
        print(f"\n{YELLOW}{BOLD}Soft Reboot {scope} Bluesound devices?{RESET}")
        if input("Confirm (y/N): ").lower() != 'y':
            return
        
        print("-" * 40)
        for d in targets:
            sanitized_ip = sanitize_ip(d.ip)
            if not sanitized_ip:
                print(f"{RED}Invalid IP: {d.ip}{RESET}")
                continue
            print(f"Soft rebooting {d.name} ({sanitized_ip})... ", end='', flush=True)
            res = self.ctl.soft_reboot(sanitized_ip)
            
            if res:
                print(f"{GREEN}Sent{RESET}")
            else:
                print(f"{YELLOW}Sent (No Ack){RESET}")
        print()
    
    def diagnose(self, target: str) -> None:
        """Diagnose a specific device."""
        print(f"\n{BOLD}Diagnostics for {target}{RESET}")
        print("=" * 50)
        
        matches = self._get_matching_devices(target)
        tgt_ip = matches[0].ip if matches else None
        
        if not tgt_ip:
            print(f"{RED}Device not found.{RESET}\n")
            return
        
        arp_mac = "Unknown"
        sanitized_ip = sanitize_ip(tgt_ip)
        if sanitized_ip:
            try:
                # Security: Validate IP before subprocess call, use list args, explicit timeout
                # IP is already sanitized by sanitize_ip(), but double-check
                if not validate_ip(sanitized_ip):
                    logger.warning(f"Invalid IP for ARP lookup: {sanitized_ip}")
                else:
                    out = subprocess.check_output(
                        ["arp", "-n", sanitized_ip], 
                        text=True, 
                        stderr=subprocess.DEVNULL,
                        timeout=2,
                        # Security: Explicitly disable shell
                        shell=False
                    )
                    # Validate output size
                    if len(out) > 1000:  # Reasonable limit for ARP output
                        logger.warning(f"ARP output too large: {len(out)} bytes")
                    elif len(out.split()) >= 4:
                        arp_mac = out.split()[3]
            except subprocess.TimeoutExpired:
                logger.debug(f"ARP lookup timeout for {sanitized_ip}")
                pass
            except subprocess.CalledProcessError as e:
                logger.debug(f"ARP lookup failed for {sanitized_ip}: {e}")
                pass
            except FileNotFoundError:
                logger.debug("arp command not found")
                pass
            except Exception as e:
                logger.debug(f"Unexpected error in ARP lookup: {e}")
                pass
        
        sys_uptime = self.ctl.get_sys_uptime(tgt_ip)
        
        print(f"IP Address: {CYAN}{tgt_ip}{RESET}")
        print(f"ARP MAC:    {CYAN}{arp_mac}{RESET}")
        print(f"Sys Uptime: {GREEN}{sys_uptime}{RESET}")
        
        self.ctl.sync_unifi()
        u = self.ctl.unifi_map.get(tgt_ip)
        if u:
            print(f"UniFi DB:   {GREEN}FOUND{RESET} -> Wired: {u.is_wired}, Uplink: {u.uplink}")
            print(f"            Conn Time: {format_uptime(u.uptime)}")
        else:
            print(f"UniFi DB:   {DIM}Not Found{RESET}")
        
        print(f"\n{BOLD}Endpoint: /SyncStatus{RESET}")
        if sanitized_ip:
            raw = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/SyncStatus")
        if raw:
            print(raw.decode('utf-8', errors='ignore'))
        else:
            print(f"{RED}Invalid IP address: {tgt_ip}{RESET}")
        print()
    
    def _run_device_command(
        self,
        target: Optional[str],
        action_label: str,
        command_fn,
        success_label: str,
    ) -> None:
        """
        Run a command on all or matching devices with consistent output formatting.
        
        Args:
            target: Device name pattern (None = all devices)
            action_label: Header text (e.g. "Starting Playback")
            command_fn: Callable(device) -> bool indicating success
            success_label: Label shown on success (e.g. "PLAYING")
        """
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}{action_label} on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            res = command_fn(d)
            state = f"{GREEN}{success_label}{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
    def play(self, args) -> None:
        """Start/resume playback on all or matching devices."""
        self._run_device_command(
            args.target, "Starting Playback",
            lambda d: self.ctl.play(d.ip), "PLAYING",
        )
    
    def stop(self, args) -> None:
        """Stop playback on all or matching devices."""
        self._run_device_command(
            args.target, "Stopping Playback",
            lambda d: self.ctl.stop(d.ip), "STOPPED",
        )
    
    def skip(self, args) -> None:
        """Skip to next track on all or matching devices."""
        self._run_device_command(
            args.target, "Skipping Track",
            lambda d: self.ctl.skip(d.ip), "SKIPPED",
        )
    
    def previous(self, args) -> None:
        """Go to previous track on all or matching devices."""
        self._run_device_command(
            args.target, "Previous Track",
            lambda d: self.ctl.previous(d.ip), "PREVIOUS",
        )
    
    def toggle(self, args) -> None:
        """Toggle play/pause state on all or matching devices."""
        def _toggle(d: PlayerStatus) -> bool:
            if d.state in ['play', 'stream', 'connecting']:
                return self.ctl.pause_device(d.ip)
            return self.ctl.play(d.ip)
        
        self._run_device_command(
            args.target, "Toggling Playback", _toggle, "OK",
        )
    
    def queue(self, args) -> None:
        """Manage playback queue on all or matching devices."""
        target = args.target
        action = args.action
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        if action == 'show' or action is None:
            # Show queue for all matching devices
            for tgt_device in targets:
                queue_data = self.ctl.get_queue(tgt_device.ip)
                if queue_data:
                    print(f"\n{BOLD}Queue for {tgt_device.name}:{RESET}")
                    print("-" * 60)
                    for idx, item in enumerate(queue_data['items'], 1):
                        print(f"{idx}. {CYAN}{item['title']}{RESET} - {item['artist']}")
                        if item['album']:
                            print(f"   Album: {item['album']}")
                    print(f"\nTotal: {queue_data['count']} items")
                else:
                    print(f"{YELLOW}No queue data available for {tgt_device.name}.{RESET}")
                if len(targets) > 1:
                    print()  # Add spacing between devices
        
        elif action == 'clear':
            # Clear queue on all matching devices
            scope = f"'{target}'" if target else "all devices"
            print(f"\n{BOLD}Clearing Queue on {scope}...{RESET}")
            print("-" * 40)
            for tgt_device in targets:
                res = self.ctl.clear_queue(tgt_device.ip)
                state = f"{GREEN}CLEARED{RESET}" if res else f"{RED}ERROR{RESET}"
                print(f"[{state}] {tgt_device.name}")
            print()
        
        elif action == 'move':
            if not args.from_index or not args.to_index:
                print(f"{RED}Usage: queue move <from> <to> [target]{RESET}")
                return
            try:
                from_idx = int(args.from_index)
                to_idx = int(args.to_index)
                scope = f"'{target}'" if target else "all devices"
                print(f"\n{BOLD}Moving Queue Item on {scope}...{RESET}")
                print("-" * 40)
                for tgt_device in targets:
                    res = self.ctl.move_queue_item(tgt_device.ip, from_idx, to_idx)
                    state = f"{GREEN}MOVED{RESET}" if res else f"{RED}ERROR{RESET}"
                    print(f"[{state}] Moved item {from_idx} to {to_idx} for {tgt_device.name}")
                print()
            except ValueError:
                print(f"{RED}Invalid queue indices.{RESET}")
    
    def inputs(self, args) -> None:
        """Manage audio inputs on all or matching devices."""
        target = args.target
        input_name = args.input
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        if input_name:
            # Set input on all matching devices
            scope = f"'{target}'" if target else "all devices"
            print(f"\n{BOLD}Setting Input on {scope}...{RESET}")
            print("-" * 40)
            for tgt_device in targets:
                res = self.ctl.set_input(tgt_device.ip, input_name)
                state = f"{GREEN}SET{RESET}" if res else f"{RED}ERROR{RESET}"
                print(f"[{state}] {tgt_device.name} -> '{input_name}'")
            print()
        else:
            # List inputs for all matching devices
            for tgt_device in targets:
                inputs = self.ctl.get_inputs(tgt_device.ip)
                if inputs:
                    print(f"\n{BOLD}Available Inputs for {tgt_device.name}:{RESET}")
                    print("-" * 60)
                    for inp in inputs:
                        marker = f"{GREEN}●{RESET}" if inp['selected'] else " "
                        print(f"{marker} {inp['name']} ({inp['type']})")
                else:
                    print(f"{YELLOW}No input data available for {tgt_device.name}.{RESET}")
                if len(targets) > 1:
                    print()  # Add spacing between devices
    
    def bluetooth(self, args) -> None:
        """Manage Bluetooth mode on all or matching devices."""
        target = args.target
        mode = args.mode
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        if mode:
            # Set mode on all matching devices
            mode_map = {'manual': 0, 'auto': 1, 'automatic': 1, 'guest': 2, 'disable': 3, 'disabled': 3}
            mode_val = mode_map.get(mode.lower())
            if mode_val is None:
                print(f"{RED}Invalid mode. Use: manual, auto, guest, or disable{RESET}")
                return
            scope = f"'{target}'" if target else "all devices"
            print(f"\n{BOLD}Setting Bluetooth Mode on {scope}...{RESET}")
            print("-" * 40)
            for tgt_device in targets:
                res = self.ctl.set_bluetooth_mode(tgt_device.ip, mode_val)
                state = f"{GREEN}SET{RESET}" if res else f"{RED}ERROR{RESET}"
                print(f"[{state}] {tgt_device.name} -> '{mode}'")
            print()
        else:
            # Show current mode for all matching devices
            for tgt_device in targets:
                current_mode = self.ctl.get_bluetooth_mode(tgt_device.ip)
                if current_mode:
                    print(f"{BOLD}Bluetooth Mode for {tgt_device.name}:{RESET} {CYAN}{current_mode}{RESET}")
                else:
                    print(f"{YELLOW}Bluetooth mode not available for {tgt_device.name}.{RESET}")
                if len(targets) > 1:
                    print()  # Add spacing between devices
    
    def presets(self, args) -> None:
        """Manage presets on all or matching devices."""
        target = args.target
        preset_id = args.preset_id
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        if preset_id is not None:
            # Play preset on all matching devices
            try:
                pid = int(preset_id)
                scope = f"'{target}'" if target else "all devices"
                print(f"\n{BOLD}Playing Preset {pid} on {scope}...{RESET}")
                print("-" * 40)
                for tgt_device in targets:
                    res = self.ctl.play_preset(tgt_device.ip, pid)
                    state = f"{GREEN}PLAYING{RESET}" if res else f"{RED}ERROR{RESET}"
                    print(f"[{state}] {tgt_device.name} -> Preset {pid}")
                print()
            except ValueError:
                print(f"{RED}Invalid preset ID.{RESET}")
        else:
            # List presets for all matching devices
            for tgt_device in targets:
                presets = self.ctl.get_presets(tgt_device.ip)
                if presets:
                    print(f"\n{BOLD}Presets for {tgt_device.name}:{RESET}")
                    print("-" * 60)
                    for preset in presets:
                        print(f"{preset['id']}. {CYAN}{preset['name']}{RESET}")
                else:
                    print(f"{YELLOW}No presets available for {tgt_device.name}.{RESET}")
                if len(targets) > 1:
                    print()  # Add spacing between devices
    
    def sync(self, args) -> None:
        """Manage sync groups."""
        action = args.action
        
        if action == 'create':
            master_name = args.master
            slave_names = args.slaves.split(',') if args.slaves else []
            
            all_devices = self._get_matching_devices(None)
            devices = {d.name.lower(): d for d in all_devices}
            
            master = devices.get(master_name.lower())
            if not master:
                print(f"{RED}Master device '{master_name}' not found.{RESET}")
                return
            
            print(f"\n{BOLD}Creating sync group with {master.name} as master...{RESET}")
            print("-" * 40)
            
            for slave_name in slave_names:
                slave = devices.get(slave_name.strip().lower())
                if slave:
                    res = self.ctl.add_sync_slave(master.ip, slave.ip)
                    state = f"{GREEN}ADDED{RESET}" if res else f"{RED}ERROR{RESET}"
                    print(f"[{state}] {slave.name} -> {master.name}")
                else:
                    print(f"{YELLOW}Slave '{slave_name}' not found.{RESET}")
            print()
        
        elif action == 'break':
            target = args.target
            targets = self._get_matching_devices(target)
            
            if not targets:
                print(f"{RED}No matching devices found.{RESET}")
                return
            
            print(f"\n{BOLD}Breaking sync groups...{RESET}")
            print("-" * 40)
            for d in targets:
                res = Network.get(f"http://{d.ip}:{BLUOS_PORT}/Sync?remove={d.ip}", timeout=2)
                state = f"{GREEN}BROKEN{RESET}" if res else f"{YELLOW}NO SYNC{RESET}"
                print(f"[{state}] {d.name}")
            print()
        
        elif action == 'list':
            print(f"\n{BOLD}Sync Groups:{RESET}")
            print("-" * 60)
            devices = self._get_matching_devices(None)
            
            for d in devices:
                if d.master:
                    print(f"{d.name} -> {d.master} (Synced)")
                else:
                    print(f"{d.name} (Standalone)")
            print()
    
    def keychain(self, args) -> None:
        """Manage UniFi API key in macOS Keychain."""
        action = args.action
        
        if not is_macos():
            print(f"{RED}Error: Keychain access is only available on macOS.{RESET}\n")
            return
        
        if action == 'set':
            # Prompt for API key
            import getpass
            print(f"\n{BOLD}Store UniFi API Key in Keychain{RESET}")
            print("-" * 40)
            api_key = getpass.getpass("Enter UniFi API Key: ")
            
            if not api_key:
                print(f"{RED}Error: API key cannot be empty.{RESET}\n")
                return
            
            if set_api_key(api_key):
                print(f"{GREEN}✓ API key stored in Keychain successfully{RESET}\n")
                print(f"{DIM}Note: The API key in config.json will be ignored.{RESET}")
                print(f"{DIM}The Keychain value takes precedence.{RESET}\n")
            else:
                print(f"{RED}Error: Failed to store API key in Keychain.{RESET}\n")
        
        elif action == 'get':
            print(f"\n{BOLD}UniFi API Key Status{RESET}")
            print("-" * 40)
            
            if has_api_key():
                api_key = get_api_key()
                if api_key:
                    # Show first 8 chars and last 4 chars for security
                    masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                    print(f"{GREEN}✓ API key found in Keychain{RESET}")
                    print(f"  Key: {masked}")
                    print(f"  Length: {len(api_key)} characters\n")
                else:
                    print(f"{YELLOW}⚠ API key entry exists but could not be retrieved{RESET}\n")
            else:
                print(f"{YELLOW}⚠ No API key found in Keychain{RESET}")
                print(f"{DIM}Checking config.json...{RESET}")
                # Get directly from config data (bypass Keychain check)
                config_key = self.ctl.config.data.get('UNIFI_API_KEY', '')
                if config_key and config_key.strip():
                    print(f"{CYAN}API key found in config.json{RESET}\n")
                else:
                    print(f"{RED}No API key found in config.json either{RESET}\n")
        
        elif action == 'delete':
            print(f"\n{BOLD}Remove UniFi API Key from Keychain{RESET}")
            print("-" * 40)
            
            if not has_api_key():
                print(f"{YELLOW}No API key found in Keychain.{RESET}\n")
                return
            
            confirm = input("Are you sure you want to remove the API key from Keychain? (y/N): ")
            if confirm.lower() != 'y':
                print("Cancelled.\n")
                return
            
            if delete_api_key():
                print(f"{GREEN}✓ API key removed from Keychain{RESET}\n")
                print(f"{DIM}Note: If an API key exists in config.json, it will be used.{RESET}\n")
            else:
                print(f"{RED}Error: Failed to remove API key from Keychain.{RESET}\n")
        
        else:
            print(f"{RED}Error: Invalid action. Use 'set', 'get', or 'delete'.{RESET}\n")


