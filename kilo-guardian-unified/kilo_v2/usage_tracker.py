"""
Usage Tracking System - Monitor Feature Usage & Quotas

Tracks:
- VPN peer connections
- Data transfer (VPN traffic)
- API calls
- Feature usage patterns
- Resource consumption
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("UsageTracker")


class UsageTracker:
    """Tracks usage metrics for billing and analytics"""

    def __init__(self, data_dir: str = "/var/lib/bastion"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.data_dir / "usage_metrics.json"
        self.events_file = self.data_dir / "usage_events.jsonl"

        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict:
        """Load usage metrics from disk"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")

        return {
            "created_at": datetime.now().isoformat(),
            "vpn": {
                "peers_created": 0,
                "peers_active": 0,
                "total_connections": 0,
                "data_transfer_bytes": 0,
            },
            "vpn_client": {
                "profiles_created": 0,
                "total_connections": 0,
                "total_duration_seconds": 0,
                "data_transfer_bytes": 0,
            },
            "vps_bridge": {
                "heartbeats_sent": 0,
                "data_syncs": 0,
                "commands_executed": 0,
            },
            "api": {"total_calls": 0, "calls_by_endpoint": defaultdict(int)},
            "features": {
                "qr_codes_generated": 0,
                "analytics_views": 0,
                "backups_created": 0,
            },
            "daily": {},
            "monthly": {},
        }

    def _save_metrics(self):
        """Save metrics to disk"""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _log_event(self, event_type: str, data: Dict):
        """Log individual usage event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }

        try:
            with open(self.events_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def _update_daily_stats(self, category: str, metric: str, value: float = 1):
        """Update daily aggregated stats"""
        today = datetime.now().date().isoformat()

        if today not in self.metrics["daily"]:
            self.metrics["daily"][today] = {}

        if category not in self.metrics["daily"][today]:
            self.metrics["daily"][today][category] = {}

        current = self.metrics["daily"][today][category].get(metric, 0)
        self.metrics["daily"][today][category][metric] = current + value

    def _update_monthly_stats(self, category: str, metric: str, value: float = 1):
        """Update monthly aggregated stats"""
        month = datetime.now().strftime("%Y-%m")

        if month not in self.metrics["monthly"]:
            self.metrics["monthly"][month] = {}

        if category not in self.metrics["monthly"][month]:
            self.metrics["monthly"][month][category] = {}

        current = self.metrics["monthly"][month][category].get(metric, 0)
        self.metrics["monthly"][month][category][metric] = current + value

    # VPN Server tracking
    def track_peer_created(self, peer_name: str):
        """Track VPN peer creation"""
        self.metrics["vpn"]["peers_created"] += 1
        self.metrics["vpn"]["peers_active"] += 1

        self._update_daily_stats("vpn", "peers_created")
        self._update_monthly_stats("vpn", "peers_created")

        self._log_event("vpn_peer_created", {"name": peer_name})
        self._save_metrics()

    def track_peer_removed(self, peer_name: str):
        """Track VPN peer removal"""
        self.metrics["vpn"]["peers_active"] = max(
            0, self.metrics["vpn"]["peers_active"] - 1
        )

        self._log_event("vpn_peer_removed", {"name": peer_name})
        self._save_metrics()

    def track_vpn_connection(self, peer_name: str, duration_seconds: int = 0):
        """Track VPN connection"""
        self.metrics["vpn"]["total_connections"] += 1

        self._update_daily_stats("vpn", "connections")
        self._update_monthly_stats("vpn", "connections")

        if duration_seconds > 0:
            self._update_daily_stats("vpn", "connection_time_seconds", duration_seconds)
            self._update_monthly_stats(
                "vpn", "connection_time_seconds", duration_seconds
            )

        self._log_event(
            "vpn_connection", {"peer": peer_name, "duration": duration_seconds}
        )
        self._save_metrics()

    def track_vpn_data_transfer(self, bytes_transferred: int):
        """Track VPN data transfer"""
        self.metrics["vpn"]["data_transfer_bytes"] += bytes_transferred

        self._update_daily_stats("vpn", "data_transfer_bytes", bytes_transferred)
        self._update_monthly_stats("vpn", "data_transfer_bytes", bytes_transferred)

        self._save_metrics()

    # VPN Client tracking
    def track_vpn_client_profile_added(self, profile_name: str, vpn_type: str):
        """Track VPN client profile creation"""
        self.metrics["vpn_client"]["profiles_created"] += 1

        self._log_event(
            "vpn_client_profile_added", {"name": profile_name, "type": vpn_type}
        )
        self._save_metrics()

    def track_vpn_client_connection(self, profile_name: str, duration_seconds: int = 0):
        """Track VPN client connection"""
        self.metrics["vpn_client"]["total_connections"] += 1

        if duration_seconds > 0:
            self.metrics["vpn_client"]["total_duration_seconds"] += duration_seconds
            self._update_daily_stats(
                "vpn_client", "connection_time_seconds", duration_seconds
            )

        self._update_daily_stats("vpn_client", "connections")
        self._update_monthly_stats("vpn_client", "connections")

        self._log_event(
            "vpn_client_connection",
            {"profile": profile_name, "duration": duration_seconds},
        )
        self._save_metrics()

    def track_vpn_client_data_transfer(self, bytes_transferred: int):
        """Track VPN client data transfer"""
        self.metrics["vpn_client"]["data_transfer_bytes"] += bytes_transferred

        self._update_daily_stats("vpn_client", "data_transfer_bytes", bytes_transferred)
        self._update_monthly_stats(
            "vpn_client", "data_transfer_bytes", bytes_transferred
        )

        self._save_metrics()

    # VPS Bridge tracking
    def track_vps_heartbeat(self):
        """Track VPS heartbeat"""
        self.metrics["vps_bridge"]["heartbeats_sent"] += 1
        self._update_daily_stats("vps_bridge", "heartbeats")
        self._save_metrics()

    def track_vps_sync(self):
        """Track VPS data sync"""
        self.metrics["vps_bridge"]["data_syncs"] += 1
        self._update_daily_stats("vps_bridge", "syncs")
        self._update_monthly_stats("vps_bridge", "syncs")
        self._save_metrics()

    def track_vps_command(self, command_type: str):
        """Track VPS command execution"""
        self.metrics["vps_bridge"]["commands_executed"] += 1

        self._log_event("vps_command", {"type": command_type})
        self._save_metrics()

    # API tracking
    def track_api_call(self, endpoint: str, method: str = "GET"):
        """Track API call"""
        self.metrics["api"]["total_calls"] += 1

        endpoint_key = f"{method} {endpoint}"
        if "calls_by_endpoint" not in self.metrics["api"]:
            self.metrics["api"]["calls_by_endpoint"] = {}

        current = self.metrics["api"]["calls_by_endpoint"].get(endpoint_key, 0)
        self.metrics["api"]["calls_by_endpoint"][endpoint_key] = current + 1

        self._update_daily_stats("api", "calls")
        self._save_metrics()

    # Feature tracking
    def track_qr_code_generated(self):
        """Track QR code generation"""
        self.metrics["features"]["qr_codes_generated"] += 1
        self._update_daily_stats("features", "qr_codes")
        self._save_metrics()

    def track_analytics_view(self):
        """Track analytics dashboard view"""
        self.metrics["features"]["analytics_views"] += 1
        self._update_daily_stats("features", "analytics_views")
        self._save_metrics()

    def track_backup_created(self):
        """Track backup creation"""
        self.metrics["features"]["backups_created"] += 1
        self._update_monthly_stats("features", "backups")
        self._save_metrics()

    # Reporting
    def get_current_usage(self) -> Dict:
        """Get current usage statistics"""
        return {
            "vpn": {
                "active_peers": self.metrics["vpn"]["peers_active"],
                "total_peers_created": self.metrics["vpn"]["peers_created"],
                "total_connections": self.metrics["vpn"]["total_connections"],
                "total_data_gb": round(
                    self.metrics["vpn"]["data_transfer_bytes"] / (1024**3), 2
                ),
            },
            "vpn_client": {
                "profiles": self.metrics["vpn_client"]["profiles_created"],
                "total_connections": self.metrics["vpn_client"]["total_connections"],
                "total_hours": round(
                    self.metrics["vpn_client"]["total_duration_seconds"] / 3600, 1
                ),
                "total_data_gb": round(
                    self.metrics["vpn_client"]["data_transfer_bytes"] / (1024**3), 2
                ),
            },
            "vps_bridge": self.metrics["vps_bridge"],
            "api": {
                "total_calls": self.metrics["api"]["total_calls"],
                "top_endpoints": self._get_top_endpoints(10),
            },
            "features": self.metrics["features"],
        }

    def get_daily_stats(self, days: int = 30) -> Dict:
        """Get daily statistics for last N days"""
        today = datetime.now().date()
        stats = {}

        for i in range(days):
            date = (today - timedelta(days=i)).isoformat()
            if date in self.metrics["daily"]:
                stats[date] = self.metrics["daily"][date]

        return stats

    def get_monthly_stats(self, months: int = 12) -> Dict:
        """Get monthly statistics for last N months"""
        current_month = datetime.now().replace(day=1)
        stats = {}

        for i in range(months):
            month = (current_month - timedelta(days=i * 30)).strftime("%Y-%m")
            if month in self.metrics["monthly"]:
                stats[month] = self.metrics["monthly"][month]

        return stats

    def _get_top_endpoints(self, limit: int = 10) -> List[Dict]:
        """Get most called API endpoints"""
        endpoints = self.metrics["api"].get("calls_by_endpoint", {})
        sorted_endpoints = sorted(endpoints.items(), key=lambda x: x[1], reverse=True)

        return [
            {"endpoint": endpoint, "calls": count}
            for endpoint, count in sorted_endpoints[:limit]
        ]

    def get_billing_summary(self) -> Dict:
        """Get summary for billing purposes"""
        current_month = datetime.now().strftime("%Y-%m")
        monthly = self.metrics["monthly"].get(current_month, {})

        return {
            "period": current_month,
            "vpn_peers_active": self.metrics["vpn"]["peers_active"],
            "vpn_data_gb": round(
                monthly.get("vpn", {}).get("data_transfer_bytes", 0) / (1024**3), 2
            ),
            "vpn_client_hours": round(
                monthly.get("vpn_client", {}).get("connection_time_seconds", 0) / 3600,
                1,
            ),
            "api_calls": monthly.get("api", {}).get("calls", 0),
            "vps_syncs": monthly.get("vps_bridge", {}).get("syncs", 0),
        }


# Singleton instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get usage tracker singleton"""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
