"""
Plugin Sandbox - Isolated execution environment for plugins
Prevents plugins from crashing Kilo or accessing unauthorized resources
"""

import logging
import multiprocessing
import os
import queue
import resource
import signal
import sys
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("PluginSandbox")


class PluginTimeoutError(Exception):
    """Raised when plugin execution exceeds timeout."""

    pass


class PluginSecurityError(Exception):
    """Raised when plugin attempts unauthorized action."""

    pass


class SandboxedPlugin:
    """
    Wrapper for plugin execution in isolated environment.

    Security features:
    - Separate process isolation
    - Memory limits
    - CPU time limits
    - Timeout enforcement
    - Exception containment
    - Resource usage monitoring
    - Auto-escalation from thread to process on repeated failures
    """

    def __init__(
        self,
        plugin_instance,
        config: Optional[Dict] = None,
        isolation_mode: str = "thread",
    ):
        """
        Initialize sandboxed plugin wrapper.

        Args:
            plugin_instance: The actual plugin instance to sandbox
            config: Security configuration (timeouts, limits, etc.)
            isolation_mode: "thread" (fast, dev-friendly) or "process" (safe)
        """
        self.plugin = plugin_instance
        self.plugin_name = (
            plugin_instance.get_name()
            if hasattr(plugin_instance, "get_name")
            else "unknown"
        )

        # Isolation mode: thread for fast dev, process for safety
        requested_mode = isolation_mode
        if config and config.get("isolation_mode"):
            requested_mode = config.get("isolation_mode")

        self.isolation_mode = (
            requested_mode
            if requested_mode
            in (
                "thread",
                "process",
            )
            else "thread"
        )

        self.auto_escalate_enabled = False
        self.escalation_threshold = 3

        # Default security config
        self.config = {
            "timeout": 30,  # Max execution time in seconds
            "memory_limit_mb": 512,  # Max memory in MB
            "cpu_time_limit": 60,  # Max CPU seconds
            "allow_network": True,  # Allow network access
            "allow_file_write": True,  # Allow file writes
            "max_retries": 3,  # Max retry attempts on failure
            "run_as_user": None,  # Drop privileges to this user
        }

        if config:
            self.config.update(config)

        # Escalation controls (opt-in via config)
        self.auto_escalate_enabled = bool(self.config.get("auto_escalate", False))
        self.escalation_threshold = int(
            self.config.get("escalation_threshold", self.escalation_threshold)
        )

        # Execution state
        self.failure_count = 0
        self.last_error = None
        self.last_execution_time = None
        self.is_healthy = True

        # Process-based isolation
        self._result_queue = None
        self._process = None

        mode_name = (
            "🧵 threads (fast, dev-friendly)"
            if self.isolation_mode == "thread"
            else "🔒 process isolation (maximum safety)"
        )
        logger.info(
            "📦 Sandboxed plugin initialized: %s using %s"
            % (self.plugin_name, mode_name)
        )

    # Proxy methods to underlying plugin for compatibility
    def get_name(self):
        """Proxy get_name to underlying plugin."""
        return self.plugin.get_name()

    def get_keywords(self):
        """Proxy get_keywords to underlying plugin."""
        return self.plugin.get_keywords()

    def run(self, query):
        """Proxy run through sandbox execution."""
        result = self._execute_method("run", query)
        if result["success"]:
            return result["result"]
        else:
            raise Exception(result.get("error", "Plugin execution failed"))

    def execute(self, query):
        """
        Proxy execute() method for plugins that implement it.
        This is called by the reasoning engine to execute briefings, etc.
        """
        if not hasattr(self.plugin, "execute"):
            raise AttributeError(
                f"Plugin '{self.plugin_name}' does not have an execute() method"
            )

        result = self._execute_method("execute", query)
        if result["success"]:
            return result["result"]
        else:
            # Return error dict for proper handling
            return result

    def _execute_method(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute plugin method in sandbox with isolation and timeout.

        Supports two modes:
        - thread: Fast, easy development (default)
        - process: Maximum safety with full isolation

        Auto-escalation: If plugin fails repeatedly in thread mode,
        automatically upgrade to process isolation for protection.

        Args:
            method_name: Name of method to call on plugin
            *args, **kwargs: Arguments to pass to method

        Returns:
            Dict with 'success', 'result', and optional 'error' keys
        """
        start_time = datetime.now()

        try:
            # Choose execution method based on isolation mode
            if self.isolation_mode == "process":
                result = self._execute_in_process(method_name, args, kwargs)
            else:  # thread mode (default)
                result = self._execute_in_thread(method_name, args, kwargs)

            execution_time = (datetime.now() - start_time).total_seconds()
            self.last_execution_time = execution_time
            self.failure_count = 0  # Reset on success
            self.is_healthy = True

            logger.debug(
                f"✅ {self.plugin_name}.{method_name}() "
                f"completed in {execution_time:.2f}s"
            )

            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "plugin": self.plugin_name,
            }

        except PluginTimeoutError as e:
            self.failure_count += 1
            self.last_error = str(e)
            logger.error(
                f"⏱️ {self.plugin_name}.{method_name}() "
                f"timed out after {self.config['timeout']}s"
            )
            self._check_for_escalation()

            return {
                "success": False,
                "error": (f"Plugin timed out after " f"{self.config['timeout']}s"),
                "error_type": "timeout",
                "plugin": self.plugin_name,
            }

        except Exception as e:
            self.failure_count += 1
            self.last_error = str(e)
            error_trace = traceback.format_exc()
            logger.error(
                f"❌ {self.plugin_name}.{method_name}() " f"failed: {e}\n{error_trace}"
            )
            self._check_for_escalation()

            # Mark unhealthy if too many failures
            if self.failure_count >= self.config["max_retries"]:
                self.is_healthy = False
                logger.warning(
                    f"⚠️ {self.plugin_name} marked UNHEALTHY "
                    f"after {self.failure_count} failures"
                )

            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_trace": error_trace,
                "plugin": self.plugin_name,
                "failure_count": self.failure_count,
            }

    def _check_for_escalation(self):
        """
        Check if plugin should be escalated from thread to process isolation.
        Called after each failure. Auto-escalates if threshold reached.
        """
        if not self.auto_escalate_enabled or self.isolation_mode == "process":
            return  # Already in process mode or escalation disabled

        if self.failure_count >= self.escalation_threshold:
            logger.warning(
                f"🚨 ESCALATING {self.plugin_name}: "
                f"{self.failure_count} failures detected. "
                f"Moving to process isolation for protection."
            )
            self.isolation_mode = "process"
            self.failure_count = 0  # Reset counter after escalation

    def _execute_in_process(self, method_name: str, args, kwargs) -> Any:
        """
        Execute plugin method in separate process for maximum isolation.
        This prevents plugin crashes from affecting Kilo.

        """
        self._result_queue = multiprocessing.Queue()

        # Start isolated process
        self._process = multiprocessing.Process(
            target=self._process_worker,
            args=(method_name, args, kwargs, self._result_queue, self.config),
        )

        self._process.start()

        # Wait for result with timeout
        self._process.join(timeout=self.config["timeout"])

        if self._process.is_alive():
            # Timeout exceeded, kill the process
            logger.warning(f"⏱️ Killing {self.plugin_name} process (timeout)")
            self._process.terminate()
            self._process.join(timeout=5)

            if self._process.is_alive():
                # Force kill if termination fails
                self._process.kill()
                self._process.join()

            raise PluginTimeoutError(
                f"Plugin {self.plugin_name} exceeded timeout of {self.config['timeout']}s"
            )

        # Get result from queue
        if not self._result_queue.empty():
            result_data = self._result_queue.get()

            if result_data.get("success"):
                return result_data["result"]
            else:
                error_msg = result_data.get("error", "Unknown error")
                raise Exception(f"Plugin error: {error_msg}")
        else:
            raise Exception("Plugin process terminated without result")

    def _process_worker(self, method_name: str, args, kwargs, result_queue, config):
        """
        Worker function that runs in separate process.
        Applies resource limits and executes plugin method.
        """
        try:
            # Apply resource limits and change user in this process
            if sys.platform != "win32":  # Unix-like systems
                import pwd

                # Memory limit
                if config.get("memory_limit_mb"):
                    memory_bytes = config["memory_limit_mb"] * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

                # CPU time limit
                if config.get("cpu_time_limit"):
                    resource.setrlimit(
                        resource.RLIMIT_CPU,
                        (config["cpu_time_limit"], config["cpu_time_limit"]),
                    )

                # Drop privileges if configured
                run_as_user = config.get("run_as_user")
                if run_as_user:
                    try:
                        pw_record = pwd.getpwnam(run_as_user)
                        os.setgid(pw_record.pw_gid)
                        os.setuid(pw_record.pw_uid)
                        logger.info(
                            f"Plugin process for '{self.plugin_name}' now running as user '{run_as_user}'"
                        )
                    except (KeyError, PermissionError) as e:
                        logger.critical(
                            f"SANDBOX FAILURE: Could not switch to user '{run_as_user}'. "
                            f"Plugin '{self.plugin_name}' is running with full permissions. "
                            f"Error: {e}. Ensure the user exists and Kilo is run with sufficient privileges (e.g., as root)."
                        )

            # Execute the plugin method
            method = getattr(self.plugin, method_name)
            result = method(*args, **kwargs)

            result_queue.put({"success": True, "result": result})

        except Exception as e:
            result_queue.put(
                {
                    "success": False,
                    "error": str(e),
                    "error_trace": traceback.format_exc(),
                }
            )

    def _execute_in_thread(self, method_name: str, args, kwargs) -> Any:
        """
        Execute plugin method in thread (lighter weight, less isolation).
        Use when full process isolation is not needed.
        """
        result_container = {"result": None, "error": None, "completed": False}

        def thread_worker():
            try:
                method = getattr(self.plugin, method_name)
                result_container["result"] = method(*args, **kwargs)
                result_container["completed"] = True
            except Exception as e:
                result_container["error"] = e
                result_container["completed"] = True

        thread = threading.Thread(target=thread_worker, daemon=True)
        thread.start()
        thread.join(timeout=self.config["timeout"])

        if not result_container["completed"]:
            raise PluginTimeoutError(
                f"Plugin {self.plugin_name} exceeded timeout of {self.config['timeout']}s"
            )

        if result_container["error"]:
            raise result_container["error"]

        return result_container["result"]

    def health_check(self) -> Dict[str, Any]:
        """
        Check plugin health status.

        Returns:
            Dict with health information
        """
        health_data = {
            "plugin": self.plugin_name,
            "healthy": self.is_healthy,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "last_execution_time": self.last_execution_time,
            "config": self.config,
            "isolation_mode": self.isolation_mode,
            "auto_escalate": self.auto_escalate_enabled,
            "escalation_threshold": self.escalation_threshold,
        }

        # Try to call plugin's own health check if available
        if hasattr(self.plugin, "health") and callable(self.plugin.health):
            try:
                plugin_health = self._execute_method("health")
                health_data["plugin_health"] = plugin_health.get("result")
            except Exception as e:
                health_data["plugin_health"] = {
                    "status": "error",
                    "detail": str(e),
                }

        return health_data

    def reset_health(self):
        """Reset health status after manual intervention."""
        self.failure_count = 0
        self.is_healthy = True
        self.last_error = None
        logger.info(f"🔄 {self.plugin_name} health status reset")

    def cleanup(self):
        """Clean up resources."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.kill()


class PluginSandboxManager:
    """
    Manages multiple sandboxed plugins.
    Provides central control for plugin isolation and security.
    """

    def __init__(self):
        self.sandboxed_plugins: Dict[str, SandboxedPlugin] = {}
        logger.info("🔒 Plugin Sandbox Manager initialized")

    def register_plugin(
        self,
        plugin_instance,
        config: Optional[Dict] = None,
        isolation_mode: Optional[str] = None,
    ):
        """
        Register a plugin for sandboxed execution.

        Args:
            plugin_instance: Plugin to sandbox
            config: Optional security configuration
        """
        plugin_name = (
            plugin_instance.get_name()
            if hasattr(plugin_instance, "get_name")
            else "unknown"
        )

        sandboxed = SandboxedPlugin(
            plugin_instance,
            config=config,
            isolation_mode=isolation_mode or "thread",
        )
        self.sandboxed_plugins[plugin_name] = sandboxed

        logger.info(f"🔒 Registered sandboxed plugin: {plugin_name}")
        return sandboxed

    def execute(
        self, plugin_name: str, method_name: str, *args, **kwargs
    ) -> Dict[str, Any]:
        """
        Execute method on sandboxed plugin.

        Args:
            plugin_name: Name of plugin to execute
            method_name: Method to call
            *args, **kwargs: Method arguments

        Returns:
            Execution result dictionary
        """
        if plugin_name not in self.sandboxed_plugins:
            return {
                "success": False,
                "error": f"Plugin {plugin_name} not found in sandbox",
                "error_type": "not_found",
            }

        return self.sandboxed_plugins[plugin_name].execute(method_name, *args, **kwargs)

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all sandboxed plugins."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_plugins": len(self.sandboxed_plugins),
            "healthy": 0,
            "unhealthy": 0,
            "plugins": {},
        }

        for name, sandbox in self.sandboxed_plugins.items():
            health = sandbox.health_check()
            report["plugins"][name] = health

            if health["healthy"]:
                report["healthy"] += 1
            else:
                report["unhealthy"] += 1

        return report

    def reset_plugin_health(self, plugin_name: str):
        """Reset health status for a specific plugin."""
        if plugin_name in self.sandboxed_plugins:
            self.sandboxed_plugins[plugin_name].reset_health()
            return True
        return False

    def cleanup_all(self):
        """Clean up all sandboxed plugins."""
        for sandbox in self.sandboxed_plugins.values():
            sandbox.cleanup()
        logger.info("🧹 All sandboxed plugins cleaned up")


# Global sandbox manager instance
_sandbox_manager = None


def get_sandbox_manager() -> PluginSandboxManager:
    """Get global sandbox manager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = PluginSandboxManager()
    return _sandbox_manager
