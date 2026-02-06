"""
K3s Controller -- typed async wrapper around kubectl.
All operations target the kilo-guardian namespace by default.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger("K3sController")

NAMESPACE = "kilo-guardian"
KUBECONFIG = os.path.expanduser("~/.kube/config")


def _env() -> dict:
    """OS env with KUBECONFIG set."""
    env = os.environ.copy()
    env["KUBECONFIG"] = KUBECONFIG
    return env


async def _kubectl(args: List[str], timeout: int = 30) -> Dict:
    """Run kubectl, return {stdout, stderr, returncode}."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "kubectl", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_env(),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return {
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "returncode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"stdout": "", "stderr": f"kubectl timed out after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


# ---------------------------------------------------------------
# Pod operations
# ---------------------------------------------------------------
async def get_pods(namespace: str = NAMESPACE) -> Dict:
    """List pods with parsed status."""
    res = await _kubectl(["get", "pods", "-n", namespace, "-o", "json"])
    if res["returncode"] != 0:
        return {"error": res["stderr"]}
    try:
        data = json.loads(res["stdout"])
        pods = []
        for item in data.get("items", []):
            statuses = item["status"].get("containerStatuses", [])
            conditions = item["status"].get("conditions", [])
            pods.append({
                "name":     item["metadata"]["name"],
                "phase":    item["status"].get("phase", "Unknown"),
                "ready":    any(
                    c.get("type") == "Ready" and c.get("status") == "True"
                    for c in conditions
                ),
                "restarts": sum(cs.get("restartCount", 0) for cs in statuses),
                "image":    statuses[0]["image"] if statuses else "",
            })
        return {"pods": pods, "count": len(pods)}
    except json.JSONDecodeError:
        return {"error": "JSON decode failed", "raw": res["stdout"][:500]}


async def get_pod_logs(
    pod_name: str,
    namespace: str = NAMESPACE,
    tail: int = 50,
    container: Optional[str] = None,
) -> Dict:
    args = ["logs", "-n", namespace, pod_name, f"--tail={tail}"]
    if container:
        args.extend(["-c", container])
    res = await _kubectl(args, timeout=15)
    return {
        "logs": res["stdout"],
        "error": res["stderr"] if res["returncode"] != 0 else None,
    }


async def exec_in_pod(
    pod_name: str,
    command: List[str],
    namespace: str = NAMESPACE,
) -> Dict:
    res = await _kubectl(
        ["exec", "-n", namespace, pod_name, "--"] + command, timeout=30
    )
    return {
        "stdout":     res["stdout"],
        "stderr":     res["stderr"],
        "returncode": res["returncode"],
    }


async def restart_pod(pod_name: str, namespace: str = NAMESPACE) -> Dict:
    """Delete pod -- Deployment controller recreates it."""
    res = await _kubectl(["delete", "pod", "-n", namespace, pod_name])
    return {
        "status":  "ok" if res["returncode"] == 0 else "error",
        "message": res["stdout"] or res["stderr"],
    }


# ---------------------------------------------------------------
# Cluster-info helpers
# ---------------------------------------------------------------
async def get_services(namespace: str = NAMESPACE) -> Dict:
    res = await _kubectl(["get", "svc", "-n", namespace, "-o", "wide"])
    return {"services": res["stdout"]}


async def get_events(namespace: str = NAMESPACE) -> Dict:
    """List events parsed from JSON."""
    res = await _kubectl(
        ["get", "events", "-n", namespace, "-o", "json"]
    )
    if res["returncode"] != 0:
        return {"error": res["stderr"]}
    try:
        data = json.loads(res["stdout"])
        items = data.get("items", [])
        
        # Sort by lastTimestamp descending, handle None values
        items.sort(key=lambda x: x.get("lastTimestamp") or "", reverse=True)
        
        events = []
        for item in items:
            events.append({
                "type":          item.get("type"),
                "reason":        item.get("reason"),
                "message":       item.get("message"),
                "lastTimestamp": item.get("lastTimestamp"),
                "object":        f"{item.get('involvedObject', {}).get('kind')}/{item.get('involvedObject', {}).get('name')}"
            })
        return {"events": events, "count": len(events)}
    except Exception as e:
        return {"error": f"Failed to parse events: {str(e)}", "raw": res["stdout"][:500]}


async def scale_deployment(
    name: str, replicas: int, namespace: str = NAMESPACE
) -> Dict:
    res = await _kubectl(
        ["scale", "deployment", name, f"--replicas={replicas}", "-n", namespace]
    )
    return {
        "status":  "ok" if res["returncode"] == 0 else "error",
        "message": res["stdout"] or res["stderr"],
    }


async def get_resource_usage(namespace: str = NAMESPACE) -> Dict:
    res = await _kubectl(["top", "pods", "-n", namespace], timeout=15)
    return {
        "usage": res["stdout"],
        "error": res["stderr"] if res["returncode"] != 0 else None,
    }
