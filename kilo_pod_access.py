#!/usr/bin/env python3
"""
Kilo Pod Access Module - REAL data access capabilities
Allows Kilo to actually interact with pod data, not just metadata
"""

import subprocess
import os
import json
from typing import Optional, Dict, Any, List


KUBECONFIG = os.path.expanduser("~/.kube/hp-k3s-config")


class KiloPodAccess:
    """Provides real access to pod data and operations"""

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

    def get_pod_logs(self, pod_name: str, namespace: str = "default",
                     tail: int = 100, container: Optional[str] = None) -> str:
        """
        Get logs from a pod

        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            tail: Number of lines to retrieve
            container: Specific container name (if pod has multiple)

        Returns:
            Log contents as string
        """
        args = ["logs", pod_name, "-n", namespace, f"--tail={tail}"]

        if container:
            args.extend(["-c", container])

        stdout, stderr, rc = self.run_kubectl(args)

        if rc == 0:
            return stdout
        else:
            return f"Error getting logs: {stderr}"

    def exec_in_pod(self, pod_name: str, command: List[str],
                   namespace: str = "default", container: Optional[str] = None) -> str:
        """
        Execute a command inside a pod

        Args:
            pod_name: Name of the pod
            command: Command to execute (list of strings)
            namespace: Kubernetes namespace
            container: Specific container (if pod has multiple)

        Returns:
            Command output as string
        """
        args = ["exec", pod_name, "-n", namespace, "--"]

        if container:
            args.extend(["-c", container])

        args.extend(command)

        stdout, stderr, rc = self.run_kubectl(args)

        if rc == 0:
            return stdout
        else:
            return f"Error executing command: {stderr}"

    def query_database_in_pod(self, pod_name: str, db_query: str,
                             namespace: str = "default",
                             db_type: str = "postgres") -> str:
        """
        Execute a database query inside a pod

        Args:
            pod_name: Name of the database pod
            db_query: SQL query to execute
            namespace: Kubernetes namespace
            db_type: Database type (postgres, mysql, mongo)

        Returns:
            Query results as string
        """
        if db_type == "postgres":
            command = ["psql", "-U", "postgres", "-c", db_query]
        elif db_type == "mysql":
            command = ["mysql", "-e", db_query]
        elif db_type == "mongo":
            command = ["mongo", "--eval", db_query]
        else:
            return f"Unsupported database type: {db_type}"

        return self.exec_in_pod(pod_name, command, namespace)

    def read_file_from_pod(self, pod_name: str, file_path: str,
                          namespace: str = "default") -> str:
        """
        Read a file from inside a pod

        Args:
            pod_name: Name of the pod
            file_path: Path to file inside pod
            namespace: Kubernetes namespace

        Returns:
            File contents as string
        """
        command = ["cat", file_path]
        return self.exec_in_pod(pod_name, command, namespace)

    def list_files_in_pod(self, pod_name: str, directory: str = "/",
                         namespace: str = "default") -> str:
        """
        List files in a directory inside a pod

        Args:
            pod_name: Name of the pod
            directory: Directory to list
            namespace: Kubernetes namespace

        Returns:
            Directory listing as string
        """
        command = ["ls", "-la", directory]
        return self.exec_in_pod(pod_name, command, namespace)

    def get_pod_environment(self, pod_name: str, namespace: str = "default") -> str:
        """
        Get environment variables from a pod

        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace

        Returns:
            Environment variables as string
        """
        command = ["env"]
        return self.exec_in_pod(pod_name, command, namespace)

    def call_pod_api(self, pod_name: str, endpoint: str,
                    port: int = 8080, namespace: str = "default") -> str:
        """
        Call an API endpoint inside a pod using port-forward

        Args:
            pod_name: Name of the pod
            endpoint: API endpoint to call
            port: Port number
            namespace: Kubernetes namespace

        Returns:
            API response as string
        """
        # This is more complex - would need port-forward + curl
        # Simplified version using kubectl exec curl
        command = ["curl", f"http://localhost:{port}{endpoint}"]
        return self.exec_in_pod(pod_name, command, namespace)

    def get_finance_data(self, pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        EXAMPLE: Get financial data from finance pod

        This is a template - adapt based on your actual finance pod structure

        Args:
            pod_name: Name of the finance pod
            namespace: Kubernetes namespace

        Returns:
            Dictionary with financial data
        """
        result = {
            "status": "unknown",
            "data": None,
            "error": None
        }

        # Try to get data from API endpoint
        api_response = self.call_pod_api(pod_name, "/api/finances", namespace=namespace)

        if "Error" not in api_response:
            try:
                result["data"] = json.loads(api_response)
                result["status"] = "success"
            except json.JSONDecodeError:
                result["error"] = "Failed to parse API response"
                result["status"] = "error"
        else:
            result["error"] = api_response
            result["status"] = "error"

        return result


# Singleton instance
_pod_access_instance: Optional[KiloPodAccess] = None


def get_pod_access() -> KiloPodAccess:
    """Get the global pod access instance"""
    global _pod_access_instance
    if _pod_access_instance is None:
        _pod_access_instance = KiloPodAccess()
    return _pod_access_instance


# Example usage
if __name__ == "__main__":
    access = get_pod_access()

    print("Testing pod access capabilities...")
    print("\n1. Get pod logs:")
    # Example: get logs from a pod
    # logs = access.get_pod_logs("finance-api-xxxx")
    # print(logs)

    print("\n2. Execute command in pod:")
    # Example: run command in pod
    # result = access.exec_in_pod("finance-api-xxxx", ["ls", "-la", "/app"])
    # print(result)

    print("\n3. Read file from pod:")
    # Example: read config file
    # config = access.read_file_from_pod("finance-api-xxxx", "/app/config.json")
    # print(config)

    print("\nPod access module loaded successfully!")
