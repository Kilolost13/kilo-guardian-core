"""
Proactive Monitor
=================
Extends the original kilo_proactive_agent.py into the unified system.

Checks (run in parallel each cycle):
  - Cluster layer   : pod phase, readiness, restart counts
  - Service layer   : HTTP health probes on every k3s service
  - Reminder layer  : upcoming reminders within 60 min
  - Finance layer   : budget threshold alerts (85 / 100 %)

All alerts are pushed through a caller-supplied async notify() callback
so the message-queue in main.py receives them without coupling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional

import httpx

logger = logging.getLogger("ProactiveMonitor")


class ProactiveMonitor:

    def __init__(self, registry, notify: Optional[Callable] = None):
        """
        Args:
            registry  : ServiceRegistry instance
            notify    : async (alert: dict) -> None  -- pushed for every new alert
        """
        self.registry = registry
        self.notify   = notify
        self._seen: set = set()   # dedup keys so one-shot alerts don't repeat
        self._last_run: Optional[datetime] = None
        self._last_results: Dict[str, Any] = {}

    # ----------------------------------------------------------
    # Cluster layer
    # ----------------------------------------------------------
    async def _check_cluster(self) -> List[Dict[str, Any]]:
        from k3s_controller import get_pods

        alerts: List[Dict] = []
        result = await get_pods()

        if "error" in result:
            return [{"type": "cluster", "severity": "high",
                     "message": f"Cannot read cluster state: {result['error']}"}]

        for pod in result.get("pods", []):
            name     = pod["name"]
            phase    = pod["phase"]
            ready    = pod["ready"]
            restarts = pod["restarts"]

            if phase != "Running" or not ready:
                key = f"not_ready:{name}"
                if key not in self._seen:
                    alerts.append({"type": "cluster", "severity": "high",
                                   "message": f"Pod {name}: phase={phase}, ready={ready}"})
                    self._seen.add(key)
            else:
                self._seen.discard(f"not_ready:{name}")   # recovered

            if restarts > 5:
                key = f"restarts:{name}:{restarts}"
                if key not in self._seen:
                    alerts.append({"type": "cluster", "severity": "medium",
                                   "message": f"Pod {name}: {restarts} restarts"})
                    self._seen.add(key)

        return alerts

    # ----------------------------------------------------------
    # Service-health layer
    # ----------------------------------------------------------
    async def _check_services(self) -> List[Dict[str, Any]]:
        alerts: List[Dict] = []
        health = await self.registry.health_check_all()

        for name, ok in health.items():
            key = f"unhealthy:{name}"
            if not ok and key not in self._seen:
                alerts.append({"type": "service", "severity": "high",
                               "message": f"Service {name} not responding to /health"})
                self._seen.add(key)
            elif ok:
                self._seen.discard(key)

        return alerts

    # ----------------------------------------------------------
    # Reminder layer
    # ----------------------------------------------------------
    async def _check_reminders(self) -> List[Dict[str, Any]]:
        svc = self.registry.services.get("reminder")
        if not svc or not svc.url:
            return []

        alerts: List[Dict] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{svc.url}/")
                if resp.status_code != 200:
                    return alerts

                now = datetime.now()
                for r in (resp.json() if isinstance(resp.json(), list) else []):
                    try:
                        when = datetime.fromisoformat(
                            r.get("when", "").replace("Z", "")
                        )
                        mins = (when - now).total_seconds() / 60
                        if 0 <= mins <= 60:
                            alerts.append({
                                "type": "reminder", "severity": "normal",
                                "message": f"Reminder in {int(mins)} min: {r.get('text', '?')}",
                            })
                    except (ValueError, AttributeError):
                        pass
        except Exception:
            pass
        return alerts

    # ----------------------------------------------------------
    # Budget layer
    # ----------------------------------------------------------
    async def _check_budgets(self) -> List[Dict[str, Any]]:
        svc = self.registry.services.get("financial")
        if not svc or not svc.url:
            return []

        alerts: List[Dict] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{svc.url}/budgets")
                if resp.status_code != 200:
                    return alerts

                for b in (resp.json() if isinstance(resp.json(), list) else []):
                    pct = b.get("percentage", 0)
                    cat = b.get("category", "?")

                    if pct >= 100:
                        alerts.append({"type": "budget", "severity": "urgent",
                                       "message": f"Over budget: {cat} at {pct:.0f}%"})
                    elif pct >= 85:
                        alerts.append({"type": "budget", "severity": "medium",
                                       "message": f"Budget warning: {cat} at {pct:.0f}%"})
        except Exception:
            pass
        return alerts

    # ----------------------------------------------------------
    # Aggregator
    # ----------------------------------------------------------
    async def run_checks(self) -> List[Dict[str, Any]]:
        """Run all checks in parallel.  Returns flat list of alert dicts."""
        results = await asyncio.gather(
            self._check_cluster(),
            self._check_services(),
            self._check_reminders(),
            self._check_budgets(),
            return_exceptions=True,
        )

        alerts: List[Dict] = []
        for r in results:
            if isinstance(r, list):
                alerts.extend(r)
            elif isinstance(r, Exception):
                logger.error("Monitor check raised: %s", r)

        # push through callback
        if self.notify:
            for a in alerts:
                await self.notify(a)

        self._last_run = datetime.now()
        self._last_results = {"alerts_count": len(alerts)}
        return alerts

    async def get_status(self) -> Dict[str, Any]:
        """Returns the summary used by the oversight dashboard."""
        # Probe a few services to see if they are 'checked'
        # In a real implementation we'd check their individual heartbeat timestamps
        health = await self.registry.health_check_all()
        
        return {
            "timestamp":         self._last_run.isoformat() if self._last_run else None,
            "financial_checked": health.get("financial", False),
            "habits_checked":    health.get("habits", False),
            "meds_checked":      health.get("meds", False),
            "alerts_count":      self._last_results.get("alerts_count", 0),
        }