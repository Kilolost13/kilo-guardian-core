"""
Kilo Guardian Security Monitor - Intrusion Detection & Response System
Monitors system integrity, detects tampering, and provides defensive responses.

LEGAL NOTICE:
- All features comply with computer security laws
- "Back hack" functionality is DEFENSIVE ONLY and logs incidents
- Active offensive hacking is DISABLED by default (illegal in most jurisdictions)
- System logs all security events for legal evidence
"""

import hashlib
import json
import logging
import os
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

try:
    from watchdog.events import FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore

    _WATCHDOG_AVAILABLE = True
except Exception:
    _WATCHDOG_AVAILABLE = False

logger = logging.getLogger("SecurityMonitor")


class AttackLogger:
    """
    Logs attacks from Caddy/FastAPI layers and notifies users
    """

    def __init__(self, log_dir: str = "kilo_data/security_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.attack_log_file = self.log_dir / "attack_log.json"
        self.user_alerts_file = self.log_dir / "user_alerts.json"

        self.attacks: List[Dict] = []
        self.user_alerts: List[Dict] = []
        self.blocked_ips: set = set()

        self.auto_block_threshold = 5  # Block after 5 attacks from same IP
        self.ip_attack_count = {}

        logger.info("🔐 Attack Logger initialized")

    def log_attack(
        self, attack_type: str, source_ip: str, details: Dict, severity: str = "warning"
    ):
        """Log an attack and check if user notification needed.

        Adds optional IP enrichment when ENABLE_IP_ENRICHMENT is set in config.
        Enrichment failures are non-fatal and recorded only for debugging.
        """
        enrichment = None
        try:
            from . import config as kilo_config
        except Exception:
            import config as kilo_config  # type: ignore
        if getattr(kilo_config, "ENABLE_IP_ENRICHMENT", False) and source_ip not in (
            None,
            "unknown",
            "",
        ):
            try:
                from ip_enrichment import enrich_ip

                enrichment = enrich_ip(source_ip)
            except Exception as e:
                logger.debug(f"IP enrichment failed for {source_ip}: {e}")
                enrichment = {"ip": source_ip, "enabled": True, "error": str(e)}

        attack = {
            "timestamp": datetime.now().isoformat(),
            "type": attack_type,
            "severity": severity,
            "source_ip": source_ip,
            "details": details,
            "blocked": source_ip in self.blocked_ips,
            "enrichment": enrichment,
        }

        self.attacks.append(attack)
        logger.warning(f"🚨 ATTACK: {attack_type} from {source_ip}")

        # Count attacks from this IP
        self.ip_attack_count[source_ip] = self.ip_attack_count.get(source_ip, 0) + 1

        # Auto-block if threshold exceeded
        if self.ip_attack_count[source_ip] >= self.auto_block_threshold:
            self._block_ip(source_ip)

        # Persist to disk
        self._save_attack_log()

        # Create user alert for critical attacks
        if severity == "critical":
            self._create_user_alert(attack)

    def _block_ip(self, ip: str):
        """Add IP to block list"""
        if ip not in self.blocked_ips:
            self.blocked_ips.add(ip)
            logger.critical(
                f"🔒 AUTO-BLOCKED IP: {ip} (exceeded {self.auto_block_threshold} attacks)"
            )

    def _create_user_alert(self, attack: Dict):
        """Create user-facing security alert"""
        alert = {
            "id": hashlib.sha256(
                f"{attack['timestamp']}{attack['source_ip']}".encode()
            ).hexdigest()[:16],
            "timestamp": attack["timestamp"],
            "severity": attack["severity"],
            "message": self._generate_alert_message(attack),
            "recommendations": self._generate_recommendations(attack),
            "source_ip": attack["source_ip"],
            "dismissed": False,
        }

        self.user_alerts.append(alert)
        self._save_user_alerts()
        logger.warning(f"📢 USER ALERT: {attack['type']}")

    def _generate_alert_message(self, attack: Dict) -> str:
        """Generate user-friendly alert message"""
        messages = {
            "sql_injection": "⚠️ SQL injection attack detected - someone tried to hack your database",
            "xss_attempt": "⚠️ XSS attack detected - someone tried to inject malicious scripts",
            "path_traversal": "⚠️ File access attack detected - someone tried to steal system files",
            "brute_force": "⚠️ Brute force attack in progress - someone is trying to guess your password",
            "scanner_detected": "⚠️ Security scanner detected - your system is being probed for vulnerabilities",
            "malicious_path": "⚠️ Attempt to access sensitive files blocked",
            "honeypot_triggered": "🍯 CRITICAL: Honeypot trap triggered - attacker caught red-handed!",
            "suspicious_agent": "⚠️ Attack tool detected (sqlmap, nmap, or similar)",
        }

        return messages.get(attack["type"], f"⚠️ Security incident: {attack['type']}")

    def _generate_recommendations(self, attack: Dict) -> List[str]:
        """Generate security recommendations"""
        critical_actions = [
            "🔴 URGENT: Change your password immediately",
            "🔴 Log out and log back in to refresh your session",
            "🔴 Check for unauthorized changes to your account",
            "🔴 Enable two-factor authentication if available",
            "🔴 Review recent activity for anything suspicious",
        ]

        normal_actions = [
            "Monitor your account for unusual activity",
            "Review recent login history",
            "Report persistent attacks to administrators",
        ]

        if attack["type"] in ["honeypot_triggered", "brute_force", "sql_injection"]:
            return critical_actions

        return normal_actions

    def _save_attack_log(self):
        """Save attack log to disk"""
        try:
            with open(self.attack_log_file, "w") as f:
                json.dump(self.attacks[-1000:], f, indent=2)  # Keep last 1000
        except Exception as e:
            logger.error(f"Failed to save attack log: {e}")

    def _save_user_alerts(self):
        """Save user alerts to disk"""
        try:
            with open(self.user_alerts_file, "w") as f:
                json.dump(self.user_alerts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save user alerts: {e}")

    def get_active_alerts(self) -> List[Dict]:
        """Get undismissed alerts"""
        return [a for a in self.user_alerts if not a.get("dismissed", False)]

    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert"""
        for alert in self.user_alerts:
            if alert["id"] == alert_id:
                alert["dismissed"] = True
                self._save_user_alerts()
                return True
        return False

    def get_recent_attacks(self, minutes: int = 60) -> List[Dict]:
        """Get attacks from last N minutes"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            a for a in self.attacks if datetime.fromisoformat(a["timestamp"]) > cutoff
        ]

    def get_attack_stats(self) -> Dict:
        """Get attack statistics"""
        from collections import defaultdict

        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for attack in self.attacks:
            by_type[attack["type"]] += 1
            by_severity[attack["severity"]] += 1

        return {
            "total_attacks": len(self.attacks),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "blocked_ips": len(self.blocked_ips),
            "active_alerts": len(self.get_active_alerts()),
            "top_attackers": sorted(
                self.ip_attack_count.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }


class HoneypotManager:
    """
    Manages honeypot trap files that detect unauthorized access
    """

    def __init__(self, trap_dir: str = "kilo_data/honeypots"):
        self.trap_dir = Path(trap_dir)
        self.trap_dir.mkdir(parents=True, exist_ok=True)

        self.trap_registry_file = self.trap_dir / "trap_registry.json"
        self.traps: Dict[str, Dict] = self._load_traps()

        # Create default traps
        self._create_default_traps()

        logger.info("🍯 Honeypot Manager initialized")

    def _load_traps(self) -> Dict:
        """Load trap registry"""
        if self.trap_registry_file.exists():
            try:
                with open(self.trap_registry_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load traps: {e}")
        return {}

    def _save_traps(self):
        """Save trap registry"""
        try:
            with open(self.trap_registry_file, "w") as f:
                json.dump(self.traps, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save traps: {e}")

    def _create_default_traps(self):
        """Create default honeypot files"""
        default_traps = [
            (
                "kilo_v2/public/.env",
                "DB_PASSWORD=honeypot_trap\nAPI_KEY=trap_detected\n",
                "Environment file trap",
            ),
            (
                "kilo_v2/public/config.php",
                "<?php $db_pass='trap'; ?>\n",
                "PHP config trap",
            ),
            (
                "kilo_v2/public/admin.php",
                "<?php header('Location: /trap'); ?>\n",
                "Admin panel trap",
            ),
            (
                "kilo_v2/public/backup.sql",
                "-- Trap file\nCREATE TABLE users (password VARCHAR(255));\n",
                "DB backup trap",
            ),
            (
                "kilo_data/.git_credentials",
                "[honeypot]\npassword=trap\n",
                "Git credentials trap",
            ),
        ]

        for path, content, desc in default_traps:
            self.create_trap(path, content, desc)

    def create_trap(self, path: str, content: str, description: str):
        """Create a honeypot trap file"""
        trap_file = Path(path)
        trap_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(trap_file, "w") as f:
                f.write(content)

            checksum = hashlib.sha256(content.encode()).hexdigest()

            self.traps[path] = {
                "checksum": checksum,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "triggers": 0,
                "last_triggered": None,
            }

            self._save_traps()
            logger.info(f"🍯 Created honeypot: {path}")

        except Exception as e:
            logger.error(f"Failed to create trap {path}: {e}")

    def check_trap(self, path: str) -> bool:
        """Check if trap was triggered (accessed/modified)"""
        if path not in self.traps:
            return False

        trap_file = Path(path)
        if not trap_file.exists():
            logger.critical(f"🚨 HONEYPOT DELETED: {path}")
            self.traps[path]["triggers"] += 1
            self.traps[path]["last_triggered"] = datetime.now().isoformat()
            self._save_traps()
            return True

        try:
            with open(trap_file, "r") as f:
                content = f.read()

            checksum = hashlib.sha256(content.encode()).hexdigest()

            if checksum != self.traps[path]["checksum"]:
                logger.critical(f"🚨 HONEYPOT MODIFIED: {path}")
                self.traps[path]["triggers"] += 1
                self.traps[path]["last_triggered"] = datetime.now().isoformat()
                self._save_traps()
                return True

        except Exception as e:
            logger.error(f"Failed to check trap {path}: {e}")

        return False

    def scan_all(self) -> List[str]:
        """Scan all traps and return triggered ones"""
        triggered = []
        for path in self.traps.keys():
            if self.check_trap(path):
                triggered.append(path)
        return triggered

    def get_stats(self) -> Dict:
        """Get honeypot statistics"""
        return {
            "total_traps": len(self.traps),
            "traps": [
                {
                    "path": path,
                    "description": info["description"],
                    "triggers": info["triggers"],
                    "last_triggered": info["last_triggered"],
                }
                for path, info in self.traps.items()
            ],
        }

    # --- Mount / network deployment extensions ---
    def deploy_to_mounts(self, extra_paths: Optional[List[str]] = None) -> Dict:
        """Scan common mount points (/mnt, /media) plus optional paths and drop lightweight traps.

        Only deploy to writable directories and avoid system critical mounts like /, /proc, /sys.
        """
        mount_roots = ["/mnt", "/media"]
        if extra_paths:
            mount_roots.extend(extra_paths)

        deployed = []
        skipped = []

        for root in mount_roots:
            if not os.path.isdir(root):
                skipped.append({"path": root, "reason": "not_directory"})
                continue
            # Enumerate subdirectories (each may be a mounted volume)
            try:
                entries = [os.path.join(root, e) for e in os.listdir(root)]
            except Exception as e:
                skipped.append({"path": root, "reason": f"list_error:{e}"})
                continue

            for entry in entries:
                if not os.path.isdir(entry):
                    continue
                # Check writable
                if not os.access(entry, os.W_OK):
                    skipped.append({"path": entry, "reason": "not_writable"})
                    continue
                # Deploy a small set of traps
                try:
                    trap_files = [
                        (
                            os.path.join(entry, ".env"),
                            "DB_PASSWORD=trap_mount\n",
                            "Mounted env trap",
                        ),
                        (
                            os.path.join(entry, "config_backup.sql"),
                            "-- backup trap\n",
                            "Mounted SQL backup trap",
                        ),
                        (
                            os.path.join(entry, "admin_panel.php"),
                            "<?php // trap ?>",
                            "Mounted admin trap",
                        ),
                    ]
                    for p, content, desc in trap_files:
                        self.create_trap(p, content, desc)
                        deployed.append(p)
                except Exception as e:
                    skipped.append({"path": entry, "reason": f"deploy_error:{e}"})

        return {"deployed": deployed, "skipped": skipped}


class QuietAgent:
    """
    Silent security monitoring - logs everything without alerting attackers
    """

    def __init__(self, log_dir: str = "kilo_data/quiet_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.observations: List[Dict] = []
        self.silent_mode = True

        logger.info("🤫 Quiet Agent initialized (stealth mode)")

    def observe(self, event_type: str, source_ip: str, details: Dict):
        """Silently log without alerting"""
        observation = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "source_ip": source_ip,
            "details": details,
        }

        self.observations.append(observation)
        self._persist_silent(observation)

    def _persist_silent(self, obs: Dict):
        """Silently save to disk"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"quiet_{date_str}.json"

        try:
            observations = []
            if log_file.exists():
                with open(log_file, "r") as f:
                    observations = json.load(f)

            observations.append(obs)

            with open(log_file, "w") as f:
                json.dump(observations, f, indent=2)
        except Exception:
            pass  # Silent failure - never alert attacker

    def get_observations(self, hours: int = 24) -> List[Dict]:
        """Get observations (admin only)"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            o
            for o in self.observations
            if datetime.fromisoformat(o["timestamp"]) > cutoff
        ]

    def analyze_patterns(self) -> Dict:
        """Analyze attack patterns"""
        from collections import defaultdict

        ip_freq = defaultdict(int)
        types = defaultdict(int)

        for obs in self.observations:
            ip_freq[obs["source_ip"]] += 1
            types[obs["type"]] += 1

        suspicious_ips = {ip: count for ip, count in ip_freq.items() if count > 10}

        return {
            "total_observations": len(self.observations),
            "unique_ips": len(ip_freq),
            "suspicious_ips": suspicious_ips,
            "event_types": dict(types),
        }


# Global instances
attack_logger = AttackLogger()
honeypot_manager = HoneypotManager()
quiet_agent = QuietAgent()


class SecurityEvent:
    """Represents a security event or threat."""

    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"

    def __init__(
        self, event_type: str, severity: str, description: str, details: Dict = None
    ):
        self.event_type = event_type
        self.severity = severity
        self.description = description
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        self.id = hashlib.sha256(
            f"{self.timestamp}{event_type}{description}".encode()
        ).hexdigest()[:16]

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.event_type,
            "severity": self.severity,
            "description": self.description,
            "details": self.details,
        }


class FileIntegrityMonitor:
    """Monitors critical files for tampering using checksums."""

    def __init__(self, monitored_paths: List[str]):
        self.monitored_paths = monitored_paths
        self.baseline = {}
        self.baseline_file = "kilo_data/file_integrity_baseline.json"
        # Developer whitelist allows certain files to be changed in dev/test
        # environments without triggering critical alerts. This file should
        # contain a JSON array of path patterns (supports glob-style matching).
        self.whitelist_file = "kilo_data/dev_whitelist.json"
        self.whitelist = self._load_whitelist()
        self._load_baseline()

    def _calculate_checksum(self, filepath: str) -> Optional[str]:
        """Calculate SHA256 checksum of a file."""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Could not checksum {filepath}: {e}")
            return None

    def _load_baseline(self):
        """Load baseline checksums from disk."""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, "r") as f:
                    self.baseline = json.load(f)
                logger.info(f"Loaded integrity baseline: {len(self.baseline)} files")
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            self.baseline = {}

    def _load_whitelist(self) -> List[str]:
        """Load developer whitelist (patterns) from disk.

        Returns list of glob patterns. If file missing, returns empty list.
        """
        try:
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        logger.info(f"Loaded dev whitelist: {len(data)} patterns")
                        return data
        except Exception as e:
            logger.warning(f"Failed to load dev whitelist: {e}")
        return []

    def save_whitelist(self, patterns: List[str]):
        """Persist a developer whitelist (overwrites existing file)."""
        try:
            os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
            with open(self.whitelist_file, "w") as f:
                json.dump(patterns, f, indent=2)
            self.whitelist = patterns
            logger.info(f"Saved dev whitelist ({len(patterns)} patterns)")
            return True
        except Exception as e:
            logger.error(f"Failed to save dev whitelist: {e}")
            return False

    def save_baseline(self):
        """Save current checksums as new baseline."""
        try:
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            self.baseline = {}

            for path_pattern in self.monitored_paths:
                # Expand glob patterns
                for filepath in Path(".").glob(path_pattern):
                    if filepath.is_file():
                        checksum = self._calculate_checksum(str(filepath))
                        if checksum:
                            self.baseline[str(filepath)] = {
                                "checksum": checksum,
                                "size": os.path.getsize(filepath),
                                "modified": os.path.getmtime(filepath),
                            }

            with open(self.baseline_file, "w") as f:
                json.dump(self.baseline, f, indent=2)

            logger.info(f"Saved new baseline: {len(self.baseline)} files")
            return True
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False

    def check_integrity(self) -> List[SecurityEvent]:
        """Check if monitored files have been tampered with."""
        events = []
        # If running under pytest or explicitly in test-mode, skip integrity
        # enforcement to avoid false positives during development tests.
        try:
            from . import config as kilo_config
        except Exception:
            try:
                import kilo_v2.config as kilo_config
            except Exception:
                kilo_config = None

        if kilo_config and getattr(kilo_config, "IS_TESTING", False):
            logger.debug("Skipping integrity checks in test mode (IS_TESTING)")
            return []

        import fnmatch

        for filepath, baseline_data in self.baseline.items():
            if not os.path.exists(filepath):
                # Skip if whitelisted
                if any(fnmatch.fnmatch(filepath, pat) for pat in self.whitelist):
                    logger.info(f"Whitelisted file deletion ignored: {filepath}")
                    continue
                events.append(
                    SecurityEvent(
                        "file_deleted",
                        SecurityEvent.SEVERITY_CRITICAL,
                        f"Protected file deleted: {filepath}",
                        {"filepath": filepath, "baseline": baseline_data},
                    )
                )
                continue

            current_checksum = self._calculate_checksum(filepath)
            if current_checksum and current_checksum != baseline_data["checksum"]:
                # If the path matches a developer whitelist pattern, treat as non-critical
                if any(fnmatch.fnmatch(filepath, pat) for pat in self.whitelist):
                    logger.warning(f"Whitelisted file modified (ignored): {filepath}")
                    continue

                events.append(
                    SecurityEvent(
                        "file_modified",
                        SecurityEvent.SEVERITY_CRITICAL,
                        f"Protected file tampered with: {filepath}",
                        {
                            "filepath": filepath,
                            "expected_checksum": baseline_data["checksum"],
                            "current_checksum": current_checksum,
                            "size_changed": os.path.getsize(filepath)
                            != baseline_data["size"],
                        },
                    )
                )

        return events


class NetworkMonitor:
    """Monitors network connections for suspicious activity."""

    def __init__(self):
        self.suspicious_ips = set()
        self.connection_log = []
        self.max_log_size = 1000

    def get_active_connections(self) -> List[Dict]:
        """Get list of active network connections."""
        connections = []
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED" and conn.raddr:
                    connections.append(
                        {
                            "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}",
                            "status": conn.status,
                            "pid": conn.pid,
                        }
                    )
        except Exception as e:
            logger.warning(f"Error getting connections: {e}")

        return connections

    def detect_suspicious_connections(self) -> List[SecurityEvent]:
        """Detect potentially suspicious network activity."""
        events = []
        connections = self.get_active_connections()

        # Store in log
        self.connection_log.extend(connections)
        if len(self.connection_log) > self.max_log_size:
            self.connection_log = self.connection_log[-self.max_log_size :]

        # Check for suspicious ports
        suspicious_ports = [31337, 12345, 54321, 9999]  # Known backdoor ports

        for conn in connections:
            remote_addr = conn.get("remote_addr") or ""
            if ":" not in remote_addr:
                continue

            remote_ip, _, port_str = remote_addr.partition(":")
            try:
                remote_port = int(port_str)
            except (TypeError, ValueError):
                continue

            # Check for backdoor ports
            if remote_port in suspicious_ports:
                events.append(
                    SecurityEvent(
                        "suspicious_port",
                        SecurityEvent.SEVERITY_CRITICAL,
                        f"Connection to suspicious port detected",
                        {"connection": conn, "port": remote_port},
                    )
                )
                self.suspicious_ips.add(remote_ip)

        return events

    def trace_connection_origin(self, ip_address: str) -> Dict:
        """
        Trace information about a remote IP (LEGAL: passive reconnaissance only).
        Does NOT perform active attacks.
        """
        info = {
            "ip": ip_address,
            "timestamp": datetime.now().isoformat(),
            "hostname": None,
            "location": None,  # Would require GeoIP database
            "is_local": False,
        }

        try:
            # Check if local/private IP
            ip_parts = ip_address.split(".")
            if ip_parts[0] in ["10", "127"] or (
                ip_parts[0] == "192" and ip_parts[1] == "168"
            ):
                info["is_local"] = True

            # Reverse DNS lookup (legal and passive)
            try:
                info["hostname"] = socket.gethostbyaddr(ip_address)[0]
            except:
                info["hostname"] = None

            logger.info(f"Traced connection: {ip_address} -> {info['hostname']}")

        except Exception as e:
            logger.warning(f"Error tracing IP {ip_address}: {e}")

        return info


class CaddyLogParser:
    """
    Parses Caddy logs to detect blocked attacks
    """

    def __init__(self, log_source: str = "stdout"):
        self.log_source = log_source
        self.last_position = 0
        self.suspicious_paths = [
            "/.env",
            "/admin",
            "/wp-admin",
            "/.git",
            "/config.php",
            "/phpmyadmin",
            "/.aws",
            "/backup",
            ".sql",
            ".bak",
        ]
        self.suspicious_agents = [
            "sqlmap",
            "nmap",
            "nikto",
            "masscan",
            "nessus",
            "acunetix",
            "metasploit",
            "burp",
            "owasp",
        ]

        logger.info("📋 Caddy Log Parser initialized")

    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse a single (possibly malformed) Caddy log line.

        Normalization strategy:
        1. Try direct json.loads.
        2. If that fails, attempt regex-based quoting of bare keys for legacy pseudo-JSON lines.
        3. If still failing, return None.
        """
        if not line:
            return None
        log_entry = None
        try:
            log_entry = json.loads(line)
        except Exception:
            # Attempt normalization for lines like: {level=INFO time=... msg="..."}
            try:
                import re

                candidate = line.strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    # Quote keys before '=' and convert '=' to ':'
                    candidate = re.sub(r"(\b[\w.-]+)=", r'"\1":', candidate)
                    # Wrap unquoted values following : until comma/space/brace in quotes
                    candidate = re.sub(r':(?!\s*["])([^\s{},]+)', r':"\1"', candidate)
                    candidate = candidate.replace("'", '"')
                    log_entry = json.loads(candidate)
            except Exception:
                log_entry = None
        if not isinstance(log_entry, dict):
            return None
        # Extract relevant fields
        status = log_entry.get("status", 0)
        path = log_entry.get("request", {}).get("uri", "")
        client_ip = log_entry.get("request", {}).get("remote_ip", "unknown")
        headers = log_entry.get("request", {}).get("headers", {}) or {}
        if isinstance(headers, dict):
            ua_val = headers.get("User-Agent")
            if isinstance(ua_val, list):
                user_agent = ua_val[0] if ua_val else ""
            else:
                user_agent = ua_val or ""
        else:
            user_agent = ""

        if status in [403, 404]:
            for sus_path in self.suspicious_paths:
                if sus_path in path.lower():
                    return {
                        "type": "malicious_path",
                        "severity": "warning",
                        "ip": client_ip,
                        "path": path,
                        "user_agent": user_agent,
                        "status": status,
                    }
            for sus_agent in self.suspicious_agents:
                if sus_agent in user_agent.lower():
                    return {
                        "type": "suspicious_agent",
                        "severity": "critical",
                        "ip": client_ip,
                        "path": path,
                        "user_agent": user_agent,
                        "status": status,
                    }
        # SQL injection patterns
        if any(
            sql in path.lower()
            for sql in ["union", "select", "drop", "insert", "0x", "'"]
        ):
            return {
                "type": "sql_injection",
                "severity": "critical",
                "ip": client_ip,
                "path": path,
                "user_agent": user_agent,
                "status": status,
            }
        # Path traversal
        if "../" in path or "..\\" in path:
            return {
                "type": "path_traversal",
                "severity": "critical",
                "ip": client_ip,
                "path": path,
                "user_agent": user_agent,
                "status": status,
            }
        # XSS patterns
        if any(xss in path.lower() for xss in ["<script", "javascript:", "onerror="]):
            return {
                "type": "xss_attempt",
                "severity": "warning",
                "ip": client_ip,
                "path": path,
                "user_agent": user_agent,
                "status": status,
            }
        return None

    def tail_logs(
        self,
        log_path: str,
        callback,
        poll_interval: float = 2.0,
        stop_event: Optional[threading.Event] = None,
    ):
        """Tail Caddy JSON log file and invoke callback for each detected attack.

        Parameters:
            log_path: Path to Caddy access log file.
            callback: Function accepting (attack_dict) when an attack is parsed.
            poll_interval: Seconds between file polling when no new data.
            stop_event: Optional threading.Event to signal stop.
        """
        logger.info(f"📂 Starting Caddy log tailer on {log_path}")
        path_obj = Path(log_path)
        logger.info(f"🪝 tail_logs invoked. Exists? {path_obj.exists()}")

        # Ensure file exists (wait briefly if not yet created by Caddy)
        wait_start = time.time()
        while not path_obj.exists():
            logger.debug(f"⏳ Waiting for log file to appear: {log_path}")
            if stop_event and stop_event.is_set():
                logger.info("🛑 Caddy log tailer stopped before file appeared")
                return
            if time.time() - wait_start > 30:  # 30s timeout
                logger.warning(
                    f"Caddy log file {log_path} not found after 30s; aborting tail"
                )
                return
            time.sleep(1)

        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            # Start at end of file to avoid historical flood
            f.seek(0, os.SEEK_END)
            last_inode = self._get_inode(path_obj)
            logger.info(f"📖 Caddy log file opened for tailing: {log_path}")

            while True:
                if stop_event and stop_event.is_set():
                    logger.info("🛑 Stop signal received for Caddy log tailer")
                    break

                line = f.readline()
                if not line:
                    # Handle rotation: inode change
                    current_inode = self._get_inode(path_obj)
                    if current_inode != last_inode:
                        logger.info("🔁 Detected Caddy log rotation; reopening file")
                        try:
                            f.close()
                            f = open(log_path, "r", encoding="utf-8", errors="ignore")
                            last_inode = current_inode
                            f.seek(0, os.SEEK_END)  # Skip historical rotated content
                        except Exception as e:
                            logger.error(f"Error reopening rotated log: {e}")
                    time.sleep(poll_interval)
                    continue

                attack = self.parse_log_line(line.strip())
                logger.debug(f"CaddyLogTail raw line: {line.strip()}")
                if attack:
                    try:
                        callback(attack)
                    except Exception as e:
                        logger.error(f"Attack callback error: {e}")
                else:
                    logger.debug("CaddyLogTail parsed no attack from line")

    def _get_inode(self, path: Path) -> int:
        try:
            return path.stat().st_ino
        except Exception:
            return -1


class SecurityMonitor:
    """
    Main security monitoring system for Kilo Guardian.
    Provides intrusion detection and response capabilities.
    """

    # Response modes
    MODE_WATCH = "watch"  # Monitor and log only
    MODE_ALERT = "alert"  # Alert user but no action
    MODE_LOCKDOWN = "lockdown"  # Lock down system
    MODE_WIPE = "wipe"  # Wipe sensitive data
    MODE_SNOOP = "snoop"  # Trace attacker (passive reconnaissance)
    MODE_DEFEND = "defend"  # Active defense (legal: block, disconnect)

    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.log_tail_thread = None
        self.stop_tail_event = threading.Event()
        self.caddy_observer = None  # watchdog observer instance if used
        self.response_mode = self.MODE_ALERT  # Default to alerting
        self.events = []
        self.max_events = 5000

        # Initialize sub-monitors
        self.file_monitor = FileIntegrityMonitor(
            [
                "kilo_v2/*.py",
                "kilo_v2/plugins/*.py",
                "kilo_secrets.enc",
                "kilo_salt.bin",
                "kilo_guardian_keep.db",
                "data_core.py",
                "run_gunicorn.sh",
            ]
        )

        self.network_monitor = NetworkMonitor()
        # Caddy log integration
        try:
            from . import config as kilo_config
        except Exception:
            import config as kilo_config
        self.caddy_log_path = getattr(
            kilo_config, "CADDY_LOG_PATH", "logs/caddy_access.log"
        )
        self.caddy_parser = CaddyLogParser()
        self._caddy_last_offset = 0

        # Security state
        self.is_locked_down = False
        self.watch_mode_active = False
        self.watch_log = []

        logger.info("🔒 Security Monitor initialized")

    def create_baseline(self):
        """Create initial integrity baseline."""
        return self.file_monitor.save_baseline()

    def set_response_mode(self, mode: str):
        """Set how system responds to threats."""
        valid_modes = [
            self.MODE_WATCH,
            self.MODE_ALERT,
            self.MODE_LOCKDOWN,
            self.MODE_WIPE,
            self.MODE_SNOOP,
            self.MODE_DEFEND,
        ]

        if mode not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")

        old_mode = self.response_mode
        self.response_mode = mode

        logger.warning(f"⚠️ Security response mode changed: {old_mode} -> {mode}")

        event = SecurityEvent(
            "mode_change",
            SecurityEvent.SEVERITY_WARNING,
            f"Security response mode changed to: {mode}",
            {"old_mode": old_mode, "new_mode": mode},
        )
        self._log_event(event)

        return True

    def _log_event(self, event: SecurityEvent):
        """Log a security event."""
        self.events.append(event)

        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Log to file
        try:
            log_file = "kilo_data/security_events.log"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to write security event log: {e}")

        # Also log to main logger
        if event.severity == SecurityEvent.SEVERITY_CRITICAL:
            logger.critical(f"🚨 SECURITY: {event.description}")
        elif event.severity == SecurityEvent.SEVERITY_WARNING:
            logger.warning(f"⚠️ SECURITY: {event.description}")
        else:
            logger.info(f"ℹ️ SECURITY: {event.description}")

    def _handle_threat(self, events: List[SecurityEvent]):
        """Handle detected threats based on response mode."""
        if not events:
            return

        for event in events:
            self._log_event(event)

        if self.response_mode == self.MODE_WATCH:
            self._activate_watch_mode(events)

        elif self.response_mode == self.MODE_ALERT:
            # Just logging (already done above)
            pass

        elif self.response_mode == self.MODE_LOCKDOWN:
            self._initiate_lockdown(events)

        elif self.response_mode == self.MODE_WIPE:
            self._wipe_sensitive_data(events)

        elif self.response_mode == self.MODE_SNOOP:
            self._snoop_attacker(events)

        elif self.response_mode == self.MODE_DEFEND:
            self._active_defense(events)

    def _activate_watch_mode(self, events: List[SecurityEvent]):
        """
        WATCH MODE: Monitor attacker activities in real-time.
        Records all actions without interfering.
        """
        if not self.watch_mode_active:
            self.watch_mode_active = True
            logger.warning("👁️ WATCH MODE ACTIVATED - Monitoring attacker activity")

        # Log attacker actions
        for event in events:
            watch_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event.to_dict(),
                "connections": self.network_monitor.get_active_connections(),
                "processes": self._get_suspicious_processes(),
            }

            self.watch_log.append(watch_entry)
            logger.info(f"📹 WATCH LOG: {event.description}")

    def _snoop_attacker(self, events: List[SecurityEvent]):
        """
        SNOOP MODE: Passive reconnaissance on attacker.
        LEGAL: Only uses passive techniques (DNS lookups, public data).
        DOES NOT perform active attacks.
        """
        logger.warning("🕵️ SNOOP MODE: Tracing attacker origin")

        connections = self.network_monitor.get_active_connections()
        traces = []

        for conn in connections:
            remote_addr = conn.get("remote_addr") or ""
            if ":" not in remote_addr:
                continue

            remote_ip = remote_addr.split(":", 1)[0]

            # Skip local connections
            if remote_ip.startswith("127.") or remote_ip.startswith("192.168."):
                continue

            trace = self.network_monitor.trace_connection_origin(remote_ip)
            traces.append(trace)

            logger.info(f"🔍 Traced: {remote_ip} -> {trace.get('hostname', 'Unknown')}")

        # Store trace results
        trace_event = SecurityEvent(
            "attacker_traced",
            SecurityEvent.SEVERITY_WARNING,
            f"Traced {len(traces)} suspicious connections",
            {"traces": traces},
        )
        self._log_event(trace_event)

    def _active_defense(self, events: List[SecurityEvent]):
        """
        DEFEND MODE: Active but LEGAL defensive measures.
        - Blocks suspicious IPs (firewall rules)
        - Kills suspicious processes
        - Disconnects suspicious connections

        DOES NOT perform offensive hacking (illegal).
        """
        logger.critical("🛡️ ACTIVE DEFENSE INITIATED")

        # Block suspicious IPs using firewall
        for ip in self.network_monitor.suspicious_ips:
            self._block_ip(ip)

        # Kill suspicious processes
        suspicious_procs = self._get_suspicious_processes()
        for proc_info in suspicious_procs:
            try:
                proc = psutil.Process(proc_info["pid"])
                logger.warning(
                    f"🔪 Terminating suspicious process: {proc_info['name']} (PID {proc_info['pid']})"
                )
                proc.terminate()

                # Force kill if still alive after 5 seconds
                time.sleep(5)
                if proc.is_running():
                    proc.kill()

            except Exception as e:
                logger.error(f"Failed to terminate process {proc_info['pid']}: {e}")

        defense_event = SecurityEvent(
            "active_defense",
            SecurityEvent.SEVERITY_CRITICAL,
            "Active defense measures deployed",
            {
                "blocked_ips": list(self.network_monitor.suspicious_ips),
                "killed_processes": suspicious_procs,
            },
        )
        self._log_event(defense_event)

    def _block_ip(self, ip_address: str):
        """
        Block an IP address using firewall rules (LEGAL defensive measure).
        """
        try:
            # Use iptables on Linux
            if os.path.exists("/usr/sbin/iptables"):
                cmd = [
                    "sudo",
                    "iptables",
                    "-A",
                    "INPUT",
                    "-s",
                    ip_address,
                    "-j",
                    "DROP",
                ]
                subprocess.run(cmd, check=True)
                logger.warning(f"🚫 Blocked IP: {ip_address}")
                return True
        except Exception as e:
            logger.error(f"Failed to block IP {ip_address}: {e}")
            return False

    def _initiate_lockdown(self, events: List[SecurityEvent]):
        """
        LOCKDOWN MODE: Lock system and prevent access.
        """
        if self.is_locked_down:
            return

        self.is_locked_down = True
        logger.critical("🔐 SYSTEM LOCKDOWN INITIATED")

        # Create lockdown marker file
        try:
            with open("kilo_data/SYSTEM_LOCKED", "w") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "reason": "Security threat detected",
                            "events": [e.to_dict() for e in events],
                        }
                    )
                )
        except Exception as e:
            logger.error(f"Failed to create lockdown marker: {e}")

        lockdown_event = SecurityEvent(
            "system_lockdown",
            SecurityEvent.SEVERITY_CRITICAL,
            "System locked down due to security threat",
            {"trigger_events": [e.to_dict() for e in events]},
        )
        self._log_event(lockdown_event)

    def _wipe_sensitive_data(self, events: List[SecurityEvent]):
        """
        WIPE MODE: Securely delete sensitive data.
        CRITICAL: This is irreversible!
        """
        logger.critical("💥 DATA WIPE INITIATED - THIS IS IRREVERSIBLE!")

        # Files to wipe
        sensitive_files = [
            "kilo_secrets.enc",
            "kilo_salt.bin",
            "kilo_guardian_keep.db",
            "kilo_data/preferences.json",
            "kilo_data/faces.json",
            "finance.db",
        ]

        wiped = []
        for filepath in sensitive_files:
            if os.path.exists(filepath):
                try:
                    # Secure delete: overwrite with random data before deleting
                    size = os.path.getsize(filepath)
                    with open(filepath, "wb") as f:
                        f.write(os.urandom(size))
                    os.remove(filepath)
                    wiped.append(filepath)
                    logger.warning(f"🗑️ WIPED: {filepath}")
                except Exception as e:
                    logger.error(f"Failed to wipe {filepath}: {e}")

        wipe_event = SecurityEvent(
            "data_wiped",
            SecurityEvent.SEVERITY_CRITICAL,
            f"Sensitive data wiped: {len(wiped)} files deleted",
            {"wiped_files": wiped, "trigger_events": [e.to_dict() for e in events]},
        )
        self._log_event(wipe_event)

    def _get_suspicious_processes(self) -> List[Dict]:
        """Detect potentially suspicious processes."""
        suspicious = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "connections"]):
                try:
                    # Check for suspicious process names
                    name = proc.info["name"].lower()
                    cmdline = " ".join(proc.info["cmdline"] or []).lower()

                    # Suspicious indicators
                    indicators = [
                        "backdoor",
                        "rootkit",
                        "keylog",
                        "rat",
                        "trojan",
                        "nc -l",
                        "ncat -l",
                    ]

                    if any(ind in name or ind in cmdline for ind in indicators):
                        suspicious.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cmdline": cmdline,
                                "connections": len(proc.info.get("connections", [])),
                            }
                        )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.error(f"Error scanning processes: {e}")

        return suspicious

    def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("🔍 Security monitoring started")

        while self.running:
            try:
                # Check file integrity
                integrity_events = self.file_monitor.check_integrity()
                if integrity_events:
                    self._handle_threat(integrity_events)

                # Check honeypots
                triggered_traps = honeypot_manager.scan_all()
                if triggered_traps:
                    for trap in triggered_traps:
                        trap_event = SecurityEvent(
                            "honeypot_triggered",
                            SecurityEvent.SEVERITY_CRITICAL,
                            f"🍯 HONEYPOT TRIGGERED: {trap}",
                            {
                                "trap_file": trap,
                                "description": honeypot_manager.traps[trap][
                                    "description"
                                ],
                            },
                        )
                        self._handle_threat([trap_event])

                        # Log to attack logger
                        attack_logger.log_attack(
                            "honeypot_triggered",
                            "unknown",
                            {"trap_file": trap},
                            severity="critical",
                        )

                        # Silent observation
                        quiet_agent.observe(
                            "honeypot_triggered", "unknown", {"trap_file": trap}
                        )

                # Check network
                network_events = self.network_monitor.detect_suspicious_connections()
                if network_events:
                    self._handle_threat(network_events)

                # Parse new Caddy log lines inline (fallback if tail thread absent)
                try:
                    self._process_caddy_log_incremental()
                except Exception as e:
                    logger.debug(f"Caddy incremental parse error: {e}")

                # Check for suspicious processes
                suspicious_procs = self._get_suspicious_processes()
                if suspicious_procs:
                    proc_event = SecurityEvent(
                        "suspicious_process",
                        SecurityEvent.SEVERITY_WARNING,
                        f"Detected {len(suspicious_procs)} suspicious processes",
                        {"processes": suspicious_procs},
                    )
                    self._handle_threat([proc_event])

                # Sleep between checks
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(30)  # Back off on errors

        logger.info("🔍 Security monitoring stopped")

    def start_monitoring(self):
        """Start the security monitoring thread."""
        if self.running:
            logger.warning("Security monitoring already running")
            return False

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Prefer filesystem watcher if available, else fall back to tail thread
        if self.caddy_log_path:

            def _attack_cb(attack_dict):
                evt = SecurityEvent(
                    attack_dict["type"],
                    (
                        SecurityEvent.SEVERITY_CRITICAL
                        if attack_dict["severity"] == "critical"
                        else SecurityEvent.SEVERITY_WARNING
                    ),
                    f"Caddy detected {attack_dict['type']} at {attack_dict.get('path','')}",
                    attack_dict,
                )
                self._handle_threat([evt])
                attack_logger.log_attack(
                    attack_dict["type"],
                    attack_dict.get("ip", "unknown"),
                    attack_dict,
                    severity=attack_dict["severity"],
                )
                quiet_agent.observe(
                    attack_dict["type"], attack_dict.get("ip", "unknown"), attack_dict
                )

            if _WATCHDOG_AVAILABLE:
                try:
                    self._start_caddy_watcher(_attack_cb)
                    logger.info(
                        f"🕵️ Watchdog file observer started for {self.caddy_log_path}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Watchdog observer failed ({e}); falling back to tail thread"
                    )
                    self.stop_tail_event.clear()
                    self.log_tail_thread = threading.Thread(
                        target=self.caddy_parser.tail_logs,
                        args=(
                            self.caddy_log_path,
                            _attack_cb,
                            2.0,
                            self.stop_tail_event,
                        ),
                        daemon=True,
                    )
                    self.log_tail_thread.start()
            else:
                self.stop_tail_event.clear()
                self.log_tail_thread = threading.Thread(
                    target=self.caddy_parser.tail_logs,
                    args=(self.caddy_log_path, _attack_cb, 2.0, self.stop_tail_event),
                    daemon=True,
                )
                self.log_tail_thread.start()
                logger.info(
                    f"📡 Caddy log tailer started (no watchdog): {self.caddy_log_path}"
                )

        logger.info("✅ Security monitoring started")
        return True

    def stop_monitoring(self):
        """Stop the security monitoring thread."""
        if not self.running:
            return False

        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        # Stop log tailer
        if self.log_tail_thread and self.log_tail_thread.is_alive():
            self.stop_tail_event.set()
            self.log_tail_thread.join(timeout=5)
            logger.info("🛑 Caddy log tailer stopped")
        self.log_tail_thread = None
        # Stop watchdog observer if running
        if self.caddy_observer:
            try:
                self.caddy_observer.stop()
                self.caddy_observer.join(timeout=5)
                logger.info("🛑 Watchdog observer stopped")
            except Exception as e:
                logger.debug(f"Error stopping watchdog observer: {e}")
            self.caddy_observer = None

        logger.info("⏹️ Security monitoring stopped")
        return True

    def get_status(self) -> Dict:
        """Get current security status."""
        recent_events = self.events[-50:] if self.events else []

        return {
            "monitoring_active": self.running,
            "response_mode": self.response_mode,
            "is_locked_down": self.is_locked_down,
            "watch_mode_active": self.watch_mode_active,
            "total_events": len(self.events),
            "recent_events": [e.to_dict() for e in recent_events],
            "suspicious_ips": list(self.network_monitor.suspicious_ips),
            "file_integrity_baseline": len(self.file_monitor.baseline),
            "active_connections": len(self.network_monitor.get_active_connections()),
        }

    def _process_caddy_log_incremental(self):
        """Incrementally read newly appended Caddy log lines and process attacks."""
        if not self.caddy_log_path:
            return
        path = Path(self.caddy_log_path)
        if not path.exists():
            return
        size = path.stat().st_size
        if size == self._caddy_last_offset:
            return  # No new data
        if size < self._caddy_last_offset:
            # File truncated/rotated
            self._caddy_last_offset = 0
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self._caddy_last_offset)
            new_data = f.read()
        self._caddy_last_offset = size
        for line in new_data.splitlines():
            line = line.strip()
            if not line:
                continue
            attack = self.caddy_parser.parse_log_line(line)
            if attack:
                evt = SecurityEvent(
                    attack["type"],
                    (
                        SecurityEvent.SEVERITY_CRITICAL
                        if attack["severity"] == "critical"
                        else SecurityEvent.SEVERITY_WARNING
                    ),
                    f"Caddy detected {attack['type']} at {attack.get('path','')}",
                    attack,
                )
                self._handle_threat([evt])
                attack_logger.log_attack(
                    attack["type"],
                    attack.get("ip", "unknown"),
                    attack,
                    severity=attack["severity"],
                )
                quiet_agent.observe(attack["type"], attack.get("ip", "unknown"), attack)

    def get_events(
        self, severity: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """Get security events, optionally filtered by severity."""
        events = self.events

        if severity:
            events = [e for e in events if e.severity == severity]

        # Return most recent first
        return [e.to_dict() for e in reversed(events[-limit:])]

    def unlock_system(self, confirmation_code: str) -> bool:
        """
        Unlock system after lockdown.
        Requires confirmation code to prevent unauthorized unlock.
        """
        # In production, this would verify against a secure hash
        expected_code = hashlib.sha256(b"KILO_UNLOCK_2025").hexdigest()[:16]

        if confirmation_code != expected_code:
            logger.error("❌ Invalid unlock code")
            return False

        self.is_locked_down = False

        try:
            os.remove("kilo_data/SYSTEM_LOCKED")
        except:
            pass

        unlock_event = SecurityEvent(
            "system_unlocked",
            SecurityEvent.SEVERITY_WARNING,
            "System unlocked by administrator",
            {"timestamp": datetime.now().isoformat()},
        )
        self._log_event(unlock_event)

        logger.info("✅ System unlocked")
        return True

    # ----------- Watchdog-based log watcher -----------
    def _start_caddy_watcher(self, attack_callback):
        """Start a watchdog observer to monitor the Caddy JSON log file for changes.

        This watcher handles rotation: when file is moved or deleted and recreated
        we reset the offset. Uses an event handler tracking modifications.
        """
        if not _WATCHDOG_AVAILABLE:
            raise RuntimeError("watchdog not installed")
        log_path = Path(self.caddy_log_path)
        directory = log_path.parent
        file_name = log_path.name
        self._caddy_last_offset = 0

        class _CaddyHandler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer
                super().__init__()

            def on_modified(self, event):
                if event.is_directory:
                    return
                if Path(event.src_path).name != file_name:
                    return
                self._read_new_lines()

            def on_created(self, event):
                if Path(event.src_path).name == file_name:
                    self.outer._caddy_last_offset = 0
                    self._read_new_lines()

            def on_moved(self, event):
                # If original file moved (rotation), reset offset
                if Path(event.src_path).name == file_name:
                    self.outer._caddy_last_offset = 0
                # If new file is target log, read from start
                if Path(event.dest_path).name == file_name:
                    self.outer._caddy_last_offset = 0
                    self._read_new_lines()

            def _read_new_lines(self):
                try:
                    if not log_path.exists():
                        return
                    size = log_path.stat().st_size
                    if size < self.outer._caddy_last_offset:
                        self.outer._caddy_last_offset = 0
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self.outer._caddy_last_offset)
                        data = f.read()
                    self.outer._caddy_last_offset = size
                    for line in data.splitlines():
                        attack = self.outer.caddy_parser.parse_log_line(line.strip())
                        if attack:
                            try:
                                attack_callback(attack)
                            except Exception as e:
                                logger.error(f"Attack callback error (watchdog): {e}")
                except Exception as e:
                    logger.debug(f"Watchdog read error: {e}")

        handler = _CaddyHandler(self)
        observer = Observer()
        observer.schedule(handler, str(directory), recursive=False)
        observer.start()
        self.caddy_observer = observer


# Global security monitor instance
_security_monitor = None


def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


# ---------------------------------------------------------------------------
# CLI entrypoint — allows running:
#   python -m kilo_v2.security_monitor --create-baseline
#   python -m kilo_v2.security_monitor --status
# ---------------------------------------------------------------------------
def _cli_main():
    import argparse

    parser = argparse.ArgumentParser(description="Kilo Guardian Security Monitor CLI")
    parser.add_argument(
        "--create-baseline",
        action="store_true",
        help="Snapshot current monitored files as the integrity baseline.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current security status (events, mode, etc.).",
    )
    parser.add_argument(
        "--clear-whitelist",
        action="store_true",
        help="Clear the developer whitelist (for production lockdown).",
    )
    args = parser.parse_args()

    monitor = get_security_monitor()

    if args.create_baseline:
        print("Creating integrity baseline...")
        ok = monitor.file_monitor.save_baseline()
        if ok:
            print(f"✅ Baseline saved: {monitor.file_monitor.baseline_file}")
            print(f"   Files recorded: {len(monitor.file_monitor.baseline)}")
        else:
            print("❌ Failed to save baseline")
            raise SystemExit(1)

    elif args.clear_whitelist:
        print("Clearing developer whitelist for production...")
        ok = monitor.file_monitor.save_whitelist([])
        if ok:
            print(f"✅ Whitelist cleared: {monitor.file_monitor.whitelist_file}")
        else:
            print("❌ Failed to clear whitelist")
            raise SystemExit(1)

    elif args.status:
        status = monitor.get_status()
        import pprint

        pprint.pprint(status)

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
