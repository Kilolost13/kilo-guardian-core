"""
Kilo Guardian Self-Healing System
Automatic recovery from errors and system failures
"""

import logging
import os
import subprocess
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("SelfHealer")
logging.basicConfig(level=logging.INFO)


class RecoveryAction:
    """Represents a recovery action that can be taken."""

    def __init__(
        self, name: str, description: str, action: Callable, auto_execute: bool = False
    ):
        self.name = name
        self.description = description
        self.action = action
        self.auto_execute = auto_execute
        self.last_executed = None
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0

    def execute(self) -> bool:
        """Execute the recovery action."""
        try:
            logger.info(f"🔧 Executing recovery action: {self.name}")
            self.action()
            self.last_executed = datetime.now()
            self.execution_count += 1
            self.success_count += 1
            logger.info(f"✅ Recovery action succeeded: {self.name}")
            return True
        except Exception as e:
            self.execution_count += 1
            self.failure_count += 1
            logger.error(f"❌ Recovery action failed: {self.name} - {e}")
            return False


class SelfHealer:
    """
    Enhanced self-healing system with automatic recovery capabilities.
    """

    def __init__(self, llm_engine=None):
        self.llm_engine = llm_engine
        self.last_error = None
        self.error_history = []
        self.max_error_history = 100

        # Recovery state
        self.recovery_actions = {}
        self.auto_recovery_enabled = True
        self.recovery_in_progress = False

        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_monitor_running = False
        self.health_monitor_thread = None

        self._register_default_recovery_actions()

        logger.info("🏥 Self-Healer initialized")

    def _register_default_recovery_actions(self):
        """Register default recovery actions."""

        # Action: Restart failed plugins
        self.register_recovery_action(
            "restart_failed_plugins",
            "Restart plugins that have crashed",
            self._restart_failed_plugins,
            auto_execute=True,
        )

        # Action: Clear temporary files
        self.register_recovery_action(
            "clear_temp_files",
            "Clear temporary files and caches",
            self._clear_temp_files,
            auto_execute=True,
        )

        # Action: Restore from backup
        self.register_recovery_action(
            "restore_backup",
            "Restore critical files from backup",
            self._restore_from_backup,
            auto_execute=False,  # Requires manual confirmation
        )

        # Action: Reset to safe mode
        self.register_recovery_action(
            "safe_mode",
            "Enter safe mode with minimal plugins",
            self._enter_safe_mode,
            auto_execute=False,
        )

        # Action: Repair file integrity
        self.register_recovery_action(
            "repair_integrity",
            "Attempt to repair corrupted files",
            self._repair_file_integrity,
            auto_execute=True,
        )

    def register_recovery_action(
        self, name: str, description: str, action: Callable, auto_execute: bool = False
    ):
        """Register a new recovery action."""
        self.recovery_actions[name] = RecoveryAction(
            name, description, action, auto_execute
        )
        logger.debug(f"Registered recovery action: {name}")

    def _restart_failed_plugins(self):
        """Restart plugins that have failed."""
        try:
            # Get the global plugin manager instance from server_core
            from kilo_v2.server_core import pm as plugin_manager

            if plugin_manager is None:
                logger.warning("Plugin manager not available yet")
                return False

            logger.info("Checking for failed plugins...")
            restarted_count = 0

            # Iterate through plugins and restart any that are unhealthy
            for plugin in plugin_manager.plugins:
                try:
                    # Check plugin health if method exists
                    if hasattr(plugin, "health"):
                        health = plugin.health()
                        if isinstance(health, dict) and not health.get(
                            "ok", health.get("status") == "healthy"
                        ):
                            plugin_name = plugin.get_name()
                            logger.info(f"Restarting unhealthy plugin: {plugin_name}")

                            # Stop and restart the plugin
                            if hasattr(plugin, "stop"):
                                plugin.stop()
                            if hasattr(plugin, "start"):
                                plugin.start()

                            restarted_count += 1
                except Exception as plugin_error:
                    logger.warning(f"Error checking/restarting plugin: {plugin_error}")

            logger.info(f"Restarted {restarted_count} failed plugins")
            return True

        except ImportError:
            logger.warning(
                "Could not import plugin manager - server may not be running"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to restart plugins: {e}")
            return False

    def _clear_temp_files(self):
        """Clear temporary files and caches."""
        temp_paths = [
            "__pycache__",
            "kilo_v2/__pycache__",
            "kilo_v2/plugins/__pycache__",
            "*.pyc",
            "*.log.old",
        ]

        cleaned = 0
        for pattern in temp_paths:
            try:
                if "*" in pattern:
                    # Use shell command for wildcards
                    subprocess.run(f"rm -f {pattern}", shell=True, check=False)
                elif os.path.isdir(pattern):
                    subprocess.run(["rm", "-rf", pattern], check=False)
                elif os.path.isfile(pattern):
                    os.remove(pattern)
                cleaned += 1
            except Exception as e:
                logger.debug(f"Could not clean {pattern}: {e}")

        logger.info(f"Cleaned {cleaned} temporary items")
        return True

    def _restore_from_backup(self):
        """Restore critical files from backup."""
        backup_dir = "kilo_data/backups"

        if not os.path.exists(backup_dir):
            logger.warning("No backup directory found")
            return False

        logger.info(f"Restoring from backup: {backup_dir}")

        # Find the most recent backup
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")], reverse=True
        )

        if not backups:
            logger.warning("No backup files found")
            return False

        latest_backup = os.path.join(backup_dir, backups[0])
        logger.info(f"Using backup: {latest_backup}")

        # Critical files to restore
        critical_files = [
            "kilo_guardian_keep.db",
            "kilo_data/file_integrity_baseline.json",
            "kilo_data/life_tracking.json",
        ]

        try:
            import tarfile

            with tarfile.open(latest_backup, "r:gz") as tar:
                # Get list of files in backup
                backup_files = tar.getnames()

                for critical_file in critical_files:
                    # Check if file exists in backup
                    matching = [f for f in backup_files if critical_file in f]
                    if matching:
                        # Extract just this file
                        for match in matching:
                            try:
                                tar.extract(match, path=".")
                                logger.info(f"Restored: {match}")
                            except Exception as e:
                                logger.warning(f"Could not restore {match}: {e}")

            logger.info("Backup restoration complete")
            return True

        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return False

    def _enter_safe_mode(self):
        """Enter safe mode with minimal plugins."""
        logger.warning("⚠️ Entering SAFE MODE - disabling non-critical plugins")

        # Create safe mode marker
        try:
            os.makedirs("kilo_data", exist_ok=True)
            with open("kilo_data/SAFE_MODE", "w") as f:
                f.write(datetime.now().isoformat())
            return True
        except Exception as e:
            logger.error(f"Failed to enter safe mode: {e}")
            return False

    def _repair_file_integrity(self):
        """Attempt to repair corrupted files."""
        logger.info("Checking file integrity...")

        # Check database files
        db_files = ["kilo_guardian_keep.db", "finance.db"]
        repaired_any = False

        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    # SQLite integrity check
                    import sqlite3

                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()

                    if result[0] != "ok":
                        logger.error(f"Database corruption detected: {db_file}")
                        conn.close()

                        # Attempt repair: dump and restore
                        backup_file = f"{db_file}.corrupted"
                        repaired_file = f"{db_file}.repaired"

                        try:
                            # Rename corrupted file
                            os.rename(db_file, backup_file)

                            # Try to recover data using .recover command
                            recover_result = subprocess.run(
                                ["sqlite3", backup_file, ".recover"],
                                capture_output=True,
                                text=True,
                                timeout=60,
                            )

                            if recover_result.returncode == 0 and recover_result.stdout:
                                # Create new database from recovered SQL
                                new_conn = sqlite3.connect(db_file)
                                new_conn.executescript(recover_result.stdout)
                                new_conn.close()
                                logger.info(f"✅ Repaired {db_file} via recovery")
                                repaired_any = True
                            else:
                                # Recovery failed, try to restore from backup
                                logger.warning(
                                    f"Recovery failed, attempting backup restore for {db_file}"
                                )
                                if self._restore_from_backup():
                                    repaired_any = True
                                else:
                                    # Restore original corrupted file
                                    os.rename(backup_file, db_file)

                        except Exception as repair_error:
                            logger.error(f"Repair failed for {db_file}: {repair_error}")
                            # Restore original if repair failed
                            if os.path.exists(backup_file) and not os.path.exists(
                                db_file
                            ):
                                os.rename(backup_file, db_file)
                    else:
                        logger.info(f"✅ {db_file} integrity OK")
                        conn.close()

                except Exception as e:
                    logger.error(f"Failed to check {db_file}: {e}")

        return True

    def diagnose_last_error(self):
        """Diagnose the last error and suggest recovery actions."""
        if not self.last_error:
            return "No recent errors to diagnose."

        diagnosis = {
            "error": self.last_error,
            "timestamp": datetime.now().isoformat(),
            "suggested_actions": [],
        }

        # Analyze error type and suggest actions
        error_lower = self.last_error.lower()

        if "plugin" in error_lower or "timeout" in error_lower:
            diagnosis["suggested_actions"].append("restart_failed_plugins")

        if "memory" in error_lower or "disk" in error_lower:
            diagnosis["suggested_actions"].append("clear_temp_files")

        if "corrupt" in error_lower or "integrity" in error_lower:
            diagnosis["suggested_actions"].append("repair_integrity")
            diagnosis["suggested_actions"].append("restore_backup")

        if "critical" in error_lower or "fatal" in error_lower:
            diagnosis["suggested_actions"].append("safe_mode")

        # Use LLM if available
        if self.llm_engine:
            try:
                prompt = (
                    f"You are a system diagnostic AI. Analyze this error and provide:\n"
                    f"1. Root cause analysis\n"
                    f"2. Recommended fix steps\n"
                    f"3. Prevention measures\n\n"
                    f"Error: {self.last_error}"
                )

                # Call the LLM engine
                if hasattr(self.llm_engine, "call"):
                    llm_diagnosis = self.llm_engine.call(prompt)
                elif hasattr(self.llm_engine, "generate"):
                    llm_diagnosis = self.llm_engine.generate(prompt)
                elif callable(self.llm_engine):
                    llm_diagnosis = self.llm_engine(prompt)
                else:
                    llm_diagnosis = "LLM engine interface not recognized"

                diagnosis["llm_analysis"] = llm_diagnosis
            except Exception as e:
                logger.warning(f"LLM diagnosis failed: {e}")
                diagnosis["llm_analysis"] = f"LLM analysis unavailable: {str(e)}"

        logger.info(
            f"Diagnosis complete: {len(diagnosis['suggested_actions'])} actions suggested"
        )
        return diagnosis

    def attempt_recovery(self, auto_only: bool = True) -> Dict[str, Any]:
        """
        Attempt automatic recovery from the last error.

        Args:
            auto_only: Only execute actions marked for auto-execution
        """
        if self.recovery_in_progress:
            logger.warning("Recovery already in progress")
            return {"success": False, "message": "Recovery already in progress"}

        self.recovery_in_progress = True

        try:
            diagnosis = self.diagnose_last_error()

            if isinstance(diagnosis, str):
                return {"success": False, "message": diagnosis}

            results = {
                "diagnosis": diagnosis,
                "actions_executed": [],
                "actions_succeeded": [],
                "actions_failed": [],
            }

            # Execute suggested recovery actions
            for action_name in diagnosis.get("suggested_actions", []):
                if action_name in self.recovery_actions:
                    action = self.recovery_actions[action_name]

                    # Skip if not auto-executable and we're in auto-only mode
                    if auto_only and not action.auto_execute:
                        logger.info(f"Skipping manual action: {action_name}")
                        continue

                    results["actions_executed"].append(action_name)

                    if action.execute():
                        results["actions_succeeded"].append(action_name)
                    else:
                        results["actions_failed"].append(action_name)

            success = len(results["actions_succeeded"]) > 0

            logger.info(
                f"Recovery {'succeeded' if success else 'failed'}: "
                f"{len(results['actions_succeeded'])}/{len(results['actions_executed'])} actions successful"
            )

            results["success"] = success
            return results

        finally:
            self.recovery_in_progress = False

    def monitor(self, func, *args, **kwargs):
        """
        Monitor function execution and automatically recover from errors.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()

            self.last_error = f"{error_msg}\n{error_trace}"

            # Add to history
            self.error_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "function": func.__name__,
                    "error": error_msg,
                    "trace": error_trace,
                }
            )

            # Trim history
            if len(self.error_history) > self.max_error_history:
                self.error_history = self.error_history[-self.max_error_history :]

            logger.error(f"Function '{func.__name__}' crashed: {e}")

            # Attempt automatic recovery if enabled
            if self.auto_recovery_enabled:
                logger.info("🔧 Attempting automatic recovery...")
                recovery_result = self.attempt_recovery(auto_only=True)

                if recovery_result.get("success"):
                    logger.info("✅ Automatic recovery successful")
                else:
                    logger.warning("⚠️ Automatic recovery failed")

            raise  # Re-raise the exception after logging and recovery attempt

    def start_health_monitoring(self):
        """Start continuous health monitoring."""
        if self.health_monitor_running:
            logger.warning("Health monitoring already running")
            return

        self.health_monitor_running = True
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop, daemon=True
        )
        self.health_monitor_thread.start()
        logger.info("✅ Health monitoring started")

    def stop_health_monitoring(self):
        """Stop health monitoring."""
        self.health_monitor_running = False
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=5)
        logger.info("⏹️ Health monitoring stopped")

    def _health_monitor_loop(self):
        """Continuous health monitoring loop."""
        while self.health_monitor_running:
            try:
                # Check system health
                self._perform_health_check()

                # Sleep until next check
                time.sleep(self.health_check_interval)

            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                time.sleep(60)  # Back off on errors

    def _perform_health_check(self):
        """Perform system health check."""
        # Check disk space
        try:
            import shutil

            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100

            if free_percent < 10:
                logger.warning(f"⚠️ Low disk space: {free_percent:.1f}% free")
                # Trigger cleanup
                if "clear_temp_files" in self.recovery_actions:
                    self.recovery_actions["clear_temp_files"].execute()
        except Exception as e:
            logger.debug(f"Disk check failed: {e}")

        # Check memory usage
        try:
            import psutil

            memory = psutil.virtual_memory()

            if memory.percent > 90:
                logger.warning(f"⚠️ High memory usage: {memory.percent}%")
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current self-healer status."""
        return {
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "recovery_in_progress": self.recovery_in_progress,
            "health_monitoring": self.health_monitor_running,
            "last_error": self.last_error,
            "error_count": len(self.error_history),
            "recovery_actions": {
                name: {
                    "description": action.description,
                    "auto_execute": action.auto_execute,
                    "execution_count": action.execution_count,
                    "success_rate": (
                        (action.success_count / action.execution_count * 100)
                        if action.execution_count > 0
                        else 0
                    ),
                }
                for name, action in self.recovery_actions.items()
            },
        }

    def execute_recovery_action(self, action_name: str) -> bool:
        """Manually execute a specific recovery action."""
        if action_name not in self.recovery_actions:
            logger.error(f"Unknown recovery action: {action_name}")
            return False

        return self.recovery_actions[action_name].execute()
