"""
License Management System - Subscription Tiers & Validation

Handles license verification, tier checking, and feature gating for monetization.

Tiers:
- FREE: 1 VPN peer, basic features
- PRO: 5 VPN peers, VPN client routing, QR codes ($4.99/month)
- BUSINESS: Unlimited peers, VPS bridge, analytics, SLA ($14.99/month)
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("LicenseManager")


class LicenseTier(Enum):
    """License tier definitions"""

    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class LicenseStatus(Enum):
    """License status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    TRIAL = "trial"


# Feature limits per tier
TIER_LIMITS = {
    LicenseTier.FREE: {
        "vpn_peers": 1,
        "vpn_client_routing": False,
        "vps_bridge": False,
        "qr_codes": False,
        "analytics": False,
        "api_calls_per_day": 1000,
        "data_transfer_gb": 1,
    },
    LicenseTier.PRO: {
        "vpn_peers": 5,
        "vpn_client_routing": True,
        "vps_bridge": False,
        "qr_codes": True,
        "analytics": True,
        "api_calls_per_day": 10000,
        "data_transfer_gb": 10,
    },
    LicenseTier.BUSINESS: {
        "vpn_peers": -1,  # Unlimited
        "vpn_client_routing": True,
        "vps_bridge": True,
        "qr_codes": True,
        "analytics": True,
        "api_calls_per_day": -1,  # Unlimited
        "data_transfer_gb": -1,  # Unlimited
    },
}


class LicenseManager:
    """Manages license validation and tier enforcement"""

    def __init__(self, license_file: str = "/var/lib/bastion/license.json"):
        self.license_file = Path(license_file)
        self.license_data = self._load_license()
        self.usage_file = Path("/var/lib/bastion/usage_stats.json")
        self.usage_data = self._load_usage()

    def _load_license(self) -> Dict:
        """Load license from disk"""
        if self.license_file.exists():
            try:
                with open(self.license_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load license: {e}")

        # Default to FREE tier
        return {
            "tier": LicenseTier.FREE.value,
            "status": LicenseStatus.ACTIVE.value,
            "license_key": "FREE-TIER",
            "bastion_id": None,
            "created_at": datetime.now().isoformat(),
            "expires_at": None,  # Free tier never expires
            "customer_email": None,
            "subscription_id": None,
        }

    def _save_license(self):
        """Save license to disk"""
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.license_file, "w") as f:
            json.dump(self.license_data, f, indent=2)

    def _load_usage(self) -> Dict:
        """Load usage statistics"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load usage stats: {e}")

        return {
            "api_calls_today": 0,
            "data_transfer_gb_today": 0.0,
            "last_reset": datetime.now().isoformat(),
            "total_api_calls": 0,
            "total_data_transfer_gb": 0.0,
        }

    def _save_usage(self):
        """Save usage statistics"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, "w") as f:
            json.dump(self.usage_data, f, indent=2)

    def _reset_daily_usage(self):
        """Reset daily usage counters if needed"""
        last_reset = datetime.fromisoformat(self.usage_data["last_reset"])
        if datetime.now().date() > last_reset.date():
            self.usage_data["api_calls_today"] = 0
            self.usage_data["data_transfer_gb_today"] = 0.0
            self.usage_data["last_reset"] = datetime.now().isoformat()
            self._save_usage()

    def activate_license(self, license_key: str, bastion_id: str) -> Dict:
        """Activate a license key"""
        try:
            # Validate license key format
            if not self._validate_key_format(license_key):
                return {"success": False, "error": "Invalid license key format"}

            # TODO: Call license server to verify key
            # For now, parse tier from key prefix
            if license_key.startswith("PRO-"):
                tier = LicenseTier.PRO
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            elif license_key.startswith("BIZ-"):
                tier = LicenseTier.BUSINESS
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            else:
                return {"success": False, "error": "Unknown license tier"}

            # Update license
            self.license_data.update(
                {
                    "tier": tier.value,
                    "status": LicenseStatus.ACTIVE.value,
                    "license_key": license_key,
                    "bastion_id": bastion_id,
                    "expires_at": expires_at,
                    "activated_at": datetime.now().isoformat(),
                }
            )

            self._save_license()

            return {"success": True, "tier": tier.value, "expires_at": expires_at}

        except Exception as e:
            logger.error(f"License activation failed: {e}")
            return {"success": False, "error": str(e)}

    def _validate_key_format(self, key: str) -> bool:
        """Validate license key format"""
        # Format: TIER-XXXXXXXX-XXXXXXXX-XXXXXXXX
        parts = key.split("-")
        return len(parts) >= 2 and parts[0] in ["PRO", "BIZ"]

    def get_tier(self) -> LicenseTier:
        """Get current license tier"""
        tier_str = self.license_data.get("tier", "free")
        return LicenseTier(tier_str)

    def get_status(self) -> LicenseStatus:
        """Get license status"""
        # Check expiration
        expires_at = self.license_data.get("expires_at")
        if expires_at:
            if datetime.now() > datetime.fromisoformat(expires_at):
                self.license_data["status"] = LicenseStatus.EXPIRED.value
                self._save_license()

        status_str = self.license_data.get("status", "active")
        return LicenseStatus(status_str)

    def is_active(self) -> bool:
        """Check if license is active"""
        return self.get_status() == LicenseStatus.ACTIVE

    def get_limits(self) -> Dict:
        """Get current tier limits"""
        tier = self.get_tier()
        return TIER_LIMITS.get(tier, TIER_LIMITS[LicenseTier.FREE])

    def check_feature_access(self, feature: str) -> bool:
        """Check if feature is accessible in current tier"""
        if not self.is_active():
            return False

        limits = self.get_limits()
        return limits.get(feature, False)

    def check_peer_limit(self, current_peers: int) -> Dict:
        """Check if adding peers is allowed"""
        limits = self.get_limits()
        max_peers = limits["vpn_peers"]

        if max_peers == -1:  # Unlimited
            return {"allowed": True}

        if current_peers >= max_peers:
            return {
                "allowed": False,
                "error": f"Peer limit reached ({max_peers})",
                "upgrade_required": True,
                "current_tier": self.get_tier().value,
                "suggested_tier": (
                    "pro" if self.get_tier() == LicenseTier.FREE else "business"
                ),
            }

        return {"allowed": True, "remaining": max_peers - current_peers}

    def record_api_call(self):
        """Record an API call for rate limiting"""
        self._reset_daily_usage()
        self.usage_data["api_calls_today"] += 1
        self.usage_data["total_api_calls"] += 1
        self._save_usage()

        # Check limit
        limits = self.get_limits()
        max_calls = limits["api_calls_per_day"]

        if max_calls != -1 and self.usage_data["api_calls_today"] > max_calls:
            return {
                "allowed": False,
                "error": "API rate limit exceeded",
                "limit": max_calls,
                "reset_at": self._get_next_reset_time(),
            }

        return {"allowed": True}

    def record_data_transfer(self, bytes_transferred: int):
        """Record data transfer for quota tracking"""
        self._reset_daily_usage()
        gb_transferred = bytes_transferred / (1024**3)

        self.usage_data["data_transfer_gb_today"] += gb_transferred
        self.usage_data["total_data_transfer_gb"] += gb_transferred
        self._save_usage()

        # Check limit
        limits = self.get_limits()
        max_gb = limits["data_transfer_gb"]

        if max_gb != -1 and self.usage_data["data_transfer_gb_today"] > max_gb:
            return {
                "allowed": False,
                "error": "Data transfer quota exceeded",
                "limit_gb": max_gb,
                "reset_at": self._get_next_reset_time(),
            }

        return {"allowed": True}

    def _get_next_reset_time(self) -> str:
        """Get next daily reset time"""
        tomorrow = datetime.now().date() + timedelta(days=1)
        reset_time = datetime.combine(tomorrow, datetime.min.time())
        return reset_time.isoformat()

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        self._reset_daily_usage()
        limits = self.get_limits()

        return {
            "tier": self.get_tier().value,
            "status": self.get_status().value,
            "expires_at": self.license_data.get("expires_at"),
            "usage": {
                "api_calls_today": self.usage_data["api_calls_today"],
                "api_calls_limit": limits["api_calls_per_day"],
                "data_transfer_gb_today": round(
                    self.usage_data["data_transfer_gb_today"], 2
                ),
                "data_transfer_limit_gb": limits["data_transfer_gb"],
                "total_api_calls": self.usage_data["total_api_calls"],
                "total_data_transfer_gb": round(
                    self.usage_data["total_data_transfer_gb"], 2
                ),
            },
            "limits": limits,
            "next_reset": self._get_next_reset_time(),
        }

    def get_upgrade_info(self) -> Dict:
        """Get information about upgrading"""
        current_tier = self.get_tier()

        if current_tier == LicenseTier.FREE:
            suggested = LicenseTier.PRO
            price = "$4.99/month"
            benefits = [
                "5 VPN peers (currently: 1)",
                "VPN client routing",
                "QR code generation",
                "Advanced analytics",
                "10 GB data transfer",
                "Priority support",
            ]
        elif current_tier == LicenseTier.PRO:
            suggested = LicenseTier.BUSINESS
            price = "$14.99/month"
            benefits = [
                "Unlimited VPN peers (currently: 5)",
                "VPS bridge/relay service",
                "Multi-site coordination",
                "Unlimited data transfer",
                "99.9% uptime SLA",
                "Dedicated support",
            ]
        else:
            return {
                "current_tier": current_tier.value,
                "message": "You have the highest tier",
            }

        return {
            "current_tier": current_tier.value,
            "suggested_tier": suggested.value,
            "price": price,
            "benefits": benefits,
            "upgrade_url": f"https://bastion.ai/upgrade?tier={suggested.value}",
        }


# Singleton instance
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Get license manager singleton"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def check_tier_access(required_tier: LicenseTier) -> bool:
    """Check if current license meets required tier"""
    manager = get_license_manager()
    current = manager.get_tier()

    tier_hierarchy = {LicenseTier.FREE: 0, LicenseTier.PRO: 1, LicenseTier.BUSINESS: 2}

    return tier_hierarchy.get(current, 0) >= tier_hierarchy.get(required_tier, 0)
