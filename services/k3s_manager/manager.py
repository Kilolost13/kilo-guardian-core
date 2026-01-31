"""
K3s Cluster Manager for Kilo
Provides skills to manage the HP k3s cluster from Beelink
"""
import subprocess
import json
from typing import Dict, List, Optional

class K3sManager:
    """Manages HP k3s cluster remotely from Beelink"""

    def __init__(self):
        self.kubeconfig = "/home/brain_ai/.kube/hp-k3s.yaml"
        self.namespace = "kilo-guardian"
        self.hp_host = "kilo@192.168.68.56"

    def _kubectl(self, args: List[str], capture_output=True) -> subprocess.CompletedProcess:
        """Execute kubectl command with proper kubeconfig"""
        cmd = ["kubectl", "--kubeconfig", self.kubeconfig] + args
        return subprocess.run(cmd, capture_output=capture_output, text=True)

    def get_cluster_status(self) -> Dict:
        """Get overall cluster health and status"""
        result = self._kubectl(["get", "nodes", "-o", "json"])
        if result.returncode != 0:
            return {"error": result.stderr, "status": "unreachable"}

        nodes = json.loads(result.stdout)
        pods_result = self._kubectl(["get", "pods", "-n", self.namespace, "-o", "json"])
        pods = json.loads(pods_result.stdout) if pods_result.returncode == 0 else {"items": []}

        running_pods = [p for p in pods.get("items", []) if p["status"]["phase"] == "Running"]
        total_pods = len(pods.get("items", []))

        return {
            "status": "healthy",
            "nodes": len(nodes.get("items", [])),
            "pods": {
                "running": len(running_pods),
                "total": total_pods
            },
            "namespace": self.namespace
        }

    def list_services(self) -> List[Dict]:
        """List all running services in kilo-guardian namespace"""
        result = self._kubectl(["get", "deployments", "-n", self.namespace, "-o", "json"])
        if result.returncode != 0:
            return []

        deployments = json.loads(result.stdout)
        services = []

        for deploy in deployments.get("items", []):
            name = deploy["metadata"]["name"]
            spec = deploy["spec"]
            status = deploy["status"]

            services.append({
                "name": name,
                "replicas": {
                    "desired": spec.get("replicas", 0),
                    "ready": status.get("readyReplicas", 0),
                    "available": status.get("availableReplicas", 0)
                },
                "status": "running" if status.get("readyReplicas", 0) > 0 else "down"
            })

        return services

    def scale_service(self, service_name: str, replicas: int) -> Dict:
        """Scale a service up or down"""
        result = self._kubectl([
            "scale", "deployment", service_name,
            "--replicas", str(replicas),
            "-n", self.namespace
        ])

        return {
            "service": service_name,
            "replicas": replicas,
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }

    def restart_service(self, service_name: str) -> Dict:
        """Restart a service (rolling restart)"""
        result = self._kubectl([
            "rollout", "restart", f"deployment/{service_name}",
            "-n", self.namespace
        ])

        return {
            "service": service_name,
            "action": "restart",
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }

    def get_service_logs(self, service_name: str, lines: int = 50) -> str:
        """Get recent logs from a service"""
        result = self._kubectl([
            "logs", "-n", self.namespace,
            "-l", f"app={service_name}",
            "--tail", str(lines)
        ])

        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

    def get_pod_status(self, service_name: str) -> Dict:
        """Get detailed status of pods for a service"""
        result = self._kubectl([
            "get", "pods", "-n", self.namespace,
            "-l", f"app={service_name}",
            "-o", "json"
        ])

        if result.returncode != 0:
            return {"error": result.stderr}

        pods = json.loads(result.stdout)
        pod_statuses = []

        for pod in pods.get("items", []):
            pod_statuses.append({
                "name": pod["metadata"]["name"],
                "phase": pod["status"]["phase"],
                "ready": all(c["ready"] for c in pod["status"].get("containerStatuses", [])),
                "restarts": sum(c["restartCount"] for c in pod["status"].get("containerStatuses", []))
            })

        return {
            "service": service_name,
            "pods": pod_statuses
        }

    def deploy_manifest(self, manifest_path: str) -> Dict:
        """Deploy a kubernetes manifest file"""
        result = self._kubectl(["apply", "-f", manifest_path])

        return {
            "manifest": manifest_path,
            "success": result.returncode == 0,
            "output": result.stdout or result.stderr
        }

    def get_service_endpoints(self) -> List[Dict]:
        """Get all accessible endpoints (NodePorts, LoadBalancers)"""
        result = self._kubectl(["get", "svc", "-n", self.namespace, "-o", "json"])

        if result.returncode != 0:
            return []

        services = json.loads(result.stdout)
        endpoints = []

        for svc in services.get("items", []):
            name = svc["metadata"]["name"]
            spec = svc["spec"]
            svc_type = spec.get("type", "ClusterIP")

            if svc_type == "NodePort":
                for port in spec.get("ports", []):
                    endpoints.append({
                        "service": name,
                        "type": "NodePort",
                        "url": f"http://192.168.68.56:{port['nodePort']}",
                        "port": port["nodePort"],
                        "targetPort": port.get("targetPort")
                    })
            elif svc_type == "LoadBalancer":
                lb_ip = spec.get("loadBalancerIP") or "192.168.68.56"
                for port in spec.get("ports", []):
                    endpoints.append({
                        "service": name,
                        "type": "LoadBalancer",
                        "url": f"http://{lb_ip}:{port['port']}",
                        "port": port["port"]
                    })

        return endpoints

    def exec_in_pod(self, service_name: str, command: str) -> str:
        """Execute a command in a pod"""
        # Get first pod for the service
        result = self._kubectl([
            "get", "pods", "-n", self.namespace,
            "-l", f"app={service_name}",
            "-o", "jsonpath={.items[0].metadata.name}"
        ])

        if result.returncode != 0 or not result.stdout:
            return f"Error: No pods found for {service_name}"

        pod_name = result.stdout.strip()

        # Execute command in pod
        exec_result = self._kubectl([
            "exec", "-n", self.namespace, pod_name,
            "--", "sh", "-c", command
        ])

        return exec_result.stdout if exec_result.returncode == 0 else f"Error: {exec_result.stderr}"


# Singleton instance
k3s_manager = K3sManager()
