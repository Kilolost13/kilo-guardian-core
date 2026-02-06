"""
Comprehensive Error Tracking and Reporting System

Tracks all errors, attempts self-healing, and reports issues to HQ.
"""

import hashlib
import json
import logging
import os
import platform
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

logger = logging.getLogger(__name__)


@dataclass
class ErrorReport:
    """Structured error report for tracking and transmission."""

    error_id: str
    timestamp: str
    severity: str
    component: str
    error_type: str
    message: str
    stack_trace: str
    context: dict
    system_info: dict
    recovery_attempted: bool
    recovery_successful: bool
    appliance_id: str
    version: str


class ErrorTracker:
    """
    Central error tracking with self-healing and reporting.

    Features:
    - Deduplicates similar errors
    - Attempts automatic recovery
    - Reports to HQ (if configured)
    - Logs locally for analysis
    - Tracks recovery success rate
    """

    def __init__(self):
        self.error_log_path = Path("/var/lib/kilo/errors")
        self.error_log_path.mkdir(parents=True, exist_ok=True)

        self.error_db = self.error_log_path / "errors.jsonl"
        self.stats_file = self.error_log_path / "stats.json"

        # HQ reporting endpoint (configurable)
        self.hq_endpoint = os.getenv(
            "KILO_HQ_ENDPOINT", "https://telemetry.example.com/api/errors"
        )
        self.hq_api_key = os.getenv("KILO_HQ_API_KEY", "")

        # Appliance identification
        self.appliance_id = self._get_appliance_id()
        self.version = self._get_version()

        # Error deduplication cache (in-memory)
        self.seen_errors: Dict[str, int] = {}  # error_id -> count

        # Recovery handlers registry
        self.recovery_handlers: Dict[str, callable] = {}
        self._register_default_handlers()

        # In-memory stats
        if self.stats_file.exists():
            self.stats = json.loads(self.stats_file.read_text())
        else:
            self.stats = {
                "total_errors": 0,
                "by_component": {},
                "by_type": {},
                "recovery_attempts": 0,
                "recovery_successes": 0,
            }

        logger.info(f"ErrorTracker initialized (appliance: {self.appliance_id})")

    def _get_appliance_id(self) -> str:
        """Get unique appliance identifier."""
        id_file = Path("/etc/kilo/appliance-id")

        if id_file.exists():
            return id_file.read_text().strip()

        # Generate from MAC address or hostname
        try:
            import uuid

            mac = uuid.getnode()
            appliance_id = hashlib.sha256(str(mac).encode()).hexdigest()[:16]

            # Try to persist
            try:
                id_file.parent.mkdir(parents=True, exist_ok=True)
                id_file.write_text(appliance_id)
            except:
                pass

            return appliance_id
        except:
            return "unknown"

    def _get_version(self) -> str:
        """Get current system version."""
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "dev"

    def _register_default_handlers(self):
        """Register built-in recovery handlers."""
        self.recovery_handlers.update(
            {
                "PluginError": self._recover_plugin_error,
                "DatabaseError": self._recover_database_error,
                "NetworkError": self._recover_network_error,
                "FileNotFoundError": self._recover_file_error,
                "PermissionError": self._recover_permission_error,
                "MemoryError": self._recover_memory_error,
            }
        )

    def track_error(
        self,
        exception: Exception = None,
        component: str = None,
        severity: str = "error",
        context: Optional[Dict[str, Any]] = None,
        attempt_recovery: bool = True,
        error: Exception = None,
    ) -> ErrorReport:
        """
        Track an error and attempt recovery.

        Args:
            exception: The exception that occurred (positional or keyword)
            error: Alias for exception (for compatibility)
            component: Component where error occurred
            severity: critical, error, warning
            context: Additional context dict
            attempt_recovery: Whether to try auto-recovery

        Returns:
            ErrorReport object
        """

        # Support 'error' as alias for 'exception' for test compatibility
        if exception is None and error is not None:
            exception = error
        if exception is None:
            raise ValueError("No exception provided to track_error")

        error_type = type(exception).__name__
        message = str(exception)
        stack_trace = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )

        # Generate error ID (hash of type + message + component)
        error_signature = f"{component}:{error_type}:{message}"
        error_id = hashlib.sha256(error_signature.encode()).hexdigest()[:16]

        # Deduplicate
        if error_id in self.seen_errors:
            self.seen_errors[error_id] += 1
            # Don't report every occurrence, just count
            if self.seen_errors[error_id] % 10 != 0:  # Report every 10th
                return None
        else:
            self.seen_errors[error_id] = 1

        # Attempt recovery
        recovery_attempted = False
        recovery_successful = False

        if attempt_recovery and error_type in self.recovery_handlers:
            recovery_attempted = True
            try:
                self.recovery_handlers[error_type](exception, context)
                recovery_successful = True
                logger.info(f"✓ Recovery successful for {error_type}")
            except Exception as e:
                logger.error(f"Recovery failed for {error_type}: {e}")

        # Build report
        report = ErrorReport(
            error_id=error_id,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity,
            component=component,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            context=context or {},
            system_info=self._get_system_info(),
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful,
            appliance_id=self.appliance_id,
            version=self.version,
        )

        # Log locally
        self._log_error(report)

        # Report to HQ (async, non-blocking)
        if severity in ["critical", "error"]:
            self._report_to_hq(report)

        # Update stats
        self._update_stats(report)

        return report

    def register_recovery_handler(self, error_type: str, handler: callable):
        """Register a custom recovery handler for a specific error type."""
        self.recovery_handlers[error_type] = handler

    def _log_error(self, report: ErrorReport):
        """Log error to local JSONL file."""
        try:
            with open(self.error_db, "a") as f:
                f.write(json.dumps(asdict(report)) + "\n")
        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    def _report_to_hq(self, report: ErrorReport):
        """Send error report to HQ endpoint (non-blocking)."""
        if not self.hq_endpoint or not self.hq_api_key:
            logger.debug("HQ reporting disabled (no endpoint/key)")
            return

        try:
            payload = asdict(report)
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.hq_api_key,
                "X-Appliance-ID": self.appliance_id,
            }

            response = requests.post(
                self.hq_endpoint, json=payload, headers=headers, timeout=5
            )

            if response.status_code == 200:
                logger.info(f"✓ Error reported to HQ: {report.error_id}")
            else:
                logger.warning(f"HQ report failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to report to HQ: {e}")

    def _update_stats(self, report: ErrorReport):
        """Update error statistics."""
        try:
            # Update in-memory stats
            self.stats["total_errors"] += 1
            self.stats["by_component"][report.component] = (
                self.stats["by_component"].get(report.component, 0) + 1
            )
            self.stats["by_type"][report.error_type] = (
                self.stats["by_type"].get(report.error_type, 0) + 1
            )

            if report.recovery_attempted:
                self.stats["recovery_attempts"] += 1
                if report.recovery_successful:
                    self.stats["recovery_successes"] += 1

            self.stats["last_updated"] = datetime.utcnow().isoformat()

            self.stats_file.write_text(json.dumps(self.stats, indent=2))
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")

    def _get_system_info(self) -> Dict[str, Any]:
        """Gather system information for error context."""
        try:
            return {
                "platform": platform.platform(),
                "python_version": sys.version,
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "uptime_seconds": time.time() - psutil.boot_time(),
            }
        except:
            return {"error": "Failed to gather system info"}

    # === Recovery Handlers ===

    def _recover_plugin_error(self, exception: Exception, context: dict):
        """Attempt to recover from plugin errors."""
        plugin_name = context.get("plugin_name")
        if not plugin_name:
            return

        logger.info(f"Attempting plugin recovery: {plugin_name}")

        # Try to reload plugin
        try:
            from kilo_v2.plugin_manager import PluginManager

            pm = PluginManager()
            pm.reload_plugin(plugin_name)
            logger.info(f"✓ Plugin reloaded: {plugin_name}")
        except:
            logger.error(f"Plugin reload failed: {plugin_name}")
            raise

    def _recover_database_error(self, exception: Exception, context: dict):
        """Attempt to recover from database errors."""
        logger.info("Attempting database recovery")

        # Try to reconnect
        try:
            from kilo_v2 import db

            db.init_db()
            logger.info("✓ Database reconnected")
        except:
            logger.error("Database recovery failed")
            raise

    def _recover_network_error(self, exception: Exception, context: dict):
        """Attempt to recover from network errors."""
        logger.info("Network error detected - will retry on next request")
        # Network errors typically resolve themselves, just log

    def _recover_file_error(self, exception: Exception, context: dict):
        """Attempt to recover from file not found errors."""
        file_path = context.get("file_path")
        if not file_path:
            return

        logger.info(f"Attempting file recovery: {file_path}")

        # Try to recreate missing file/directory
        try:
            path = Path(file_path)
            if context.get("is_directory"):
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                if context.get("default_content"):
                    path.write_text(context["default_content"])
            logger.info(f"✓ File/dir created: {file_path}")
        except:
            raise

    def _recover_permission_error(self, exception: Exception, context: dict):
        """Attempt to recover from permission errors."""
        file_path = context.get("file_path")
        logger.warning(
            f"Permission error on {file_path} - operator intervention needed"
        )
        # Log for manual fix, can't auto-fix permissions

    def _recover_memory_error(self, exception: Exception, context: dict):
        """Attempt to recover from memory errors."""
        logger.critical("Memory error detected - forcing garbage collection")

        import gc

        gc.collect()

        # Log memory hog if possible
        try:
            top_memory = sorted(
                [(obj, sys.getsizeof(obj)) for obj in gc.get_objects()],
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            logger.warning(f"Top memory consumers: {top_memory}")
        except:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        if self.stats_file.exists():
            return json.loads(self.stats_file.read_text())
        return {}

    def get_recent_errors(self, limit: int = 50) -> List[ErrorReport]:
        """Get recent error reports."""
        if not self.error_db.exists():
            return []

        errors = []
        with open(self.error_db, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    data = json.loads(line)
                    errors.append(ErrorReport(**data))
                except:
                    pass

        return errors


# Global instance
_error_tracker = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def track_error(
    exception: Exception,
    component: str,
    severity: str = "error",
    context: Optional[Dict[str, Any]] = None,
) -> Optional[ErrorReport]:
    """Convenience function to track errors."""
    return get_error_tracker().track_error(exception, component, severity, context)
