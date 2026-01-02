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

# Import Utils for backward compatibility
class Utils:
    format_bytes = staticmethod(format_bytes)
    format_rate = staticmethod(format_rate)
    format_uptime = staticmethod(format_uptime)


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
        """Print comprehensive help information."""
        # Header
        print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{BOLD}{BLUE}  Bluesound Controller{RESET}")
        print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
        
        # Description
        print(f"{CYAN}A unified command-line controller for Bluesound devices on macOS.{RESET}\n")
        
        # Usage
        print(f"{BOLD}USAGE:{RESET}")
        print(f"  {GREEN}bluesound-controller{RESET} {DIM}<command>{RESET} {DIM}[options]{RESET} {DIM}[arguments]{RESET}\n")
        
        # Commands
        print(f"{BOLD}COMMANDS:{RESET}\n")
        
        # Discover
        print(f"  {GREEN}discover{RESET}")
        print(f"    {DIM}Discover and list all Bluesound devices on your network.{RESET}")
        print(f"    {DIM}Uses mDNS (default) or LSDP based on configuration.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller discover{RESET}\n")
        
        # Status
        print(f"  {GREEN}status{RESET} {DIM}[name] [options]{RESET}")
        print(f"    {DIM}Display comprehensive status report for all or filtered devices.{RESET}")
        print(f"    {DIM}Shows device info, network stats, playback state, and UniFi data.{RESET}\n")
        print(f"    {BOLD}Arguments:{RESET}")
        print(f"      {DIM}name{RESET}          Filter devices by name (partial match, case-insensitive)\n")
        print(f"    {BOLD}Options:{RESET}")
        print(f"      {CYAN}--scan{RESET}        Force fresh network discovery (bypass cache)")
        print(f"      {CYAN}--json{RESET}        Output in JSON format for scripting\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller status{RESET}")
        print(f"      {DIM}bluesound-controller status \"Living Room\"{RESET}")
        print(f"      {DIM}bluesound-controller status --scan{RESET}")
        print(f"      {DIM}bluesound-controller status --json{RESET}\n")
        
        # Diagnose
        print(f"  {GREEN}diagnose{RESET} {DIM}<name>{RESET}")
        print(f"    {DIM}Show detailed diagnostic information for a specific device.{RESET}")
        print(f"    {DIM}Includes IP, MAC address, uptime, UniFi data, and raw XML.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller diagnose \"Kitchen Speaker\"{RESET}\n")
        
        # Volume
        print(f"  {GREEN}volume{RESET} {DIM}[command] [target]{RESET}")
        print(f"    {DIM}Control volume for all or specific devices.{RESET}\n")
        print(f"    {BOLD}Commands:{RESET}")
        print(f"      {CYAN}(none){RESET}        List current volume levels for all devices")
        print(f"      {CYAN}<number>{RESET}      Set absolute volume (0-100)")
        print(f"      {CYAN}+<number>{RESET}     Increase volume by specified amount")
        print(f"      {CYAN}-<number>{RESET}     Decrease volume by specified amount")
        print(f"      {CYAN}mute{RESET}          Mute device(s)")
        print(f"      {CYAN}unmute{RESET}        Unmute device(s)")
        print(f"      {CYAN}reset{RESET}         Reset to default safe volume\n")
        print(f"    {BOLD}Target:{RESET}")
        print(f"      {DIM}all{RESET}           Apply to all devices (default)")
        print(f"      {DIM}<name>{RESET}         Apply to devices matching name\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller volume{RESET}")
        print(f"        {DIM}# List volumes{RESET}")
        print(f"      {DIM}bluesound-controller volume 25{RESET}")
        print(f"        {DIM}# Set all to 25%{RESET}")
        print(f"      {DIM}bluesound-controller volume +5{RESET}")
        print(f"        {DIM}# Increase all by 5{RESET}")
        print(f"      {DIM}bluesound-controller volume mute \"Bedroom\"{RESET}")
        print(f"        {DIM}# Mute bedroom{RESET}")
        print(f"      {DIM}bluesound-controller volume reset{RESET}")
        print(f"        {DIM}# Reset all to safe level{RESET}\n")
        
        # Playback Controls
        print(f"  {GREEN}play{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Start or resume playback on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller play \"Living Room\"{RESET}\n")
        
        print(f"  {GREEN}pause{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Pause playback on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller pause \"Living Room\"{RESET}\n")
        
        print(f"  {GREEN}stop{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Stop playback on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller stop \"Living Room\"{RESET}\n")
        
        print(f"  {GREEN}skip{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Skip to next track on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller skip \"Living Room\"{RESET}\n")
        
        print(f"  {GREEN}previous{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Go to previous track on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller previous \"Living Room\"{RESET}\n")
        
        print(f"  {GREEN}toggle{RESET} {DIM}[name]{RESET}")
        print(f"    {DIM}Toggle play/pause state on all or specific devices.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller toggle \"Living Room\"{RESET}\n")
        
        # Queue
        print(f"  {GREEN}queue{RESET} {DIM}[action] [target]{RESET}")
        print(f"    {DIM}Manage playback queue.{RESET}\n")
        print(f"    {BOLD}Actions:{RESET}")
        print(f"      {CYAN}show{RESET}         Show queue (default)")
        print(f"      {CYAN}clear{RESET}        Clear queue")
        print(f"      {CYAN}move <from> <to>{RESET}  Move track in queue\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller queue \"Living Room\"{RESET}")
        print(f"        {DIM}# Show queue{RESET}")
        print(f"      {DIM}bluesound-controller queue clear \"Living Room\"{RESET}")
        print(f"        {DIM}# Clear queue{RESET}")
        print(f"      {DIM}bluesound-controller queue move 3 1 \"Living Room\"{RESET}")
        print(f"        {DIM}# Move track{RESET}\n")
        
        # Inputs
        print(f"  {GREEN}inputs{RESET} {DIM}[target] [input]{RESET}")
        print(f"    {DIM}List or set audio input source.{RESET}\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller inputs \"Living Room\"{RESET}")
        print(f"        {DIM}# List inputs{RESET}")
        print(f"      {DIM}bluesound-controller inputs \"Living Room\" \"Bluetooth\"{RESET}")
        print(f"        {DIM}# Set input{RESET}\n")
        
        # Bluetooth
        print(f"  {GREEN}bluetooth{RESET} {DIM}[target] [mode]{RESET}")
        print(f"    {DIM}Get or set Bluetooth mode.{RESET}\n")
        print(f"    {BOLD}Modes:{RESET} manual, auto, guest, disable\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller bluetooth \"Living Room\"{RESET}")
        print(f"        {DIM}# Show mode{RESET}")
        print(f"      {DIM}bluesound-controller bluetooth \"Living Room\" auto{RESET}")
        print(f"        {DIM}# Set to auto{RESET}\n")
        
        # Presets
        print(f"  {GREEN}presets{RESET} {DIM}[target] [preset_id]{RESET}")
        print(f"    {DIM}List or play presets.{RESET}\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller presets \"Living Room\"{RESET}")
        print(f"        {DIM}# List presets{RESET}")
        print(f"      {DIM}bluesound-controller presets \"Living Room\" 1{RESET}")
        print(f"        {DIM}# Play preset 1{RESET}\n")
        
        # Sync
        print(f"  {GREEN}sync{RESET} {DIM}<action> [args]{RESET}")
        print(f"    {DIM}Manage sync groups for multi-room playback.{RESET}\n")
        print(f"    {BOLD}Actions:{RESET}")
        print(f"      {CYAN}create <master> <slaves>{RESET}  Create sync group")
        print(f"      {CYAN}break [target]{RESET}            Break sync group")
        print(f"      {CYAN}list{RESET}                      List all sync groups\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller sync create \"Living Room\" \"Kitchen,Bedroom\"{RESET}")
        print(f"      {DIM}bluesound-controller sync break \"Living Room\"{RESET}")
        print(f"      {DIM}bluesound-controller sync list{RESET}\n")
        
        # Reboot
        print(f"  {GREEN}reboot{RESET} {DIM}[--soft]{RESET}")
        print(f"    {DIM}Reboot all Bluesound devices on the network.{RESET}")
        print(f"    {YELLOW}⚠️  WARNING: This will interrupt playback on all devices!{RESET}\n")
        print(f"    {BOLD}Options:{RESET}")
        print(f"      {CYAN}--soft{RESET}        Perform soft reboot (less disruptive)\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller reboot{RESET}")
        print(f"        {DIM}# Hard reboot{RESET}")
        print(f"      {DIM}bluesound-controller reboot --soft{RESET}")
        print(f"        {DIM}# Soft reboot{RESET}\n")
        
        # Keychain
        print(f"  {GREEN}keychain{RESET} {DIM}<action>{RESET}")
        print(f"    {DIM}Manage UniFi API key in macOS Keychain (secure storage).{RESET}\n")
        print(f"    {BOLD}Actions:{RESET}")
        print(f"      {CYAN}set{RESET}          Store API key in Keychain")
        print(f"      {CYAN}get{RESET}          Show API key status")
        print(f"      {CYAN}delete{RESET}       Remove API key from Keychain\n")
        print(f"    {CYAN}Examples:{RESET}")
        print(f"      {DIM}bluesound-controller keychain set{RESET}")
        print(f"        {DIM}# Store API key in Keychain{RESET}")
        print(f"      {DIM}bluesound-controller keychain get{RESET}")
        print(f"        {DIM}# Check if API key is stored{RESET}")
        print(f"      {DIM}bluesound-controller keychain delete{RESET}")
        print(f"        {DIM}# Remove API key from Keychain{RESET}\n")
        print(f"    {DIM}Note: Keychain values take precedence over config.json{RESET}\n")
        
        # Environment Variables
        print(f"{BOLD}ENVIRONMENT VARIABLES:{RESET}\n")
        print(f"  {CYAN}BLUESOUND_DEBUG{RESET}={DIM}1{RESET}")
        print(f"    Enable debug logging. Logs are written to:")
        print(f"    {DIM}~/.config/bluesound-controller/bluesound-controller.log{RESET}\n")
        
        # Configuration
        print(f"{BOLD}CONFIGURATION:{RESET}\n")
        print(f"  Configuration file: {CYAN}~/.config/bluesound-controller/config.json{RESET}\n")
        print(f"  {DIM}Edit this file to configure:{RESET}")
        print(f"    {DIM}• Discovery method (mdns, lsdp, or both){RESET}")
        print(f"    {DIM}• Discovery timeout and cache settings{RESET}")
        print(f"    {DIM}• Default safe volume level{RESET}")
        print(f"    {DIM}• UniFi Controller integration (optional){RESET}\n")
        print(f"  {BOLD}API Key Storage:{RESET}")
        print(f"    {DIM}• Recommended: Store API key in macOS Keychain (secure){RESET}")
        print(f"    {DIM}  Use: {CYAN}bluesound-controller keychain set{RESET}")
        print(f"    {DIM}• Alternative: Store in config.json (less secure){RESET}\n")
        
        # Footer
        print(f"{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{DIM}For more information, see: https://github.com/tbaur/bluesound-controller{RESET}\n")
        
        print(f"{BOLD}DEVELOPMENT:{RESET}\n")
        print(f"  {CYAN}--run-code-tests{RESET}")
        print(f"    {DIM}Run test suite and automatically update documentation with results.{RESET}")
        print(f"    {DIM}Updates README.md and docs/README-DETAILED.md with test count and coverage.{RESET}\n")
        print(f"    {CYAN}Example:{RESET} {DIM}bluesound-controller --run-code-tests{RESET}\n")
    
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
        print(f"\n{BOLD}Volume Control: {args.target or 'all'}{RESET}")
        print("-" * 40)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as executor:
            future_to_ip = {executor.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for future in as_completed(future_to_ip):
                d = future.result()
                if d.name == 'Unknown':
                    continue
                if args.target != 'all' and args.target.lower() not in d.name.lower():
                    continue
                
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
        
        targets = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for f in as_completed(f_map):
                d = f.result()
                if d.name != 'Unknown':
                    if not target or target.lower() in d.name.lower():
                        targets.append(d)
        
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
        
        tgt_ip = None
        with ThreadPoolExecutor(max_workers=10) as ex:
            f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
            for f in as_completed(f_map):
                d = f.result()
                if target.lower() in d.name.lower():
                    tgt_ip = d.ip
                    break
        
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
    
    def play(self, args) -> None:
        """Start/resume playback on all or matching devices."""
        target = args.target
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}Starting Playback on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            res = self.ctl.play(d.ip)
            state = f"{GREEN}PLAYING{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
    def stop(self, args) -> None:
        """Stop playback on all or matching devices."""
        target = args.target
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}Stopping Playback on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            res = self.ctl.stop(d.ip)
            state = f"{GREEN}STOPPED{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
    def skip(self, args) -> None:
        """Skip to next track on all or matching devices."""
        target = args.target
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}Skipping Track on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            res = self.ctl.skip(d.ip)
            state = f"{GREEN}SKIPPED{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
    def previous(self, args) -> None:
        """Go to previous track on all or matching devices."""
        target = args.target
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}Previous Track on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            res = self.ctl.previous(d.ip)
            state = f"{GREEN}PREVIOUS{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
    def toggle(self, args) -> None:
        """Toggle play/pause state on all or matching devices."""
        target = args.target
        scope = f"'{target}'" if target else "all devices"
        print(f"\n{BOLD}Toggling Playback on {scope}...{RESET}")
        
        targets = self._get_matching_devices(target)
        
        if not targets:
            print(f"{RED}No matching devices found.{RESET}")
            return
        
        print("-" * 40)
        for d in targets:
            # Toggle based on current state
            if d.state in ['play', 'stream', 'connecting']:
                res = self.ctl.pause_device(d.ip)
                state = f"{YELLOW}PAUSED{RESET}" if res else f"{RED}ERROR{RESET}"
            else:
                res = self.ctl.play(d.ip)
                state = f"{GREEN}PLAYING{RESET}" if res else f"{RED}ERROR{RESET}"
            print(f"[{state}] {d.name}")
        print()
    
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
            
            # Find devices
            devices = {}
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as ex:
                f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
                for f in as_completed(f_map):
                    d = f.result()
                    if d.name != 'Unknown':
                        devices[d.name.lower()] = d
            
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
            targets = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as ex:
                f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
                for f in as_completed(f_map):
                    d = f.result()
                    if d.name != 'Unknown':
                        if not target or target.lower() in d.name.lower():
                            targets.append(d)
            
            if not targets:
                print(f"{RED}No matching devices found.{RESET}")
                return
            
            print(f"\n{BOLD}Breaking sync groups...{RESET}")
            print("-" * 40)
            for d in targets:
                # Break sync by removing all slaves (get from sync status)
                # For now, just remove from any master
                res = Network.get(f"http://{d.ip}:{BLUOS_PORT}/Sync?remove={d.ip}", timeout=2)
                state = f"{GREEN}BROKEN{RESET}" if res else f"{YELLOW}NO SYNC{RESET}"
                print(f"[{state}] {d.name}")
            print()
        
        elif action == 'list':
            print(f"\n{BOLD}Sync Groups:{RESET}")
            print("-" * 60)
            devices = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_DISCOVERY) as ex:
                f_map = {ex.submit(self.ctl.get_device_info, ip): ip for ip in self.ctl.ips}
                for f in as_completed(f_map):
                    d = f.result()
                    if d.name != 'Unknown':
                        devices.append(d)
            
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


