"""
VPN Client Plugin - Route Bastion Traffic Through External VPN

Routes Bastion AI traffic through external VPN providers for:
- Anonymity and privacy
- Geographic location flexibility
- Traffic encryption
- Bypass network restrictions

Supports: WireGuard and OpenVPN
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from plugins.base_plugin import BasePlugin

# Import license and usage tracking
try:
    from license_manager import get_license_manager
    from usage_tracker import get_usage_tracker

    _HAS_LICENSE_SYSTEM = True
except ImportError:
    _HAS_LICENSE_SYSTEM = False


class VPNClientPlugin(BasePlugin):
    """VPN Client for routing Bastion traffic through external VPN"""

    def __init__(self):
        super().__init__()
        self.config_dir = Path("/etc/bastion/vpn")
        self.profiles_file = Path("/var/lib/bastion/vpn_profiles.json")
        self.current_connection = None
        self.profiles = self._load_profiles()

        # License and usage tracking
        if _HAS_LICENSE_SYSTEM:
            self.license_manager = get_license_manager()
            self.usage_tracker = get_usage_tracker()
        else:
            self.license_manager = None
            self.usage_tracker = None

    def get_name(self) -> str:
        return "vpn_client"

    def get_keywords(self) -> List[str]:
        return [
            "vpn client",
            "connect vpn",
            "route traffic",
            "vpn connection",
            "anonymity",
            "privacy",
        ]

    def _load_profiles(self) -> Dict:
        """Load VPN profiles from disk"""
        if self.profiles_file.exists():
            with open(self.profiles_file, "r") as f:
                return json.load(f)
        return {"profiles": [], "active_profile": None}

    def _save_profiles(self):
        """Save VPN profiles to disk"""
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profiles_file, "w") as f:
            json.dump(self.profiles, f, indent=2)

    def add_wireguard_profile(self, name: str, config: str) -> Dict:
        """Add WireGuard VPN profile"""
        try:
            # Create config directory
            self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Save config file
            config_file = self.config_dir / f"{name}.conf"
            with open(config_file, "w") as f:
                f.write(config)
            os.chmod(config_file, 0o600)

            # Add to profiles
            profile = {
                "name": name,
                "type": "wireguard",
                "config_file": str(config_file),
                "created": datetime.now().isoformat(),
                "last_connected": None,
                "enabled": True,
            }

            self.profiles["profiles"].append(profile)
            self._save_profiles()

            return {
                "success": True,
                "profile": profile,
                "message": f"WireGuard profile '{name}' added successfully",
            }

        except Exception as e:
            self.logger.error(f"Failed to add WireGuard profile: {e}")
            return {"success": False, "error": str(e)}

    def add_openvpn_profile(self, name: str, config: str) -> Dict:
        """Add OpenVPN profile"""
        try:
            # Create config directory
            self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Save config file
            config_file = self.config_dir / f"{name}.ovpn"
            with open(config_file, "w") as f:
                f.write(config)
            os.chmod(config_file, 0o600)

            # Add to profiles
            profile = {
                "name": name,
                "type": "openvpn",
                "config_file": str(config_file),
                "created": datetime.now().isoformat(),
                "last_connected": None,
                "enabled": True,
            }

            self.profiles["profiles"].append(profile)
            self._save_profiles()

            return {
                "success": True,
                "profile": profile,
                "message": f"OpenVPN profile '{name}' added successfully",
            }

        except Exception as e:
            self.logger.error(f"Failed to add OpenVPN profile: {e}")
            return {"success": False, "error": str(e)}

    def connect(self, profile_name: str) -> Dict:
        """Connect to VPN using specified profile"""
        try:
            # Check license for VPN client routing
            if self.license_manager:
                if not self.license_manager.check_feature_access("vpn_client_routing"):
                    return {
                        "success": False,
                        "error": "VPN client routing requires Pro tier or higher",
                        "upgrade_required": True,
                        "upgrade_info": self.license_manager.get_upgrade_info(),
                    }

            # Find profile
            profile = None
            for p in self.profiles["profiles"]:
                if p["name"] == profile_name:
                    profile = p
                    break

            if not profile:
                return {
                    "success": False,
                    "error": f"Profile '{profile_name}' not found",
                }

            if not profile["enabled"]:
                return {
                    "success": False,
                    "error": f"Profile '{profile_name}' is disabled",
                }

            # Disconnect if already connected
            if self.profiles["active_profile"]:
                self.disconnect()

            # Connect based on type
            if profile["type"] == "wireguard":
                result = self._connect_wireguard(profile)
            elif profile["type"] == "openvpn":
                result = self._connect_openvpn(profile)
            else:
                return {
                    "success": False,
                    "error": f"Unknown profile type: {profile['type']}",
                }

            if result["success"]:
                # Update profile
                profile["last_connected"] = datetime.now().isoformat()
                self.profiles["active_profile"] = profile_name
                self._save_profiles()

                # Verify connection
                time.sleep(2)
                if self._verify_connection():
                    # Track usage
                    if self.usage_tracker:
                        self.usage_tracker.track_vpn_client_connection(profile_name)

                    return {
                        "success": True,
                        "profile": profile_name,
                        "message": f"Connected to {profile_name}",
                        "public_ip": self._get_public_ip(),
                    }
                else:
                    self.disconnect()
                    return {
                        "success": False,
                        "error": "Connection established but not working",
                    }

            return result

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return {"success": False, "error": str(e)}

    def _connect_wireguard(self, profile: Dict) -> Dict:
        """Connect to WireGuard VPN"""
        try:
            interface_name = f"wg_{profile['name'][:8]}"

            # Start WireGuard
            result = subprocess.run(
                ["wg-quick", "up", profile["config_file"]],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to start WireGuard: {result.stderr.decode()}",
                }

            self.current_connection = {
                "type": "wireguard",
                "interface": interface_name,
                "profile": profile["name"],
            }

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _connect_openvpn(self, profile: Dict) -> Dict:
        """Connect to OpenVPN"""
        try:
            # Start OpenVPN in background
            log_file = Path("/var/log/bastion/openvpn.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)

            process = subprocess.Popen(
                [
                    "openvpn",
                    "--config",
                    profile["config_file"],
                    "--daemon",
                    "--log",
                    str(log_file),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait a bit for connection
            time.sleep(5)

            # Check if process is still running
            if process.poll() is not None:
                return {"success": False, "error": "OpenVPN process terminated"}

            self.current_connection = {
                "type": "openvpn",
                "pid": process.pid,
                "profile": profile["name"],
            }

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def disconnect(self) -> Dict:
        """Disconnect from current VPN"""
        try:
            if not self.profiles["active_profile"]:
                return {"success": False, "error": "Not connected to any VPN"}

            profile_name = self.profiles["active_profile"]

            # Find profile
            profile = None
            for p in self.profiles["profiles"]:
                if p["name"] == profile_name:
                    profile = p
                    break

            if not profile:
                return {"success": False, "error": "Active profile not found"}

            # Disconnect based on type
            if profile["type"] == "wireguard":
                subprocess.run(
                    ["wg-quick", "down", profile["config_file"]], check=False
                )
            elif profile["type"] == "openvpn":
                subprocess.run(
                    ["pkill", "-f", f"openvpn.*{profile['name']}"], check=False
                )

            self.profiles["active_profile"] = None
            self.current_connection = None
            self._save_profiles()

            return {"success": True, "message": f"Disconnected from {profile_name}"}

        except Exception as e:
            self.logger.error(f"Failed to disconnect: {e}")
            return {"success": False, "error": str(e)}

    def _verify_connection(self) -> bool:
        """Verify VPN connection is working"""
        try:
            # Try to reach a test endpoint
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", "https://1.1.1.1"],
                capture_output=True,
            )
            return result.returncode == 0
        except:
            return False

    def _get_public_ip(self) -> Optional[str]:
        """Get current public IP address"""
        try:
            result = (
                subprocess.check_output(
                    ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                    timeout=10,
                )
                .decode()
                .strip()
            )
            return result
        except:
            return None

    def get_status(self) -> Dict:
        """Get VPN client status"""
        try:
            active = self.profiles.get("active_profile")

            if not active:
                return {
                    "success": True,
                    "connected": False,
                    "profiles_count": len(self.profiles["profiles"]),
                }

            # Find active profile
            profile = None
            for p in self.profiles["profiles"]:
                if p["name"] == active:
                    profile = p
                    break

            # Get connection stats
            public_ip = self._get_public_ip()

            return {
                "success": True,
                "connected": True,
                "active_profile": profile,
                "public_ip": public_ip,
                "connection_time": profile.get("last_connected"),
            }

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {"success": False, "error": str(e)}

    def list_profiles(self) -> Dict:
        """List all VPN profiles"""
        return {
            "success": True,
            "profiles": self.profiles["profiles"],
            "active": self.profiles.get("active_profile"),
            "total": len(self.profiles["profiles"]),
        }

    def remove_profile(self, name: str) -> Dict:
        """Remove VPN profile"""
        try:
            # Check if profile is active
            if self.profiles.get("active_profile") == name:
                self.disconnect()

            # Find and remove profile
            profile = None
            for p in self.profiles["profiles"]:
                if p["name"] == name:
                    profile = p
                    break

            if not profile:
                return {"success": False, "error": f"Profile '{name}' not found"}

            # Delete config file
            config_file = Path(profile["config_file"])
            if config_file.exists():
                config_file.unlink()

            # Remove from profiles
            self.profiles["profiles"] = [
                p for p in self.profiles["profiles"] if p["name"] != name
            ]
            self._save_profiles()

            return {"success": True, "message": f"Profile '{name}' removed"}

        except Exception as e:
            self.logger.error(f"Failed to remove profile: {e}")
            return {"success": False, "error": str(e)}

    def run(self, query: str) -> Dict:
        """Handle VPN client commands"""
        query_lower = query.lower()

        if "connect" in query_lower:
            # Extract profile name
            if "to" in query_lower:
                parts = query_lower.split("to")
                if len(parts) > 1:
                    profile_name = parts[1].strip().split()[0]
                    return self.connect(profile_name)
            return {"success": False, "error": "Please specify profile name"}

        elif "disconnect" in query_lower:
            return self.disconnect()

        elif "status" in query_lower:
            return self.get_status()

        elif "list" in query_lower:
            return self.list_profiles()

        elif "remove" in query_lower:
            return {"success": False, "error": "Please specify profile name"}

        else:
            return {
                "type": "help",
                "commands": {
                    "connect to [profile]": "Connect to VPN using profile",
                    "disconnect": "Disconnect from current VPN",
                    "status": "Show VPN connection status",
                    "list profiles": "List all VPN profiles",
                },
            }

    def health(self) -> bool:
        """Check if VPN client is healthy"""
        try:
            # If connected, verify connection works
            if self.profiles.get("active_profile"):
                return self._verify_connection()
            return True
        except:
            return False
