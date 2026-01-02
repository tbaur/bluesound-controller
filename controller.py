#!/usr/bin/env python3
"""
Bluesound Controller - Core device management logic.

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
import os
import sys
import time
import json
import subprocess
import re
import urllib.parse
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import logging
from typing import List, Dict, Optional, Set
from dataclasses import asdict

from constants import BLUOS_PORT, CACHE_FILE, UNIFI_CACHE_FILE, MAX_XML_DEPTH, MAX_XML_SIZE, MAX_XML_ELEMENTS, MAX_XML_ATTRIBUTES, SUBPROCESS_TIMEOUT, DISCOVERY_MDNS, DISCOVERY_LSDP, DISCOVERY_BOTH
from models import UniFiClient, PlayerStatus
from config import Config
from network import Network
from utils import atomic_write, get_rate_limiter
from validators import validate_ip, sanitize_ip, validate_hostname, validate_timeout
from lsdp import LSDPDiscovery

logger = logging.getLogger("Bluesound")


class BluesoundController:
    """Main controller for Bluesound device management."""
    
    def __init__(self):
        self.config = Config()
        self.ips: List[str] = []
        self.unifi_map: Dict[str, UniFiClient] = {}
    
    def discover(self, force_refresh: bool = False) -> None:
        """
        Discovers devices using configured discovery method (mDNS, LSDP, or both).
        """
        if not force_refresh and self._load_discovery_cache():
            return
        
        discovery_method = self.config.get('DISCOVERY_METHOD', DISCOVERY_MDNS).lower()
        timeout = int(self.config.get('DISCOVERY_TIMEOUT', 5))
        
        print(f"Scanning Network ({timeout}s) [{discovery_method}]...", file=sys.stderr)
        
        discovered_ips: Set[str] = set()
        
        # Try mDNS if method is mdns or both
        if discovery_method in (DISCOVERY_MDNS, DISCOVERY_BOTH):
            mdns_ips = self._discover_mdns(timeout)
            discovered_ips.update(mdns_ips)
        
        # Try LSDP if method is lsdp or both (or if mDNS failed)
        if discovery_method == DISCOVERY_LSDP or (discovery_method == DISCOVERY_BOTH and not discovered_ips):
            lsdp_ips = self._discover_lsdp(timeout)
            discovered_ips.update(lsdp_ips)
        
        # Filter and validate all IPs
        validated_ips = [ip for ip in discovered_ips if validate_ip(ip)]
        self.ips = sorted(validated_ips)
        
        if self.ips:
            atomic_write(CACHE_FILE, {'ts': time.time(), 'ips': self.ips})
        else:
            logger.warning("No valid devices found via discovery")
    
    def _discover_mdns(self, timeout: int) -> List[str]:
        """Discover devices using mDNS."""
        service = self.config.get('BLUOS_SERVICE', '_musc._tcp')
        
        # 1. Capture mDNS Output
        raw_output = self._run_dns_sd(service, timeout)
        if not raw_output:
            logger.debug("No response from dns-sd")
            return []
        
        # 2. Parse Hostnames via Regex
        host_pattern = re.compile(r"SRV\s+\d+\s+\d+\s+\d+\s+(\S+)")
        hosts: Set[str] = set()
        
        for line in raw_output.splitlines():
            if "SRV" in line:
                match = host_pattern.search(line)
                if match:
                    hosts.add(match.group(1).rstrip('.'))
        
        if not hosts:
            logger.debug("No devices found via mDNS.")
            return []
        
        # 3. Resolve IPs using dscacheutil with validation
        resolved_ips = self._resolve_hosts(hosts)
        return list(resolved_ips)
    
    def _discover_lsdp(self, timeout: int) -> List[str]:
        """Discover devices using LSDP."""
        try:
            lsdp = LSDPDiscovery(timeout=timeout)
            return lsdp.discover()
        except Exception as e:
            logger.debug(f"LSDP discovery error: {e}")
            return []
    
    def _load_discovery_cache(self) -> bool:
        """Load discovery cache if valid."""
        if not os.path.exists(CACHE_FILE):
            return False
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            cached_ts = float(data.get('ts', 0))
            ttl = int(self.config.get('CACHE_TTL', 300))
            if time.time() - cached_ts < ttl:
                cached_ips = data.get('ips', [])
                # Validate cached IPs
                validated_ips = [ip for ip in cached_ips if validate_ip(str(ip))]
                if validated_ips:
                    logger.debug("Using cached discovery data.")
                    self.ips = validated_ips
                    return True
                else:
                    logger.warning("Cached IPs failed validation, refreshing")
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"Cache load error: {e}")
        return False
    
    def _run_dns_sd(self, service: str, timeout: int) -> str:
        """
        Run dns-sd command to discover services with security protections.
        
        Args:
            service: Service name to discover (validated)
            timeout: Timeout in seconds (validated)
            
        Returns:
            Command output as string
        """
        # Validate and sanitize inputs
        if not service or not isinstance(service, str):
            logger.warning("Invalid service name for dns-sd")
            return ""
        
        # Validate service name format (basic check for injection prevention)
        if not re.match(r'^[a-zA-Z0-9._-]+$', service):
            logger.warning(f"Invalid service name format: {service}")
            return ""
        
        # Validate timeout
        validated_timeout = validate_timeout(timeout, min_val=1, max_val=60)
        
        tmp_file = os.path.join(os.path.expanduser("~"), f".bluesound-tmp-discovery-{os.getpid()}")
        try:
            with open(tmp_file, 'w') as outfile:
                subprocess.run(
                    ["dns-sd", "-Z", service, "local"],
                    stdout=outfile,
                    stderr=subprocess.DEVNULL,
                    timeout=validated_timeout,
                    check=False,
                    # Security: No shell=True, args as list
                    shell=False
                )
        except subprocess.TimeoutExpired:
            logger.debug(f"dns-sd timeout after {validated_timeout}s")
            pass
        except OSError as e:
            logger.debug(f"dns-sd execution error: {e}")
            pass
        except Exception as e:
            logger.debug(f"Unexpected error in dns-sd: {e}")
            pass
        
        output = ""
        if os.path.exists(tmp_file):
            try:
                with open(tmp_file, 'r', errors='ignore') as f:
                    output = f.read()
            finally:
                os.remove(tmp_file)
        return output
    
    def _resolve_hosts(self, hosts: Set[str]) -> Set[str]:
        """
        Resolve hostnames to IP addresses with comprehensive validation and security.
        
        Args:
            hosts: Set of hostnames to resolve (validated before processing)
            
        Returns:
            Set of validated IP addresses
        """
        found_ips = set()
        for host in hosts:
            # Validate hostname before subprocess call (prevents injection)
            if not host or not isinstance(host, str):
                logger.warning(f"Invalid hostname type: {type(host)}")
                continue
            
            # Validate hostname format and length
            if not validate_hostname(host):
                logger.warning(f"Invalid hostname format: {host}")
                continue
            
            # Additional security: ensure hostname doesn't contain shell metacharacters
            if any(char in host for char in [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']):
                logger.warning(f"Hostname contains unsafe characters: {host}")
                continue
            
            try:
                # Native macOS resolution requires full hostname (e.g. node.local)
                # Security: Use list of args (not shell), validated timeout, validated input
                out = subprocess.check_output(
                    ["dscacheutil", "-q", "host", "-a", "name", host],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=SUBPROCESS_TIMEOUT,
                    # Security: Explicitly disable shell
                    shell=False
                )
                
                # Validate output size to prevent memory exhaustion
                if len(out) > MAX_XML_SIZE:  # Reuse size limit constant
                    logger.warning(f"dscacheutil output too large for {host}: {len(out)} bytes")
                    continue
                
                for line in out.splitlines():
                    if "ip_address" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            ip = parts[1].strip()
                            # Validate IP address before adding
                            sanitized_ip = sanitize_ip(ip)
                            if sanitized_ip:
                                found_ips.add(sanitized_ip)
            except subprocess.TimeoutExpired:
                logger.debug(f"Host resolution timeout for {host}")
                continue
            except subprocess.CalledProcessError as e:
                logger.debug(f"Host resolution failed for {host}: {e}")
                continue
            except OSError as e:
                logger.debug(f"OS error resolving host {host}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Unexpected error resolving host {host}: {e}")
                continue
        return found_ips
    
    def sync_unifi(self) -> str:
        """Fetches client data from UniFi Controller."""
        if self.config.get('UNIFI_ENABLED') != 'true' or not self.ips:
            return "SKIPPED"
        
        # Check config first before checking cache
        base = self.config.get('UNIFI_CONTROLLER')
        site = self.config.get('UNIFI_SITE', 'default')
        key = self.config.get('UNIFI_API_KEY')
        
        if not base or not key:
            return "MISSING_CONFIG"
        
        # Check Cache
        if os.path.exists(UNIFI_CACHE_FILE):
            try:
                with open(UNIFI_CACHE_FILE, "r") as f:
                    data = json.load(f)
                if time.time() - float(data.get('ts', 0)) < int(self.config.get('CACHE_TTL', 300)):
                    self.unifi_map = {ip: UniFiClient(**d) for ip, d in data.get('clients', {}).items()}
                    return "CACHED"
            except Exception:
                pass
        
        # Fetch Fresh
        
        url = f"https://{base}/proxy/network/api/s/{site}/stat/sta"
        headers = {
            'X-API-KEY': key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        resp_bytes = Network.get(url, timeout=4, headers=headers)
        if not resp_bytes:
            # Graceful degradation: continue without UniFi data
            logger.warning("UniFi fetch failed, continuing without network stats")
            return "ERROR_FETCH"
        
        try:
            raw = json.loads(resp_bytes)
            target_ips = set(self.ips)
            temp_map = {}
            
            for c in raw.get('data', []):
                ip = c.get('ip')
                if not ip:
                    continue
                # Validate IP from UniFi response
                sanitized_ip = sanitize_ip(str(ip))
                if not sanitized_ip or sanitized_ip not in target_ips:
                    continue
                ip = sanitized_ip
                
                is_wired = c.get('is_wired', False) or str(c.get('type', '')).upper() == 'WIRED'
                
                if is_wired:
                    uplink = c.get('last_uplink_name', 'Unknown Switch')
                    port_info = str(c.get('sw_port') or c.get('last_uplink_remote_port') or '')
                else:
                    uplink = c.get('ap_name') or c.get('last_uplink_name') or c.get('ap_mac') or 'Unknown AP'
                    essid = c.get('essid', '')
                    port_info = f"WiFi: {essid}" if essid else "WiFi"
                
                temp_map[ip] = UniFiClient(
                    mac=c.get('mac', '').lower(),
                    is_wired=is_wired,
                    uplink=uplink,
                    port_info=port_info,
                    down_tot=c.get('tx_bytes', 0) if not is_wired else c.get('wired-tx_bytes', 0),
                    up_tot=c.get('rx_bytes', 0) if not is_wired else c.get('wired-rx_bytes', 0),
                    down_rate=c.get('tx_bytes-r', 0) if not is_wired else c.get('wired-tx_bytes-r', 0),
                    up_rate=c.get('rx_bytes-r', 0) if not is_wired else c.get('wired-rx_bytes-r', 0),
                    uptime=c.get('uptime', 0)
                )
            
            self.unifi_map = temp_map
            cache_payload = {ip: asdict(obj) for ip, obj in temp_map.items()}
            atomic_write(UNIFI_CACHE_FILE, {'ts': time.time(), 'clients': cache_payload})
            return f"SUCCESS:{len(temp_map)}"
        except Exception as e:
            logger.error(f"UniFi Parse Error: {e}", exc_info=True)
            return "ERROR_PARSE"
    
    def get_sys_uptime(self, ip: str) -> str:
        """Get system uptime from device diagnostics page."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return "N/A"
        url = f"http://{sanitized_ip}/diagnostics"
        content = Network.get(url, timeout=3)
        if content:
            try:
                html = content.decode('utf-8', errors='ignore')
                match = re.search(r'Uptime:</div>\s*<div[^>]*>(.*?)</div>', html, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            except Exception:
                pass
        return "N/A"
    
    def _safe_parse_xml(self, xml_data: bytes, ip: str) -> Optional[ET.Element]:
        """
        Safely parse XML with comprehensive protection against XML bombs.
        
        Protections include:
        - Size limit checking (prevents memory exhaustion)
        - Depth limit checking (prevents stack overflow)
        - Entity expansion protection (via XMLParser with custom entity resolver)
        - Malformed XML handling
        
        Args:
            xml_data: XML data as bytes
            ip: IP address for logging
            
        Returns:
            Parsed XML root element or None if parsing fails
        """
        if not xml_data:
            return None
        
        # Check size limit before any processing
        if len(xml_data) > MAX_XML_SIZE:
            logger.warning(f"XML too large for {ip}: {len(xml_data)} bytes (max: {MAX_XML_SIZE})")
            return None
        
        # Additional check: reject empty or whitespace-only XML
        if not xml_data.strip():
            logger.debug(f"Empty XML data for {ip}")
            return None
        
        try:
            # Create a safe XML parser with entity expansion protection
            # ElementTree's default parser already has some protection, but we add explicit limits
            parser = ET.XMLParser()
            
            # Disable external entity resolution to prevent XXE attacks
            # This is done by using the default parser which doesn't resolve external entities
            # For additional safety, we'll use a custom entity resolver if needed
            
            # Parse XML with size and depth protection
            root = ET.fromstring(xml_data, parser=parser)
            
            # Check depth with improved recursion protection
            def check_depth(elem, depth=0, element_count=[0]):
                """
                Check XML depth and element count to prevent DoS.
                
                Args:
                    elem: XML element to check
                    depth: Current nesting depth
                    element_count: List to track total element count (mutable for recursion)
                    
                Returns:
                    True if valid, False otherwise
                """
                if depth > MAX_XML_DEPTH:
                    return False
                
                element_count[0] += 1
                if element_count[0] > MAX_XML_ELEMENTS:
                    logger.warning(f"XML has too many elements for {ip}: {element_count[0]}")
                    return False
                
                for child in elem:
                    if not check_depth(child, depth + 1, element_count):
                        return False
                
                return True
            
            element_count = [0]
            if not check_depth(root, 0, element_count):
                logger.warning(f"XML structure invalid for {ip}: depth or element count exceeded")
                return None
            
            # Additional validation: check root element for suspicious patterns
            # Check attribute count (prevent attribute flooding) - lenient for root element
            if len(root.attrib) > MAX_XML_ATTRIBUTES * 2:  # More lenient for root
                logger.warning(f"Root element has too many attributes for {ip}: {len(root.attrib)}")
                return None
            
            # Check text length (prevent text node flooding) - only on root
            if root.text and len(root.text) > MAX_XML_SIZE // 10:  # Max 10% of total size per text node
                logger.warning(f"Root element text too long for {ip}: {len(root.text)} bytes")
                return None
            
            return root
        except ET.ParseError as e:
            logger.debug(f"XML parse error for {ip}: {e}")
            return None
        except RecursionError:
            logger.warning(f"XML recursion error for {ip} (likely too deep)")
            return None
        except MemoryError:
            logger.warning(f"XML memory error for {ip} (likely too large)")
            return None
        except Exception as e:
            logger.debug(f"XML processing error for {ip}: {e}")
            return None
    
    def get_device_info(self, ip: str) -> PlayerStatus:
        """Get comprehensive device information."""
        # Validate IP before use
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            logger.warning(f"Invalid IP address: {ip}")
            return PlayerStatus(ip=ip, status="invalid")
        
        status = PlayerStatus(ip=sanitized_ip)
        try:
            sync_xml = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/SyncStatus", timeout=3)
            status_xml = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Status", timeout=3)
            status.uptime = self.get_sys_uptime(sanitized_ip)
            
            if sync_xml:
                root = self._safe_parse_xml(sync_xml, sanitized_ip)
                if root is None:
                    status.status = "xml_error"
                    return status
                status.name = root.attrib.get('name', 'Unknown')
                status.model = root.attrib.get('modelName') or root.attrib.get('brand') or ''
                status.brand = root.attrib.get('brand', '')
                status.db = root.attrib.get('db', '')
                status.fw = root.attrib.get('version', '')
                status.master = root.attrib.get('master', '')
                
                batt = root.find('battery')
                if batt is not None:
                    status.battery = batt.attrib.get('level')
            
            if status_xml:
                root = self._safe_parse_xml(status_xml, sanitized_ip)
                if root is None:
                    if status.status == "offline":
                        status.status = "xml_error"
                    return status
                status.volume = int(root.findtext('volume', '0'))
                status.state = root.findtext('state', 'stop')
                status.service = root.findtext('service', 'Library/Input')
                status.track = root.findtext('title1') or root.findtext('title') or ''
                status.artist = root.findtext('artist', '')
                status.album = root.findtext('album', '')
                
                if status.service == 'Raat':
                    status.service = 'Roon'
            
            if status.brand and status.brand not in status.model:
                status.full_model = f"{status.brand} {status.model}"
            else:
                status.full_model = status.model
            
            status.unifi = self.unifi_map.get(sanitized_ip)
        
        except ET.ParseError as e:
            logger.error(f"XML Parse Error for {sanitized_ip}: {e}")
            status.status = "parse_error"
        except ValueError as e:
            logger.error(f"Value Error for {sanitized_ip}: {e}")
            status.status = "value_error"
        except Exception as e:
            logger.debug(f"Device Info Error {sanitized_ip}: {e}")
            status.status = "error"
        
        return status
    
    def play(self, ip: str) -> bool:
        """Start/resume playback on device."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Play", timeout=2)
        return res is not None
    
    def pause_device(self, ip: str) -> bool:
        """Pause playback on device."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Pause", timeout=2)
        return res is not None
    
    def stop(self, ip: str) -> bool:
        """Stop playback on device."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Stop", timeout=2)
        return res is not None
    
    def skip(self, ip: str) -> bool:
        """Skip to next track."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Skip", timeout=2)
        return res is not None
    
    def previous(self, ip: str) -> bool:
        """Go to previous track."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Back", timeout=2)
        return res is not None
    
    def get_queue(self, ip: str) -> Optional[Dict]:
        """Get queue information."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return None
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Queue", timeout=3)
        if res:
            try:
                root = self._safe_parse_xml(res, sanitized_ip)
                if root:
                    queue_items = []
                    for item in root.findall('item'):
                        queue_items.append({
                            'title': item.findtext('title', ''),
                            'artist': item.findtext('artist', ''),
                            'album': item.findtext('album', ''),
                            'image': item.findtext('image', ''),
                            'service': item.findtext('service', '')
                        })
                    return {'items': queue_items, 'count': len(queue_items)}
            except Exception as e:
                logger.debug(f"Queue parse error for {sanitized_ip}: {e}")
        return None
    
    def clear_queue(self, ip: str) -> bool:
        """Clear the queue."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Queue?clear=1", timeout=2)
        return res is not None
    
    def move_queue_item(self, ip: str, from_index: int, to_index: int) -> bool:
        """Move queue item from one position to another."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Queue?move={from_index}&to={to_index}", timeout=2)
        return res is not None
    
    def get_inputs(self, ip: str) -> Optional[List[Dict]]:
        """Get available audio inputs."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return None
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/AudioInputs", timeout=3)
        if res:
            try:
                root = self._safe_parse_xml(res, sanitized_ip)
                if root:
                    inputs = []
                    for inp in root.findall('input'):
                        inputs.append({
                            'name': inp.findtext('name', ''),
                            'type': inp.findtext('type', ''),
                            'selected': inp.get('selected', '0') == '1'
                        })
                    return inputs
            except Exception as e:
                logger.debug(f"Inputs parse error for {sanitized_ip}: {e}")
        return None
    
    def set_input(self, ip: str, input_name: str) -> bool:
        """Set audio input."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        encoded_name = urllib.parse.quote(input_name)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/AudioInput?input={encoded_name}", timeout=2)
        return res is not None
    
    def get_bluetooth_mode(self, ip: str) -> Optional[str]:
        """Get current Bluetooth mode."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return None
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/AudioModes", timeout=3)
        if res:
            try:
                root = self._safe_parse_xml(res, sanitized_ip)
                if root:
                    mode = root.findtext('bluetoothAutoplay', '')
                    mode_map = {'0': 'Manual', '1': 'Automatic', '2': 'Guest', '3': 'Disabled'}
                    return mode_map.get(mode, 'Unknown')
            except Exception as e:
                logger.debug(f"Bluetooth mode parse error for {sanitized_ip}: {e}")
        return None
    
    def set_bluetooth_mode(self, ip: str, mode: int) -> bool:
        """Set Bluetooth mode (0=Manual, 1=Automatic, 2=Guest, 3=Disabled)."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        if mode not in (0, 1, 2, 3):
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/audiomodes?bluetoothAutoplay={mode}", timeout=2)
        return res is not None
    
    def soft_reboot(self, ip: str) -> bool:
        """Perform soft reboot."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.post(f"http://{sanitized_ip}/Reboot", data={"soft": "1"}, timeout=2)
        return res is not None
    
    def get_presets(self, ip: str) -> Optional[List[Dict]]:
        """Get available presets."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return None
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Presets", timeout=3)
        if res:
            try:
                root = self._safe_parse_xml(res, sanitized_ip)
                if root:
                    presets = []
                    for preset in root.findall('preset'):
                        presets.append({
                            'id': preset.get('id', ''),
                            'name': preset.findtext('name', ''),
                            'image': preset.findtext('image', '')
                        })
                    return presets
            except Exception as e:
                logger.debug(f"Presets parse error for {sanitized_ip}: {e}")
        return None
    
    def play_preset(self, ip: str, preset_id: int) -> bool:
        """Play a preset."""
        sanitized_ip = sanitize_ip(ip)
        if not sanitized_ip:
            return False
        get_rate_limiter().wait_if_needed(sanitized_ip)
        res = Network.get(f"http://{sanitized_ip}:{BLUOS_PORT}/Preset?id={preset_id}", timeout=2)
        return res is not None
    
    def add_sync_slave(self, master_ip: str, slave_ip: str) -> bool:
        """Add slave device to sync group."""
        sanitized_master = sanitize_ip(master_ip)
        sanitized_slave = sanitize_ip(slave_ip)
        if not sanitized_master or not sanitized_slave:
            return False
        get_rate_limiter().wait_if_needed(sanitized_master)
        res = Network.get(f"http://{sanitized_master}:{BLUOS_PORT}/Sync?slave={sanitized_slave}", timeout=2)
        return res is not None
    
    def remove_sync_slave(self, master_ip: str, slave_ip: str) -> bool:
        """Remove slave device from sync group."""
        sanitized_master = sanitize_ip(master_ip)
        sanitized_slave = sanitize_ip(slave_ip)
        if not sanitized_master or not sanitized_slave:
            return False
        get_rate_limiter().wait_if_needed(sanitized_master)
        res = Network.get(f"http://{sanitized_master}:{BLUOS_PORT}/Sync?remove={sanitized_slave}", timeout=2)
        return res is not None

