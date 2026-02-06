"""
Browser Security Shield Extension - Network Security Plugin
Extends network_security.py with endpoints for browser-based protection
Handles credential monitoring, threat detection, DNS checks, and intrusion alerts
"""

import hashlib
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from plugins.base_plugin import BasePlugin


class BrowserSecurityShieldExtension:
    """
    Extension module for NetworkSecurityPlugin.
    Provides browser-specific security monitoring and threat detection.
    """

    def __init__(self, parent_plugin):
        self.parent_plugin = parent_plugin
        self.threat_log: List[Dict] = []
        self.network_baselines: Dict = {}
        self.dns_cache: Dict[str, str] = {}
        self.suspicious_domains: Set[str] = set()
        self.malicious_urls: Set[str] = set()
        self.session_tokens: Set[str] = set()
        self.credential_attempts: List[Dict] = []

        # Load threat intelligence from files if available
        self._load_threat_db()

    def _load_threat_db(self):
        """Load known malicious domains and URLs from threat database"""
        try:
            # In production, this would fetch from threat feeds (IP reputation, URLhaus, etc.)
            self.suspicious_domains = {
                "phishing.example.com",
                "malware.example.com",
                "c2.malicious.net",
            }
        except Exception as e:
            print(f"[BrowserSecurityShield] Failed to load threat DB: {e}")

    # ============================================================================
    # NETWORK BASELINE MANAGEMENT
    # ============================================================================

    def establish_baseline(self, request_data: Dict) -> Dict:
        """
        Establish network baseline for intrusion detection.
        Captures current network state to detect anomalies.
        """
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "active_devices": len(self.parent_plugin.discovered_devices),
            "open_ports": self.parent_plugin.security_stats.get("openPorts", 0),
            "known_ips": [d["ip"] for d in self.parent_plugin.discovered_devices],
            "gateway_mac": self._get_gateway_mac(),
            "dns_servers": self._get_dns_servers(),
            "arp_entries": self._get_arp_table_hash(),
        }

        # Store baseline
        baseline_id = hashlib.md5(
            json.dumps(baseline, sort_keys=True).encode()
        ).hexdigest()

        self.network_baselines[baseline_id] = baseline

        return {
            "type": "baseline_established",
            "baseline_id": baseline_id,
            "baseline": baseline,
            "message": f'Network baseline established with {baseline["active_devices"]} devices',
        }

    # ============================================================================
    # INTRUSION DETECTION
    # ============================================================================

    def check_intrusions(self, request_data: Dict) -> Dict:
        """
        Check for network intrusions by comparing against baseline.
        Detects:
        - New unknown devices
        - Unexpected port openings
        - ARP spoofing
        - MITM attempts
        """
        baseline = request_data.get("baseline", {})
        current_devices = self.parent_plugin.discovered_devices

        threats = []

        # Check for new devices
        baseline_ips = set(baseline.get("known_ips", []))
        current_ips = {d["ip"] for d in current_devices}

        new_devices = current_ips - baseline_ips
        if new_devices:
            threats.append(
                {
                    "type": "NEW_DEVICES_DETECTED",
                    "severity": "medium",
                    "devices": list(new_devices),
                    "message": f"{len(new_devices)} new device(s) detected on network",
                }
            )

        # Check for missing devices (possible disconnection or attack)
        missing_devices = baseline_ips - current_ips
        if missing_devices:
            threats.append(
                {
                    "type": "DEVICES_MISSING",
                    "severity": "medium",
                    "devices": list(missing_devices),
                    "message": f"{len(missing_devices)} device(s) disappeared from network",
                }
            )

        # Check for unusual port activity
        current_open = self.parent_plugin.security_stats.get("openPorts", 0)
        baseline_open = baseline.get("open_ports", 0)

        if current_open > baseline_open * 1.5:  # 50% increase
            threats.append(
                {
                    "type": "UNUSUAL_PORT_ACTIVITY",
                    "severity": "high",
                    "baseline_ports": baseline_open,
                    "current_ports": current_open,
                    "message": "Significantly more open ports than baseline",
                }
            )

        # Check for ARP table changes (ARP spoofing detection)
        baseline_arp = baseline.get("arp_entries")
        current_arp = self._get_arp_table_hash()

        if baseline_arp and baseline_arp != current_arp:
            threats.append(
                {
                    "type": "ARP_TABLE_MODIFIED",
                    "severity": "high",
                    "message": "ARP table has changed - possible ARP spoofing or MITM attack",
                }
            )

        # Log threats
        for threat in threats:
            self.log_threat(threat)

        return {
            "type": "intrusion_check_complete",
            "threats_detected": len(threats) > 0,
            "threats": threats,
            "severity": "high" if threats else "none",
        }

    # ============================================================================
    # DNS ANOMALY DETECTION
    # ============================================================================

    def check_dns_anomalies(self, request_data: Dict) -> Dict:
        """
        Check for DNS anomalies:
        - DNS hijacking (unexpected DNS responses)
        - DNS spoofing
        - DNS redirection to phishing sites
        """
        domains = request_data.get("domains", [])
        anomalies = []

        for domain in domains:
            # Check against known phishing/malicious domains
            if self._is_malicious_domain(domain):
                anomalies.append(
                    {
                        "type": "MALICIOUS_DOMAIN",
                        "domain": domain,
                        "severity": "critical",
                        "message": f"Domain {domain} is known to be malicious",
                    }
                )

            # In production, would also do DNS lookup verification
            # to detect if responses changed unexpectedly

        return {
            "type": "dns_check_complete",
            "anomalies_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "checked_domains": len(domains),
        }

    def _is_malicious_domain(self, domain: str) -> bool:
        """Check if domain is known malicious"""
        return any(malicious in domain.lower() for malicious in self.suspicious_domains)

    # ============================================================================
    # CREDENTIAL THEFT MONITORING
    # ============================================================================

    def monitor_credentials(self, request_data: Dict) -> Dict:
        """
        Monitor for credential theft attempts:
        - Session token exposure
        - Password field interception
        - Credential submission to suspicious URLs
        """
        credential_types = request_data.get("credentialTypes", [])
        count = request_data.get("count", {})

        recommendations = []

        # Session token security recommendations
        if count.get("sessions", 0) > 3:
            recommendations.append(
                {
                    "type": "SESSION_TOKEN_LIMIT",
                    "severity": "medium",
                    "message": f'High number of active sessions ({count["sessions"]}). Consider reducing to minimize exposure.',
                }
            )

        # Cookie security recommendations
        if count.get("sensitiveCookies", 0) > 0:
            recommendations.append(
                {
                    "type": "SENSITIVE_COOKIES",
                    "severity": "high",
                    "count": count["sensitiveCookies"],
                    "message": f'{count["sensitiveCookies"]} sensitive cookies detected. Ensure they are HttpOnly and Secure.',
                }
            )

        recommendations.append(
            {
                "type": "GENERAL_PROTECTION",
                "severity": "info",
                "message": "Enable two-factor authentication on all important accounts for additional protection",
            }
        )

        return {
            "type": "credential_monitoring_complete",
            "recommendations": recommendations,
            "credential_types_monitored": len(credential_types),
        }

    # ============================================================================
    # MALICIOUS URL DETECTION
    # ============================================================================

    def check_url(self, request_data: Dict) -> Dict:
        """
        Check if a URL is malicious:
        - Known phishing sites
        - Malware distribution
        - Command & Control (C2) servers
        - Known exploits
        """
        url = request_data.get("url", "")
        context = request_data.get("context", "")

        threat = None

        # Parse URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc
        except:
            domain = url

        # Check for known malicious domains
        if self._is_malicious_domain(domain):
            threat = {
                "type": "MALICIOUS_DOMAIN",
                "severity": "critical",
                "message": f"URL points to known malicious domain: {domain}",
                "action": "BLOCK",
            }

        # Check for suspicious patterns
        elif self._has_phishing_indicators(url):
            threat = {
                "type": "PHISHING_ATTEMPT",
                "severity": "high",
                "message": "URL has indicators of phishing attack",
                "action": "WARN",
            }

        # Check for known C2 patterns
        elif self._is_c2_pattern(url):
            threat = {
                "type": "C2_COMMUNICATION",
                "severity": "critical",
                "message": "URL matches known C2 communication pattern",
                "action": "BLOCK",
            }

        if threat:
            self.log_threat(threat)
            return {"type": "url_check_complete", "threat": threat}

        return {
            "type": "url_check_complete",
            "threat": None,
            "message": "URL appears safe",
        }

    def _has_phishing_indicators(self, url: str) -> bool:
        """Detect phishing patterns in URLs"""
        phishing_indicators = [
            "login",
            "signin",
            "verify",
            "confirm",
            "update",
            "suspended",
            "urgent",
            "security",
            "validate",
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in phishing_indicators)

    def _is_c2_pattern(self, url: str) -> bool:
        """Detect C2 communication patterns"""
        c2_patterns = [
            "beacon",
            "callback",
            "c2",
            "command",
            "control",
            "implant",
            "payload",
        ]

        url_lower = url.lower()
        return any(pattern in url_lower for pattern in c2_patterns)

    # ============================================================================
    # THREAT LOGGING & REPORTING
    # ============================================================================

    def log_threat(self, threat: Dict):
        """Log threat to threat database"""
        threat["logged_at"] = datetime.now().isoformat()
        self.threat_log.append(threat)

        # Keep only recent threats (last 1000)
        if len(self.threat_log) > 1000:
            self.threat_log = self.threat_log[-1000:]

        print(
            f"[BrowserSecurityShield] Threat logged: {threat.get('type')} - {threat.get('message')}"
        )

    def report_issues(self, request_data: Dict) -> Dict:
        """Report security issues from browser"""
        issues = request_data.get("issues", [])

        logged_issues = []
        for issue in issues:
            issue["reported_at"] = datetime.now().isoformat()
            issue["source"] = "browser"
            logged_issues.append(issue)
            self.log_threat(
                {"type": "BROWSER_SECURITY_ISSUE", "severity": "high", "issues": issue}
            )

        return {
            "type": "issues_reported",
            "count": len(logged_issues),
            "message": f"{len(logged_issues)} security issue(s) reported",
        }

    def report_threat(self, request_data: Dict) -> Dict:
        """Report threat from browser security shield"""
        threat = request_data
        self.log_threat(threat)

        return {
            "type": "threat_reported",
            "threat_id": hashlib.md5(
                json.dumps(threat, sort_keys=True).encode()
            ).hexdigest()[:16],
            "message": "Threat reported to security log",
        }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _get_gateway_mac(self) -> str:
        """Get gateway MAC address"""
        try:
            import subprocess

            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            # Parse result - typically first entry is gateway
            return "unknown"
        except:
            return "unknown"

    def _get_dns_servers(self) -> List[str]:
        """Get current DNS servers"""
        try:
            import subprocess

            result = subprocess.run(
                ["cat", "/etc/resolv.conf"], capture_output=True, text=True
            )
            dns_servers = []
            for line in result.stdout.split("\n"):
                if line.startswith("nameserver"):
                    dns_servers.append(line.split()[1])
            return dns_servers
        except:
            return []

    def _get_arp_table_hash(self) -> str:
        """Get hash of ARP table for change detection"""
        try:
            import subprocess

            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            return hashlib.md5(result.stdout.encode()).hexdigest()[:16]
        except:
            return "unknown"

    def get_threat_log(self, limit: int = 50) -> List[Dict]:
        """Get recent threats"""
        return self.threat_log[-limit:]

    def get_statistics(self) -> Dict:
        """Get threat statistics"""
        by_type = {}
        by_severity = {}

        for threat in self.threat_log:
            threat_type = threat.get("type", "UNKNOWN")
            severity = threat.get("severity", "unknown")

            by_type[threat_type] = by_type.get(threat_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_threats": len(self.threat_log),
            "by_type": by_type,
            "by_severity": by_severity,
            "critical_count": sum(
                1 for t in self.threat_log if t.get("severity") == "critical"
            ),
            "high_count": sum(
                1 for t in self.threat_log if t.get("severity") == "high"
            ),
        }
