"""
Unified Service Registry for Kilo.
Maps all services across k3s microservices and guardian-unified capabilities.
Provides async health checking and capability-based discovery.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger("ServiceRegistry")


@dataclass
class ServiceInfo:
    name: str
    url: str
    port: int
    layer: str          # "k3s" | "guardian" | "host"
    capabilities: List[str] = field(default_factory=list)
    healthy: bool = True
    last_checked: float = 0
    health_endpoint: str = "/health"


class ServiceRegistry:
    """
    Single source of truth for every service in the Kilo ecosystem.
    k3s services are populated from ConfigMap-style env vars (or defaults).
    Guardian services are logical markers -- they have no standalone HTTP endpoint;
    commands targeting them are routed through Gemini or the local reasoning engine.
    """

    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self._init_k3s()
        self._init_guardian()

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def _init_k3s(self):
        defs = {
            "ai-brain":     ("http://kilo-ai-brain:9004",     9004,
                             ["orchestration", "sedentary", "meds_upload", "habit_events", "memory"]),
            "gateway":      ("http://kilo-gateway:8000",      8000,
                             ["routing", "proxy", "admin"]),
            "reminder":     ("http://kilo-reminder:9002",     9002,
                             ["reminders", "schedule", "upcoming"]),
            "habits":       ("http://kilo-habits:9000",       9000,
                             ["habits", "tracking", "completion", "streak"]),
            "meds":         ("http://kilo-meds:9000",         9000,
                             ["medications", "adherence", "dosage", "pill"]),
            "financial":    ("http://kilo-financial:9005",    9005,
                             ["finance", "budget", "spending", "bills", "csv", "bank", "income", "money tracking", "financial overview"]),
            "library":      ("http://kilo-library:9006",      9006,
                             ["knowledge", "library", "reference", "search", "fact", "information lookup", "find facts"]),
            "cam":          ("http://kilo-cam:9007",          9007,
                             ["camera", "monitoring", "face", "posture", "activity detection", "what am I doing"]),
            "voice":        ("http://kilo-voice:9008",        9008,
                             ["voice", "speech", "stt", "tts", "text to speech", "speech to text", "audio conversion"]),
            "ml-engine":    ("http://kilo-ml-engine:9009",    9009,
                             ["ml", "prediction", "analytics", "pattern", "trend"]),
            "socketio":     ("http://kilo-socketio:9010",     9010,
                             ["realtime", "websocket", "push"]),
            "usb-transfer": ("http://kilo-usb-transfer:9010", 9010,
                             ["usb", "file_transfer", "sync", "external drive", "copy files"]),
            "marketing":    ("http://kilo-marketing:80",      80,
                             ["marketing", "website", "landing"]),  # health_ep set below
            "guardian":     ("http://kilo-guardian:8001",     8001,
                             ["guardian", "plugin", "reasoning", "persona", "security", "drone", "mesh"]),
        }
        for name, (default_url, port, caps) in defs.items():
            url = os.getenv(f"{name.upper().replace('-', '_')}_URL", default_url)
            self.services[name] = ServiceInfo(
                name=name, url=url, port=port, layer="k3s", capabilities=caps
            )


        # Some services don't have /health -- use / instead
        for name in ("marketing",):
            if name in self.services:
                self.services[name].health_endpoint = "/"

    def _init_guardian(self):
        """
        Guardian-unified logical services.  These are now split into individual
        dedicated pods for modularity.
        """
        caps_map = {
            "reasoning-engine":  ("http://kilo-reasoning-engine:8001", ["reasoning", "routing", "nlp", "embedding", "intent"]),
            "plugin-manager":    ("http://kilo-guardian:8001",         ["plugins", "sandbox", "extensions", "dynamic"]),
            "user-context":      ("http://kilo-guardian:8001",         ["user_profile", "preferences", "history", "learning"]),
            "persona-manager":   ("http://kilo-guardian:8001",         ["persona", "home", "pro", "business", "style"]),
            "unified-knowledge": ("http://kilo-guardian:8001",         ["knowledge", "facts"]),
            "security-monitor":  ("http://kilo-security-monitor:8001", ["security", "intrusion", "honeypot", "audit"]),
            "drone-control":     ("http://kilo-drone-control:8001",    ["drone", "flight", "video", "fpv", "geofence"]),
            "meshtastic":        ("http://kilo-meshtastic:8001",       ["mesh", "tracking", "radio", "lora"]),
            "watchdog":          ("http://kilo-guardian:8001",         ["process", "auto_restart", "supervisor"]),
        }
        for name, (url, caps) in caps_map.items():
            self.services[name] = ServiceInfo(
                name=name, url=url, port=8001, layer="k3s", capabilities=caps
            )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def find_by_capability(self, capability: str) -> List[ServiceInfo]:
        return [s for s in self.services.values() if capability in s.capabilities]

    def find_best_match(self, capabilities: List[str]) -> Optional[ServiceInfo]:
        best, best_score = None, 0
        for svc in self.services.values():
            score = len(set(capabilities) & set(svc.capabilities))
            if score > best_score:
                best, best_score = svc, score
        return best

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------
    async def health_check(self, name: str, timeout: float = 5.0) -> bool:
        svc = self.services.get(name)
        if not svc or svc.layer != "k3s":
            return True          # guardian services are always "local-healthy"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{svc.url}{svc.health_endpoint}")
                svc.healthy = resp.status_code == 200
        except Exception:
            svc.healthy = False
        svc.last_checked = time.time()
        return svc.healthy

    async def health_check_all(self) -> Dict[str, bool]:
        import asyncio
        k3s_names = [n for n, s in self.services.items() if s.layer == "k3s"]
        results = await asyncio.gather(
            *(self.health_check(n) for n in k3s_names),
            return_exceptions=True
        )
        return {
            name: (r if isinstance(r, bool) else False)
            for name, r in zip(k3s_names, results)
        }

    # ------------------------------------------------------------------
    # Status dump
    # ------------------------------------------------------------------
    def get_status(self) -> Dict:
        return {
            name: {
                "layer": s.layer,
                "url": s.url,
                "port": s.port,
                "healthy": s.healthy,
                "capabilities": s.capabilities,
                "last_checked": s.last_checked,
            }
            for name, s in self.services.items()
        }


# ---------------------------------------------------------------------------
# Host-mode ClusterIP resolver
# ---------------------------------------------------------------------------
async def resolve_cluster_ips(registry: "ServiceRegistry"):
    """
    When the agent runs on the k3s host (not inside a pod), DNS names like
    'kilo-reminder' don't resolve.  ClusterIPs DO work from the host on k3s.
    This function runs kubectl once at startup and patches the registry URLs
    to use ClusterIPs instead of DNS names.
    """
    import asyncio, json, os

    env = os.environ.copy()
    env["KUBECONFIG"] = os.path.expanduser("~/.kube/config")

    try:
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "get", "svc", "-n", "kilo-guardian", "-o", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        data = json.loads(stdout.decode())

        # Build name -> ClusterIP map from kubectl output
        # Service names in k3s are like "kilo-reminder" -- strip "kilo-" prefix
        # to match our registry keys
        svc_map: Dict[str, str] = {}
        for item in data.get("items", []):
            k8s_name = item["metadata"]["name"]            # e.g. "kilo-reminder"
            cluster_ip = item.get("status", {}).get("loadBalancer", {})
            cluster_ip = item["spec"].get("clusterIP", "")
            ports = item["spec"].get("ports", [])
            port = ports[0]["port"] if ports else 80

            # Strip "kilo-" prefix and convert hyphens to underscores
            reg_key = k8s_name.replace("kilo-", "", 1).replace("-", "_")
            if reg_key in registry.services and registry.services[reg_key].layer == "k3s":
                new_url = f"http://{cluster_ip}:{port}"
                registry.services[reg_key].url = new_url
                logger.info("Resolved %s -> %s", reg_key, new_url)

    except Exception as e:
        logger.warning("ClusterIP resolution failed: %s -- falling back to DNS names", e)
