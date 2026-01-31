#!/usr/bin/env python3
"""
Kilo Auto Data Fetch - AUTONOMOUS pod data access
Automatically discovers and fetches ALL available data from k3s pods
No bullshit questions - just GET THE DATA
"""

import subprocess
import os
import json
import re
from typing import Dict, List, Any

KUBECONFIG = os.path.expanduser("~/.kube/hp-k3s-config")


class KiloAutoDataFetch:
    """Autonomously fetch ALL data from k3s cluster"""

    def __init__(self):
        os.environ['KUBECONFIG'] = KUBECONFIG

    def run_kubectl(self, args: List[str]) -> tuple:
        """Run kubectl command"""
        try:
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def get_all_pods(self, namespace: str = "default") -> List[Dict[str, str]]:
        """Get all running pods with details"""
        stdout, _, rc = self.run_kubectl(["get", "pods", "-n", namespace, "-o", "json"])

        if rc != 0:
            return []

        try:
            data = json.loads(stdout)
            pods = []
            for item in data.get("items", []):
                pod = {
                    "name": item["metadata"]["name"],
                    "status": item["status"]["phase"],
                    "containers": [c["name"] for c in item["spec"]["containers"]],
                    "namespace": namespace
                }
                pods.append(pod)
            return pods
        except:
            return []

    def auto_fetch_pod_data(self, pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Automatically fetch ALL available data from a pod
        Tries multiple methods and aggregates everything
        """
        data = {
            "pod_name": pod_name,
            "namespace": namespace,
            "logs": None,
            "environment": None,
            "files": {},
            "database_data": None,
            "api_responses": {},
            "process_list": None,
            "disk_usage": None,
            "errors": []
        }

        # 1. GET LOGS (last 200 lines)
        try:
            stdout, _, rc = self.run_kubectl(["logs", pod_name, "-n", namespace, "--tail=200"])
            if rc == 0:
                data["logs"] = stdout
        except Exception as e:
            data["errors"].append(f"Failed to get logs: {e}")

        # 2. GET ENVIRONMENT VARIABLES
        try:
            stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--", "env"])
            if rc == 0:
                data["environment"] = stdout
        except Exception as e:
            data["errors"].append(f"Failed to get environment: {e}")

        # 3. GET PROCESS LIST
        try:
            stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--", "ps", "aux"])
            if rc == 0:
                data["process_list"] = stdout
        except Exception as e:
            data["errors"].append(f"Failed to get processes: {e}")

        # 4. TRY TO FIND AND READ DATA FILES
        common_data_paths = [
            "/app/data",
            "/data",
            "/var/lib/app",
            "/app",
            "/usr/src/app",
            "/opt/app"
        ]

        for path in common_data_paths:
            try:
                stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--", "ls", "-la", path])
                if rc == 0:
                    data["files"][path] = stdout

                    # Try to read JSON/CSV files
                    for line in stdout.split('\n'):
                        if '.json' in line or '.csv' in line or '.txt' in line:
                            filename = line.split()[-1]
                            file_path = f"{path}/{filename}"
                            try:
                                file_stdout, _, file_rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--", "cat", file_path])
                                if file_rc == 0:
                                    data["files"][file_path] = file_stdout
                            except:
                                pass
            except:
                pass

        # 5. TRY COMMON API ENDPOINTS (if it's a web service)
        common_endpoints = [
            "/health",
            "/api/data",
            "/api/status",
            "/data",
            "/metrics"
        ]

        for endpoint in common_endpoints:
            try:
                # Try curl on localhost
                stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--",
                                                 "curl", "-s", f"http://localhost:8080{endpoint}"])
                if rc == 0 and stdout and "404" not in stdout:
                    data["api_responses"][endpoint] = stdout
            except:
                pass

        # 6. TRY TO DETECT AND QUERY DATABASE
        # Check if common database processes are running
        if data["process_list"]:
            if "postgres" in data["process_list"].lower():
                try:
                    # Try to query postgres
                    stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--",
                                                     "psql", "-U", "postgres", "-c", "\\dt"])
                    if rc == 0:
                        data["database_data"] = {"type": "postgres", "tables": stdout}

                        # Try to get row counts
                        stdout2, _, rc2 = self.run_kubectl(["exec", pod_name, "-n", namespace, "--",
                                                           "psql", "-U", "postgres", "-c",
                                                           "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"])
                        if rc2 == 0:
                            data["database_data"]["schema"] = stdout2
                except Exception as e:
                    data["errors"].append(f"Failed to query postgres: {e}")

            elif "mysql" in data["process_list"].lower():
                try:
                    stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--",
                                                     "mysql", "-e", "SHOW TABLES"])
                    if rc == 0:
                        data["database_data"] = {"type": "mysql", "tables": stdout}
                except Exception as e:
                    data["errors"].append(f"Failed to query mysql: {e}")

            elif "mongo" in data["process_list"].lower():
                try:
                    stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--",
                                                     "mongo", "--eval", "db.getCollectionNames()"])
                    if rc == 0:
                        data["database_data"] = {"type": "mongo", "collections": stdout}
                except Exception as e:
                    data["errors"].append(f"Failed to query mongo: {e}")

        # 7. GET DISK USAGE
        try:
            stdout, _, rc = self.run_kubectl(["exec", pod_name, "-n", namespace, "--", "df", "-h"])
            if rc == 0:
                data["disk_usage"] = stdout
        except:
            pass

        return data

    def fetch_all_cluster_data(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Fetch ALL data from ALL running pods in the cluster
        Returns comprehensive cluster data snapshot
        """
        result = {
            "pods": [],
            "total_pods": 0,
            "running_pods": 0,
            "data_by_pod": {}
        }

        # Get all pods
        pods = self.get_all_pods(namespace)
        result["total_pods"] = len(pods)

        for pod in pods:
            if pod["status"] == "Running":
                result["running_pods"] += 1
                result["pods"].append(pod["name"])

                # Fetch all data from this pod
                print(f"Fetching data from {pod['name']}...")
                pod_data = self.auto_fetch_pod_data(pod["name"], namespace)
                result["data_by_pod"][pod["name"]] = pod_data

        return result

    def get_finance_specific_data(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Smart finance data extraction
        Finds finance-related pods and extracts relevant data
        """
        result = {
            "finance_pods": [],
            "finance_data": {}
        }

        # Get all pods
        pods = self.get_all_pods(namespace)

        # Find finance-related pods
        finance_keywords = ["finance", "money", "account", "transaction", "payment", "billing"]

        for pod in pods:
            pod_name_lower = pod["name"].lower()
            if any(keyword in pod_name_lower for keyword in finance_keywords):
                result["finance_pods"].append(pod["name"])

                if pod["status"] == "Running":
                    # Get comprehensive data
                    pod_data = self.auto_fetch_pod_data(pod["name"], namespace)
                    result["finance_data"][pod["name"]] = pod_data

        return result

    def format_data_for_ai(self, cluster_data: Dict[str, Any]) -> str:
        """
        Format the fetched data into a readable summary for AI
        """
        lines = []
        lines.append("=== COMPREHENSIVE CLUSTER DATA ===\n")

        lines.append(f"Total Pods: {cluster_data['total_pods']}")
        lines.append(f"Running Pods: {cluster_data['running_pods']}")
        lines.append(f"Data fetched from: {', '.join(cluster_data['pods'])}\n")

        for pod_name, pod_data in cluster_data.get("data_by_pod", {}).items():
            lines.append(f"\n{'='*60}")
            lines.append(f"POD: {pod_name}")
            lines.append('='*60)

            if pod_data.get("logs"):
                lines.append(f"\n--- LOGS (last 200 lines) ---")
                lines.append(pod_data["logs"][:2000])  # Limit to 2000 chars

            if pod_data.get("environment"):
                lines.append(f"\n--- ENVIRONMENT VARIABLES ---")
                lines.append(pod_data["environment"][:1000])

            if pod_data.get("database_data"):
                lines.append(f"\n--- DATABASE ({pod_data['database_data'].get('type')}) ---")
                lines.append(str(pod_data["database_data"])[:1000])

            if pod_data.get("api_responses"):
                lines.append(f"\n--- API RESPONSES ---")
                for endpoint, response in pod_data["api_responses"].items():
                    lines.append(f"{endpoint}: {response[:500]}")

            if pod_data.get("files"):
                lines.append(f"\n--- FILES ---")
                for path, content in list(pod_data["files"].items())[:5]:  # Limit files
                    lines.append(f"{path}:")
                    if isinstance(content, str):
                        lines.append(content[:500])

        return "\n".join(lines)


# Singleton
_auto_fetch_instance = None

def get_auto_fetch() -> KiloAutoDataFetch:
    """Get singleton instance"""
    global _auto_fetch_instance
    if _auto_fetch_instance is None:
        _auto_fetch_instance = KiloAutoDataFetch()
    return _auto_fetch_instance


if __name__ == "__main__":
    print("Testing auto data fetch...")
    fetcher = get_auto_fetch()

    print("\n1. Getting all pods...")
    pods = fetcher.get_all_pods()
    print(f"Found {len(pods)} pods")
    for pod in pods:
        print(f"  - {pod['name']} ({pod['status']})")

    print("\n2. Testing finance-specific data fetch...")
    finance_data = fetcher.get_finance_specific_data()
    print(f"Found {len(finance_data['finance_pods'])} finance pods")
    print(json.dumps(finance_data, indent=2, default=str))
