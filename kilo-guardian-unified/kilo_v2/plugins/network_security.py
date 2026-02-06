"""
Network Security Plugin - Backend for Browser Extension
Handles network scanning, port scanning, CVE checking, IoT device monitoring
Integrates with Browser Security Shield for comprehensive user protection
"""

import json
import socket
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from plugins.base_plugin import BasePlugin
from plugins.browser_security_shield import BrowserSecurityShieldExtension


class NetworkSecurityPlugin(BasePlugin):
    """
    Network security monitoring backend.
    Integrates with browser extension for comprehensive network protection.
    """

    def __init__(self):
        super().__init__()
        self.discovered_devices = []
        self.security_stats = {
            "openPorts": 0,
            "vulnerabilities": 0,
            "iotDevices": 0,
            "blockedThreats": 0,
        }
        self.vpn_connected = False
        self.scan_in_progress = False

        # Runtime configuration (can be updated via API)
        self.config = {
            "scan_method": "auto",  # auto | nmap | arp | ping
            "enable_port_scan": False,
            "include_offline_devices": True,
            "browser_extension_enabled": True,
            "data_collection": {
                "collect_device_metadata": True,
                "collect_open_ports": False,
                "collect_security_events": True,
                "collect_browser_events": True,
            },
        }
        self._config_lock = threading.RLock()

        # Initialize browser security shield extension
        self.browser_shield = BrowserSecurityShieldExtension(self)

    def get_name(self):
        return "network_security"

    def get_keywords(self):
        return [
            "network",
            "scan",
            "devices",
            "iot",
            "security",
            "port",
            "ports",
            "open ports",
            "vulnerability",
            "cve",
            "exploit",
            "threat",
            "firewall",
            "vpn",
            "proxy",
            "connection",
            "heartbeat",
        ]

    def get_config(self):
        """Return a safe copy of current configuration."""
        with self._config_lock:
            # Shallow copy is sufficient for simple nested dicts
            return json.loads(json.dumps(self.config))

    def update_config(self, updates: Dict) -> Dict:
        """Update runtime configuration with validation."""
        with self._config_lock:
            if not isinstance(updates, dict):
                return self.get_config()

            # Allowed top-level keys
            allowed_keys = {
                "scan_method": {"auto", "nmap", "arp", "ping"},
                "enable_port_scan": {True, False},
                "include_offline_devices": {True, False},
                "browser_extension_enabled": {True, False},
                "data_collection": None,
            }

            for key, value in updates.items():
                if key not in allowed_keys:
                    continue

                if key == "data_collection" and isinstance(value, dict):
                    # Merge selective flags
                    dc = self.config.get("data_collection", {})
                    for dc_key in [
                        "collect_device_metadata",
                        "collect_open_ports",
                        "collect_security_events",
                        "collect_browser_events",
                    ]:
                        if dc_key in value:
                            dc[dc_key] = bool(value[dc_key])
                    self.config["data_collection"] = dc
                else:
                    allowed_values = allowed_keys[key]
                    if allowed_values is None or value in allowed_values:
                        self.config[key] = value

            return self.get_config()

    def run(self, query):
        """Main dispatcher for network security commands."""
        query_lower = query.lower()

        # Network scan
        if "scan" in query_lower and "network" in query_lower:
            return self._handle_network_scan()

        # Security check
        elif "security" in query_lower and "check" in query_lower:
            return self._handle_security_check()

        # Device list
        elif "devices" in query_lower or "list" in query_lower:
            return self._list_devices()

        # VPN status
        elif "vpn" in query_lower:
            return self._handle_vpn_status()

        # Port scan
        elif "port" in query_lower:
            return self._handle_port_scan(query)

        else:
            return {
                "type": "network_security_help",
                "content": {
                    "message": "Network Security Monitor",
                    "description": "Comprehensive network device monitoring and security scanning",
                    "commands": [
                        "scan network - Discover all devices on local network",
                        "security check - Run port scan and CVE checks",
                        "list devices - Show discovered network devices",
                        "vpn status - Check VPN connection status",
                        "scan ports [ip] - Scan specific device ports",
                    ],
                    "features": [
                        "🔍 Network device discovery",
                        "🔒 Port scanning",
                        "🛡️ CVE vulnerability checking",
                        "📡 IoT device monitoring",
                        "🌐 VPN status tracking",
                        "💻 Browser extension integration",
                    ],
                    "integration": {
                        "browser_extension": "Install the Kilo Guardian browser extension",
                        "extension_path": "browser_extension/",
                        "api_endpoints": [
                            "POST /api/network/scan - Network scan",
                            "POST /api/security/check - Security check",
                            "POST /api/network/heartbeat - Heartbeat",
                            "POST /api/vpn/status - VPN status update",
                        ],
                    },
                    "config": self.get_config(),
                },
            }

    def _handle_network_scan(self):
        """
        Perform network scan to discover devices.

        METHODS:
        1. ARP scan (fastest, local network only)
        2. Ping sweep (works across subnets)
        3. nmap (most detailed, requires install)

        PRIVACY: Scans LOCAL network only, does not access external networks
        """
        if self.scan_in_progress:
            return {
                "type": "scan_in_progress",
                "content": {
                    "message": "Network scan already in progress",
                    "status": "scanning",
                },
            }

        self.scan_in_progress = True

        try:
            with self._config_lock:
                scan_method = self.config.get("scan_method", "auto")
                include_offline = self.config.get("include_offline_devices", True)

            devices = []

            # Choose scan method based on config
            if scan_method == "nmap":
                devices = self._scan_with_nmap()
            elif scan_method == "arp":
                devices = self._scan_with_arp()
            elif scan_method == "ping":
                devices = self._scan_with_ping()
            else:
                # Auto: try nmap -> arp -> ping
                devices = self._scan_with_nmap()
                if not devices:
                    devices = self._scan_with_arp()
                if not devices:
                    devices = self._scan_with_ping()

            if not include_offline:
                devices = [d for d in devices if d.get("online")]

            self.discovered_devices = devices

            # Update stats
            self.security_stats["iotDevices"] = len(
                [d for d in devices if d.get("type") == "iot"]
            )

            return {
                "type": "network_scan_complete",
                "content": {
                    "message": f"Network scan complete: {len(devices)} devices found",
                    "devices": devices,
                    "stats": self.security_stats,
                    "scan_method": "nmap" if devices else "fallback",
                },
            }

        except Exception as e:
            return {
                "type": "error",
                "content": {
                    "message": f"Network scan failed: {str(e)}",
                    "suggestion": "Ensure you have network scanning tools installed (nmap, arp-scan)",
                },
            }
        finally:
            self.scan_in_progress = False

    def _scan_with_nmap(self):
        """
        Scan network using nmap.

        REQUIRES: nmap installed (sudo apt install nmap)
        Uses a lightweight ping sweep (-sn) and parses greppable output (-oG).
        """
        # Check if nmap is installed (try flatpak-spawn first, then direct)
        nmap_cmd = None
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "which", "nmap"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                nmap_cmd = ["flatpak-spawn", "--host", "nmap"]
        except Exception:
            pass

        if not nmap_cmd:
            try:
                result = subprocess.run(
                    ["which", "nmap"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    nmap_cmd = ["nmap"]
                else:
                    return []
            except Exception as e:
                print(f"nmap check failed: {e}")
                return []

        # Detect local /24 network
        def _detect_network_cidr():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ".".join(ip.split(".")[:3]) + ".0/24"
            except Exception:
                return "192.168.1.0/24"

        network_range = _detect_network_cidr()
        cmd = nmap_cmd + ["-sn", "-oG", "-", network_range]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        except Exception as e:
            print(f"nmap execution failed: {e}")
            return []

        if result.returncode != 0:
            return []

        devices = []
        current_device = None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Host:"):
                parts = line.split()
                ip = parts[1]
                current_device = {
                    "ip": ip,
                    "mac": "unknown",
                    "name": self._resolve_hostname(ip),
                    "online": "Status: Up" in line,
                    "type": "unknown",
                    "openPorts": [],
                }
                devices.append(current_device)
            if "MAC Address" in line and current_device:
                try:
                    mac_section = line.split("MAC Address:")[1].strip()
                    mac = mac_section.split()[0]
                    vendor = (
                        mac_section.split("(")[-1].split(")")[0]
                        if "(" in mac_section
                        else ""
                    )
                    current_device["mac"] = mac
                    current_device["type"] = self._identify_device_type(vendor)
                except Exception:
                    pass

        return devices

    def _scan_with_arp(self):
        """
        Scan network using ARP table.
        Works on local network without requiring root.
        """
        devices = []

        try:
            # Get ARP table
            if self._is_linux():
                result = subprocess.run(
                    ["arp", "-a"], capture_output=True, text=True, timeout=10
                )

                for line in result.stdout.split("\n"):
                    # Parse ARP output: hostname (ip) at mac [ether] on interface
                    if "(" in line and ")" in line:
                        parts = line.split()
                        ip = line.split("(")[1].split(")")[0]

                        # Extract MAC if present
                        mac = "unknown"
                        for part in parts:
                            if ":" in part and len(part) == 17:  # MAC address format
                                mac = part
                                break

                        # Hostname
                        hostname = parts[0] if parts else "Unknown"

                        device = {
                            "ip": ip,
                            "mac": mac,
                            "name": hostname,
                            "online": True,
                            "type": self._identify_device_type(mac),
                            "openPorts": [],
                            "vulnerabilities": 0,
                        }
                        devices.append(device)

            elif self._is_windows():
                result = subprocess.run(
                    ["arp", "-a"], capture_output=True, text=True, timeout=10
                )

                for line in result.stdout.split("\n"):
                    if "dynamic" in line.lower() or "static" in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1] if len(parts) > 1 else "unknown"

                            device = {
                                "ip": ip,
                                "mac": mac,
                                "name": self._resolve_hostname(ip),
                                "online": True,
                                "type": self._identify_device_type(mac),
                                "openPorts": [],
                                "vulnerabilities": 0,
                            }
                            devices.append(device)

        except Exception as e:
            print(f"ARP scan failed: {e}")

        return devices

    def _scan_with_ping(self):
        """
        Ping sweep to find active devices.
        Slowest method but works everywhere.
        """
        devices = []

        try:
            # Get local IP and network range
            local_ip = socket.gethostbyname(socket.gethostname())
            network_prefix = ".".join(local_ip.split(".")[0:3])

            print(f"Ping scanning {network_prefix}.0/24...")

            # Ping common IP range (1-254)
            # In production, use threading for faster scanning
            for i in range(1, 255):
                ip = f"{network_prefix}.{i}"

                # Quick ping (1 packet, 1 second timeout)
                ping_cmd = (
                    ["ping", "-c", "1", "-W", "1", ip]
                    if self._is_linux()
                    else ["ping", "-n", "1", "-w", "1000", ip]
                )

                result = subprocess.run(
                    ping_cmd, capture_output=True, text=True, timeout=2
                )

                if result.returncode == 0:
                    device = {
                        "ip": ip,
                        "mac": "unknown",
                        "name": self._resolve_hostname(ip),
                        "online": True,
                        "type": "unknown",
                        "openPorts": [],
                        "vulnerabilities": 0,
                    }
                    devices.append(device)
                    print(f"Found device: {ip}")

        except Exception as e:
            print(f"Ping scan failed: {e}")

        return devices

    def _identify_device_type(self, mac_or_vendor):
        """
        Identify device type based on MAC vendor or other info.

        Common IoT device vendors:
        - Nest, Ring, Wyze: cameras
        - Philips, LIFX: smart lights
        - Amazon, Google: smart speakers
        - Samsung, LG: smart TVs
        """
        vendor_lower = mac_or_vendor.lower()

        if any(v in vendor_lower for v in ["nest", "ring", "wyze", "arlo", "camera"]):
            return "iot-camera"
        elif any(v in vendor_lower for v in ["philips", "lifx", "hue", "light"]):
            return "iot-light"
        elif any(
            v in vendor_lower for v in ["amazon", "google", "alexa", "echo", "home"]
        ):
            return "iot-speaker"
        elif any(v in vendor_lower for v in ["samsung", "lg", "sony", "tv"]):
            return "iot-tv"
        elif any(v in vendor_lower for v in ["router", "cisco", "netgear", "linksys"]):
            return "router"
        else:
            return "unknown"

    def _resolve_hostname(self, ip):
        """Resolve IP to hostname."""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return f"Device-{ip.split('.')[-1]}"

    def _is_linux(self):
        import platform

        return platform.system().lower() == "linux"

    def _is_windows(self):
        import platform

        return platform.system().lower() == "windows"

    def _handle_security_check(self):
        """
        Run comprehensive security check:
        1. Port scanning on all devices
        2. CVE vulnerability lookup
        3. IoT device risk assessment
        """
        if not self.discovered_devices:
            return {
                "type": "network_security_help",
                "content": {
                    "message": "Network scan required",
                    "description": "No devices discovered yet. Please run a network scan first to discover devices on your local network.",
                    "status": "waiting_for_scan",
                    "suggestion": "Use 'scan network' command to begin",
                    "quick_action": "scan network",
                },
            }

        # Port scan all devices
        for device in self.discovered_devices:
            device["openPorts"] = self._scan_ports(device["ip"])

        # Update stats
        self.security_stats["openPorts"] = sum(
            len(d.get("openPorts", [])) for d in self.discovered_devices
        )

        # CVE-style checks (heuristic, offline)
        cve_alerts = self._check_cve_vulnerabilities()

        self.security_stats["vulnerabilities"] = len(cve_alerts)

        return {
            "type": "security_check_complete",
            "content": {
                "message": "Security check complete",
                "stats": self.security_stats,
                "cveAlerts": cve_alerts,
                "devices": self.discovered_devices,
            },
        }

    def _scan_ports(self, ip, ports=None):
        """
        Scan ports on a specific IP.

        Common ports to check:
        - 21: FTP
        - 22: SSH
        - 23: Telnet (insecure!)
        - 80: HTTP
        - 443: HTTPS
        - 3389: RDP
        - 8080: HTTP alternate
        """
        if ports is None:
            ports = [21, 22, 23, 80, 443, 3389, 8080, 8443]

        open_ports = []

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    open_ports.append(port)
            except:
                pass

        return open_ports

    def _check_cve_vulnerabilities(self):
        """
        Check devices for known CVE vulnerabilities.

        This uses offline heuristics to flag risky services/ports and
        common IoT issues without requiring external API calls.
        """
        cve_alerts = []

        for device in self.discovered_devices:
            open_ports = set(device.get("openPorts", []))
            device_type = device.get("type", "unknown")

            def add_alert(cve_id, severity, description):
                cve_alerts.append(
                    {
                        "cveId": cve_id,
                        "severity": severity,
                        "device": device.get("name", "Unknown Device"),
                        "ip": device.get("ip", "unknown"),
                        "description": description,
                    }
                )

            # Insecure management / legacy protocols
            if 23 in open_ports:
                add_alert(
                    "CVE-TELNET-INSECURE",
                    "critical",
                    "Telnet (23) is exposed. Disable Telnet and use SSH instead.",
                )
            if 21 in open_ports:
                add_alert(
                    "CVE-FTP-CLEAR-TEXT",
                    "high",
                    "FTP (21) transmits credentials in clear text. Use SFTP/FTPS.",
                )
            if 3389 in open_ports:
                add_alert(
                    "CVE-RDP-EXPOSURE",
                    "high",
                    "RDP (3389) is reachable. Restrict to VPN and enable MFA.",
                )
            if 7547 in open_ports:
                add_alert(
                    "CVE-TR069-EXPOSED",
                    "high",
                    "TR-069 management port (7547) exposed; common ISP router issue.",
                )
            if 80 in open_ports and 443 not in open_ports:
                add_alert(
                    "CVE-HTTP-UNENCRYPTED",
                    "medium",
                    "Web interface only on HTTP. Enable HTTPS and disable plaintext logins.",
                )
            if 554 in open_ports and "camera" in device_type:
                add_alert(
                    "CVE-RTSP-EXPOSED",
                    "medium",
                    "RTSP (554) is open on a camera; ensure strong passwords and firmware updates.",
                )

            # IoT/Router hygiene
            if device_type.startswith("iot"):
                add_alert(
                    "CVE-IOT-HYGIENE",
                    "medium",
                    "IoT device detected. Verify firmware is current and unused services are closed.",
                )
            if device_type == "router":
                add_alert(
                    "CVE-ROUTER-FIRMWARE",
                    "medium",
                    "Router detected. Check for latest firmware and disable WPS/UPnP if unused.",
                )

        return cve_alerts

    def _list_devices(self):
        """List all discovered devices."""
        return {
            "type": "device_list",
            "content": {
                "message": f"Discovered devices: {len(self.discovered_devices)}",
                "devices": self.discovered_devices,
                "stats": self.security_stats,
            },
        }

    def _handle_vpn_status(self):
        """Get VPN connection status."""
        return {
            "type": "vpn_status",
            "content": {
                "message": "VPN status",
                "connected": self.vpn_connected,
                "location": "Unknown" if not self.vpn_connected else "VPN Server",
                "note": "VPN functionality managed by browser extension",
            },
        }

    def _handle_port_scan(self, query):
        """Handle port scan command."""
        # Extract IP from query
        import re

        ip_match = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", query)

        if not ip_match:
            return {
                "type": "error",
                "content": {
                    "message": "Please specify IP address",
                    "format": "scan ports [ip address]",
                    "example": "scan ports 192.168.1.1",
                },
            }

        ip = ip_match.group(0)
        open_ports = self._scan_ports(ip)

        return {
            "type": "port_scan_complete",
            "content": {
                "message": f"Port scan complete for {ip}",
                "ip": ip,
                "open_ports": open_ports,
                "port_count": len(open_ports),
            },
        }

    def health(self):
        """Health check."""
        return {
            "status": "healthy",
            "discovered_devices": len(self.discovered_devices),
            "vpn_connected": self.vpn_connected,
            "security_stats": self.security_stats,
        }
