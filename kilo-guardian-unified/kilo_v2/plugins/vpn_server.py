"""
VPN Server Plugin - WireGuard VPN Server for Remote Access

Provides secure remote access to Bastion AI via WireGuard VPN.
Features:
- Automatic peer management
- Key generation and QR codes
- Dynamic firewall configuration
- Connection monitoring
- Traffic statistics
"""

import base64
import io
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import qrcode
from plugins.base_plugin import BasePlugin

# Import license and usage tracking
try:
    from license_manager import LicenseTier, get_license_manager
    from usage_tracker import get_usage_tracker

    _HAS_LICENSE_SYSTEM = True
except ImportError:
    _HAS_LICENSE_SYSTEM = False


class VPNServerPlugin(BasePlugin):
    """WireGuard VPN Server for remote access to Bastion"""

    def __init__(self):
        super().__init__()
        self.config_dir = Path("/etc/wireguard")
        self.interface = "wg0"
        self.port = 51820
        self.peers_file = Path("/var/lib/bastion/vpn_peers.json")
        self.server_ip = "10.8.0.1/24"
        self.peers = self._load_peers()

        # License and usage tracking
        if _HAS_LICENSE_SYSTEM:
            self.license_manager = get_license_manager()
            self.usage_tracker = get_usage_tracker()
        else:
            self.license_manager = None
            self.usage_tracker = None

    def get_name(self) -> str:
        return "vpn_server"

    def get_keywords(self) -> List[str]:
        return ["vpn", "wireguard", "remote access", "peer", "tunnel", "secure access"]

    def _load_peers(self) -> Dict:
        """Load peer configuration from disk"""
        if self.peers_file.exists():
            with open(self.peers_file, "r") as f:
                return json.load(f)
        return {"peers": [], "next_ip": 2}

    def _save_peers(self):
        """Save peer configuration to disk"""
        self.peers_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.peers_file, "w") as f:
            json.dump(self.peers, f, indent=2)

    def _generate_keys(self) -> tuple:
        """Generate WireGuard private/public key pair"""
        try:
            # Generate private key
            private_key = (
                subprocess.check_output(["wg", "genkey"], stderr=subprocess.PIPE)
                .decode()
                .strip()
            )

            # Generate public key from private key
            public_key = (
                subprocess.check_output(
                    ["wg", "pubkey"], input=private_key.encode(), stderr=subprocess.PIPE
                )
                .decode()
                .strip()
            )

            return private_key, public_key
        except Exception as e:
            self.logger.error(f"Failed to generate keys: {e}")
            return None, None

    def _get_server_public_key(self) -> Optional[str]:
        """Get server's public key"""
        try:
            config_file = self.config_dir / f"{self.interface}.conf"
            if not config_file.exists():
                return None

            with open(config_file, "r") as f:
                for line in f:
                    if line.startswith("PrivateKey"):
                        private_key = line.split("=")[1].strip()
                        public_key = (
                            subprocess.check_output(
                                ["wg", "pubkey"],
                                input=private_key.encode(),
                                stderr=subprocess.PIPE,
                            )
                            .decode()
                            .strip()
                        )
                        return public_key
        except Exception as e:
            self.logger.error(f"Failed to get server public key: {e}")
        return None

    def _get_server_endpoint(self) -> Optional[str]:
        """Get server's public IP/hostname"""
        try:
            # Try to get public IP
            result = (
                subprocess.check_output(["curl", "-s", "ifconfig.me"], timeout=5)
                .decode()
                .strip()
            )
            return f"{result}:{self.port}"
        except:
            return f"YOUR_PUBLIC_IP:{self.port}"

    def _generate_qr_code(self, config: str) -> str:
        """Generate QR code for mobile client configuration"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(config)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            return ""

    def setup_server(self) -> Dict:
        """Initialize WireGuard VPN server"""
        try:
            # Check license for VPN server access
            if self.license_manager:
                if not self.license_manager.check_feature_access("vpn_server"):
                    from license_manager import LicenseTier

                    return {
                        "success": False,
                        "error": "VPN Server requires Pro tier or higher subscription",
                        "upgrade_required": True,
                        "upgrade_info": {
                            "message": "VPN Server is a premium feature that allows remote access to your Bastion AI system.",
                            "tier": "Pro or Enterprise",
                            "price": "Starting at $29/month",
                            "features": [
                                "Secure remote access",
                                "Up to 25 peers (Pro) or unlimited (Enterprise)",
                                "QR code configuration",
                                "Traffic monitoring",
                            ],
                        },
                    }

            # Check if WireGuard is installed
            try:
                subprocess.run(["wg", "version"], check=True, capture_output=True)
            except:
                return {
                    "success": False,
                    "error": "WireGuard not installed. Run: sudo apt install wireguard",
                }

            # Create config directory
            self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Generate server keys
            private_key, public_key = self._generate_keys()
            if not private_key:
                return {"success": False, "error": "Failed to generate server keys"}

            # Create server configuration
            config_file = self.config_dir / f"{self.interface}.conf"
            config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {self.server_ip}
ListenPort = {self.port}
PostUp = iptables -A FORWARD -i {self.interface} -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i {self.interface} -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Peers will be added below
"""

            with open(config_file, "w") as f:
                f.write(config_content)

            os.chmod(config_file, 0o600)

            # Enable IP forwarding
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

            # Start WireGuard interface
            subprocess.run(["wg-quick", "up", self.interface], check=False)

            # Enable on boot
            subprocess.run(
                ["systemctl", "enable", f"wg-quick@{self.interface}"], check=False
            )

            return {
                "success": True,
                "interface": self.interface,
                "server_ip": self.server_ip,
                "port": self.port,
                "public_key": public_key,
                "endpoint": self._get_server_endpoint(),
            }

        except Exception as e:
            self.logger.error(f"Failed to setup VPN server: {e}")
            return {"success": False, "error": str(e)}

    def add_peer(self, name: str, email: str = "") -> Dict:
        """Add new VPN peer (client)"""
        try:
            # Check license limits
            if self.license_manager:
                current_peers = len(self.peers["peers"])
                limit_check = self.license_manager.check_peer_limit(current_peers)

                if not limit_check.get("allowed", True):
                    # Return upgrade prompt
                    return {
                        "success": False,
                        "error": limit_check["error"],
                        "upgrade_required": True,
                        "upgrade_info": self.license_manager.get_upgrade_info(),
                    }

            # Generate peer keys
            private_key, public_key = self._generate_keys()
            if not private_key:
                return {"success": False, "error": "Failed to generate peer keys"}

            # Assign IP address
            peer_ip = f"10.8.0.{self.peers['next_ip']}/32"
            self.peers["next_ip"] += 1

            # Add peer to config
            config_file = self.config_dir / f"{self.interface}.conf"
            peer_config = f"""
[Peer]
# {name} ({email})
PublicKey = {public_key}
AllowedIPs = {peer_ip}
"""

            with open(config_file, "a") as f:
                f.write(peer_config)

            # Reload WireGuard
            subprocess.run(
                ["wg", "syncconf", self.interface, str(config_file)], check=False
            )

            # Generate client config
            server_public_key = self._get_server_public_key()
            server_endpoint = self._get_server_endpoint()

            client_config = f"""[Interface]
PrivateKey = {private_key}
Address = {peer_ip.replace('/32', '/24')}
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

            # Generate QR code (check license for Pro+ tier)
            qr_code = ""
            if self.license_manager:
                if self.license_manager.check_feature_access("qr_codes"):
                    qr_code = self._generate_qr_code(client_config)
                    if self.usage_tracker:
                        self.usage_tracker.track_qr_code_generated()
                else:
                    qr_code = "UPGRADE_TO_PRO_FOR_QR_CODES"
            else:
                qr_code = self._generate_qr_code(client_config)

            # Track usage
            if self.usage_tracker:
                self.usage_tracker.track_peer_created(name)

            # Save peer info
            peer_info = {
                "name": name,
                "email": email,
                "public_key": public_key,
                "ip": peer_ip,
                "created": datetime.now().isoformat(),
                "enabled": True,
            }
            self.peers["peers"].append(peer_info)
            self._save_peers()

            return {
                "success": True,
                "peer": peer_info,
                "client_config": client_config,
                "qr_code": qr_code,
            }

        except Exception as e:
            self.logger.error(f"Failed to add peer: {e}")
            return {"success": False, "error": str(e)}

    def remove_peer(self, public_key: str) -> Dict:
        """Remove VPN peer"""
        try:
            # Find peer
            peer = None
            for p in self.peers["peers"]:
                if p["public_key"] == public_key:
                    peer = p
                    break

            if not peer:
                return {"success": False, "error": "Peer not found"}

            # Remove from config file
            config_file = self.config_dir / f"{self.interface}.conf"
            with open(config_file, "r") as f:
                lines = f.readlines()

            # Find and remove peer section
            new_lines = []
            skip = False
            for line in lines:
                if f"PublicKey = {public_key}" in line:
                    skip = True
                    # Remove previous lines if they're part of peer block
                    while new_lines and (
                        new_lines[-1].startswith("#")
                        or new_lines[-1].strip() == "[Peer]"
                    ):
                        new_lines.pop()
                    continue
                if skip and line.startswith("["):
                    skip = False
                if not skip:
                    new_lines.append(line)

            with open(config_file, "w") as f:
                f.writelines(new_lines)

            # Reload WireGuard
            subprocess.run(
                ["wg", "syncconf", self.interface, str(config_file)], check=False
            )

            # Remove from peers list
            self.peers["peers"] = [
                p for p in self.peers["peers"] if p["public_key"] != public_key
            ]
            self._save_peers()

            # Track removal
            if self.usage_tracker:
                self.usage_tracker.track_peer_removed(peer["name"])

            return {"success": True, "removed": peer}

        except Exception as e:
            self.logger.error(f"Failed to remove peer: {e}")
            return {"success": False, "error": str(e)}

    def list_peers(self) -> Dict:
        """List all VPN peers with connection status"""
        try:
            # Get current connections
            result = subprocess.check_output(
                ["wg", "show", self.interface], stderr=subprocess.PIPE
            )
            wg_output = result.decode()

            # Parse connection status
            connected_peers = {}
            current_peer = None
            for line in wg_output.split("\n"):
                if line.startswith("peer:"):
                    current_peer = line.split(":")[1].strip()
                    connected_peers[current_peer] = {}
                elif current_peer and "transfer:" in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        connected_peers[current_peer]["rx"] = (
                            parts[0].split(":")[1].strip()
                        )
                        connected_peers[current_peer]["tx"] = parts[1].strip()
                elif current_peer and "latest handshake:" in line:
                    connected_peers[current_peer]["last_handshake"] = line.split(":")[
                        1
                    ].strip()

            # Merge with peer info
            peers_with_status = []
            for peer in self.peers["peers"]:
                peer_data = peer.copy()
                if peer["public_key"] in connected_peers:
                    peer_data["connected"] = True
                    peer_data["stats"] = connected_peers[peer["public_key"]]
                else:
                    peer_data["connected"] = False
                peers_with_status.append(peer_data)

            return {
                "success": True,
                "peers": peers_with_status,
                "total": len(peers_with_status),
                "connected": sum(
                    1 for p in peers_with_status if p.get("connected", False)
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to list peers: {e}")
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict:
        """Get VPN server status and statistics"""
        try:
            # Check if interface is up
            result = subprocess.run(
                ["ip", "link", "show", self.interface], capture_output=True
            )
            is_running = result.returncode == 0

            if not is_running:
                return {"success": True, "running": False, "interface": self.interface}

            # Get interface statistics
            result = subprocess.check_output(
                ["wg", "show", self.interface], stderr=subprocess.PIPE
            )
            wg_output = result.decode()

            # Parse stats
            listening_port = None
            public_key = None
            peer_count = 0

            for line in wg_output.split("\n"):
                if "listening port:" in line:
                    listening_port = line.split(":")[1].strip()
                elif "public key:" in line:
                    public_key = line.split(":")[1].strip()
                elif line.startswith("peer:"):
                    peer_count += 1

            return {
                "success": True,
                "running": True,
                "interface": self.interface,
                "port": listening_port,
                "public_key": public_key,
                "endpoint": self._get_server_endpoint(),
                "peer_count": peer_count,
                "server_ip": self.server_ip,
            }

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {"success": False, "error": str(e)}

    def run(self, query: str) -> Dict:
        """Handle VPN server commands"""
        query_lower = query.lower()

        if "setup" in query_lower or "initialize" in query_lower:
            return self.setup_server()

        elif "add peer" in query_lower or "new peer" in query_lower:
            # Extract name from query
            name = "New Peer"
            if "name" in query_lower:
                parts = query.split("name")
                if len(parts) > 1:
                    name = parts[1].strip().split()[0]
            return self.add_peer(name)

        elif "list" in query_lower or "show peers" in query_lower:
            return self.list_peers()

        elif "status" in query_lower:
            return self.get_status()

        elif "remove" in query_lower and "peer" in query_lower:
            return {
                "success": False,
                "error": "Please specify peer public key to remove",
            }

        else:
            return {
                "type": "help",
                "commands": {
                    "setup": "Initialize WireGuard VPN server",
                    "add peer": "Add new VPN client peer",
                    "list peers": "Show all peers and connection status",
                    "remove peer": "Remove a peer (requires public key)",
                    "status": "Show VPN server status",
                },
            }

    def health(self) -> bool:
        """Check if VPN server is healthy"""
        try:
            result = subprocess.run(
                ["ip", "link", "show", self.interface], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
