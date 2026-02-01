#!/usr/bin/env python3
"""
Simplified Kilo Agent - K3s Monitoring
Works via SSH to HP server since direct kubectl has connectivity issues
"""

import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List

class SimpleKiloAgent:
    """Simple K3s monitoring agent that works via SSH"""

    def __init__(self, hp_host="kilo@192.168.68.56"):
        self.hp_host = hp_host
        self.monitoring = False
        self.last_status = {}

    def ssh_kubectl(self, command: str) -> str:
        """Run kubectl command on HP via SSH"""
        full_cmd = f"ssh {self.hp_host} 'sudo kubectl {command}'"
        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            return f"Error: {e}"

    def get_pods(self) -> List[Dict]:
        """Get all pods in kilo-guardian namespace"""
        output = self.ssh_kubectl("get pods -n kilo-guardian -o json")
        try:
            data = json.loads(output)
            return data.get('items', [])
        except:
            return []

    def get_pod_status(self) -> Dict[str, Dict]:
        """Get status of all Kilo pods"""
        pods = self.get_pods()
        status = {}

        for pod in pods:
            name = pod['metadata']['name']
            spec = pod['status']

            status[name] = {
                'phase': spec.get('phase', 'Unknown'),
                'ready': self._is_pod_ready(spec),
                'restarts': self._get_restart_count(spec),
                'age': self._get_pod_age(pod['metadata'].get('creationTimestamp', ''))
            }

        return status

    def _is_pod_ready(self, status: Dict) -> bool:
        """Check if pod is ready"""
        conditions = status.get('conditions', [])
        for cond in conditions:
            if cond.get('type') == 'Ready':
                return cond.get('status') == 'True'
        return False

    def _get_restart_count(self, status: Dict) -> int:
        """Get total restart count for pod"""
        containers = status.get('containerStatuses', [])
        return sum(c.get('restartCount', 0) for c in containers)

    def _get_pod_age(self, timestamp: str) -> str:
        """Calculate pod age from timestamp"""
        if not timestamp:
            return "Unknown"
        # Simplified - just return timestamp for now
        return timestamp[:10]

    def detect_issues(self, current_status: Dict) -> List[str]:
        """Detect issues by comparing with last status"""
        issues = []

        for pod_name, status in current_status.items():
            # Check if pod is not running
            if status['phase'] != 'Running':
                issues.append(f"🔴 {pod_name}: Not running (phase={status['phase']})")

            # Check if pod is not ready
            if not status['ready'] and status['phase'] == 'Running':
                issues.append(f"🟡 {pod_name}: Running but not ready")

            # Check for high restart counts
            if status['restarts'] > 5:
                issues.append(f"⚠️  {pod_name}: High restart count ({status['restarts']})")

            # Check if restart count increased
            if pod_name in self.last_status:
                old_restarts = self.last_status[pod_name]['restarts']
                new_restarts = status['restarts']
                if new_restarts > old_restarts:
                    issues.append(f"🔄 {pod_name}: Restarted ({old_restarts} → {new_restarts})")

        return issues

    def print_status(self, status: Dict):
        """Print current status in readable format"""
        print(f"\n{'='*80}")
        print(f"Kilo Guardian Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # Count by status
        running = sum(1 for s in status.values() if s['phase'] == 'Running' and s['ready'])
        total = len(status)

        print(f"📊 Overview: {running}/{total} pods healthy\n")

        # List all pods
        for pod_name, pod_status in sorted(status.items()):
            phase = pod_status['phase']
            ready = "✅" if pod_status['ready'] else "❌"
            restarts = pod_status['restarts']

            # Shorten pod name for display
            short_name = pod_name.split('-')[1] if '-' in pod_name else pod_name

            print(f"{ready} {short_name:15} | {phase:10} | Restarts: {restarts:2}")

    def monitor_once(self):
        """Run one monitoring cycle"""
        print("\n🔍 Checking K3s cluster...")

        # Get current status
        current_status = self.get_pod_status()

        if not current_status:
            print("❌ Could not get pod status - check SSH access to HP")
            return

        # Print status
        self.print_status(current_status)

        # Detect issues
        if self.last_status:
            issues = self.detect_issues(current_status)
            if issues:
                print(f"\n{'='*80}")
                print("⚠️  Issues Detected:")
                print(f"{'='*80}")
                for issue in issues:
                    print(f"  {issue}")

        # Save status for next comparison
        self.last_status = current_status

    def monitor_loop(self, interval=60):
        """Continuously monitor K3s cluster"""
        print(f"🚀 Starting Kilo Agent - monitoring every {interval} seconds")
        print("Press Ctrl+C to stop\n")

        self.monitoring = True

        try:
            while self.monitoring:
                self.monitor_once()
                print(f"\n💤 Sleeping {interval} seconds...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 Stopping agent...")
            self.monitoring = False


def main():
    """Main entry point"""
    import sys

    agent = SimpleKiloAgent()

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Run once and exit
        agent.monitor_once()
    else:
        # Continuous monitoring
        agent.monitor_loop(interval=60)


if __name__ == "__main__":
    main()
