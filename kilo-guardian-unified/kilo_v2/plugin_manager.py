import asyncio
import importlib.util
import json as _json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from inspect import getmembers, isclass
from pathlib import Path

# Try to import jsonschema for manifest validation; if missing we'll warn later
try:
    import jsonschema

    _HAS_JSONSCHEMA = True
except Exception:
    jsonschema = None
    _HAS_JSONSCHEMA = False

# Local config for plugin runtime settings
try:
    from . import config as cfg
except Exception:
    # fallback for direct execution contexts
    import kilo_v2.config as cfg

# Import plugin sandbox for isolation
try:
    from plugin_sandbox import get_sandbox_manager

    _HAS_SANDBOX = True
except Exception as e:
    logger_temp = logging.getLogger("PluginManager")
    logger_temp.warning(f"Sandbox unavailable, plugins will run without isolation: {e}")
    _HAS_SANDBOX = False

# Configure the logger for this module
logger = logging.getLogger("PluginManager")


class PluginManager:
    """
    Manages the loading, initialization, and execution of all modular plugins.
    It scans the 'plugins' directory, dynamically loads modules, finds classes
    inheriting from BasePlugin, and starts their background tasks.
    """

    def __init__(self, plugin_dir="plugins"):
        # The plugin directory is expected to be a sibling of this file
        self.plugin_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), plugin_dir)
        )
        self.plugins = []
        self._plugin_lock = threading.RLock()  # Thread-safe access to plugins
        self._BasePluginClass = None  # Placeholder for the BasePlugin class

        # Threat logging for browser security shield
        self.threat_log = []
        self._threat_lock = threading.RLock()

        logger.info(f"Plugin directory set to: {self.plugin_dir}")

        # Health/watchdog settings
        self.health_interval = getattr(cfg, "PLUGIN_HEALTH_INTERVAL", 20)
        self.restart_retries = getattr(cfg, "PLUGIN_RESTART_RETRIES", 3)
        self._watchdog_thread = None
        self._watchdog_stop = threading.Event()

        # Smart hybrid sandbox settings
        self.isolation_mode = getattr(cfg, "PLUGIN_ISOLATION_MODE", "thread")
        self.auto_escalate = getattr(cfg, "PLUGIN_AUTO_ESCALATE_ON_FAILURE", True)
        self.escalation_threshold = getattr(
            cfg, "PLUGIN_FAILURE_THRESHOLD_FOR_ESCALATION", 3
        )

        # Initialize sandbox manager if available
        self.sandbox_manager = get_sandbox_manager() if _HAS_SANDBOX else None
        if self.sandbox_manager:
            mode_desc = (
                "🧵 thread mode (fast, dev-friendly)"
                if self.isolation_mode == "thread"
                else "🔒 process isolation (maximum safety)"
            )
            escalate_str = " + auto-escalation on failure" if self.auto_escalate else ""
            logger.info(f"✅ Plugin sandbox enabled - {mode_desc}{escalate_str}")
        else:
            logger.warning(
                "⚠️ Plugin sandbox disabled - plugins will run " "in main process"
            )

        # Ensure the plugins directory is in sys.path for proper imports
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

    def _load_base_plugin(self):
        """Dynamically loads and returns the BasePlugin class."""
        base_plugin_path = os.path.join(self.plugin_dir, "base_plugin.py")
        if not os.path.exists(base_plugin_path):
            logger.error(
                f"❌ Critical: base_plugin.py not found at " f"{base_plugin_path}"
            )
            return None

        try:
            # Create a spec and module for base_plugin
            spec_base = importlib.util.spec_from_file_location(
                "plugins.base_plugin", base_plugin_path
            )
            base_module = importlib.util.module_from_spec(spec_base)

            # Insert into sys.modules to allow imports by name
            sys.modules["plugins.base_plugin"] = base_module
            spec_base.loader.exec_module(base_module)

            # Get the BasePlugin class object
            BasePlugin = getattr(base_module, "BasePlugin", None)
            if not BasePlugin:
                logger.error(
                    f"❌ Critical: 'BasePlugin' class not found in {base_plugin_path}"
                )
                return None
            logger.debug(f"✅ BasePlugin loaded successfully from {base_plugin_path}")
            return BasePlugin

        except Exception as e:
            logger.error(f"❌ Critical error loading BasePlugin: {e}", exc_info=True)
            return None

    async def load_plugins(self):
        """Scans the plugin directory and loads all valid plugins asynchronously."""
        self.plugins.clear()
        logger.debug("Attempting to load BasePlugin...")
        self._BasePluginClass = self._load_base_plugin()

        if not self._BasePluginClass:
            logger.critical("Cannot load plugins: BasePlugin is missing or invalid.")
            return

        logger.debug(f"Scanning plugin directory: {self.plugin_dir}")
        tasks = []
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and filename not in (
                "base_plugin.py",
                "__init__.py",
            ):
                path = os.path.join(self.plugin_dir, filename)
                logger.debug(f"Found potential plugin file: {filename}")
                tasks.append(asyncio.to_thread(self._load_single_plugin, path))

        await asyncio.gather(*tasks)

        # Load persisted plugin states and apply them
        self._load_plugin_states()

        logger.info(
            f"✅ Plugin loading complete. Found {len(self.plugins)} active plugins."
        )
        for p in self.plugins:
            enabled_status = "enabled" if getattr(p, "enabled", True) else "disabled"
            logger.info(
                f" -> Plugin Loaded: {p.get_name()} [{enabled_status}] (Keywords: {', '.join(p.get_keywords())})"
            )

    def _load_plugin_states(self):
        """Load persisted plugin enabled/disabled states from file."""
        states_file = os.path.join(
            os.path.dirname(__file__), "user_data", "plugin_states.json"
        )
        if not os.path.exists(states_file):
            logger.debug(
                "No plugin states file found, all plugins will be enabled by default"
            )
            return

        try:
            with open(states_file, "r") as f:
                states = _json.load(f)

            for plugin in self.plugins:
                plugin_name = plugin.get_name()
                if plugin_name in states:
                    plugin.enabled = states[plugin_name].get("enabled", True)
                    logger.debug(
                        f"Restored state for {plugin_name}: {'enabled' if plugin.enabled else 'disabled'}"
                    )
        except Exception as e:
            logger.error(f"Failed to load plugin states: {e}")

    def _load_single_plugin(self, path):
        """Dynamically loads a single Python file as a plugin module."""
        plugin_name = os.path.basename(path).replace(".py", "")
        module_name = f"plugins.{plugin_name}"
        logger.debug(f"Loading single plugin: {plugin_name} from {path}")

        # Check for manifest first to decide whether to isolate
        manifest = None
        manifest_path = os.path.splitext(path)[0] + ".json"
        try:
            if os.path.exists(manifest_path):
                with open(manifest_path, "r") as mf:
                    manifest = _json.load(mf)
                    logger.debug(f"Found manifest for {plugin_name}: {manifest_path}")
                    # Validate manifest against schema if available
                    schema_path = os.path.join(
                        os.path.dirname(__file__), "plugin_manifest_schema.json"
                    )
                    if _HAS_JSONSCHEMA and os.path.exists(schema_path):
                        try:
                            schema = _json.load(open(schema_path, "r"))
                            jsonschema.validate(instance=manifest, schema=schema)
                        except Exception as ve:
                            logger.error(
                                f"Plugin manifest validation failed for {plugin_name}: {ve}"
                            )
                            return
                    elif not _HAS_JSONSCHEMA:
                        logger.warning(
                            "jsonschema not installed; skipping manifest validation"
                        )
        except Exception as e:
            logger.warning(f"Failed to read manifest for {plugin_name}: {e}")

        # If manifest requests isolation, start a subprocess worker
        if manifest and manifest.get("isolate"):
            try:
                proxy = self._start_subprocess_plugin(path, manifest)
                if proxy:
                    proxy.manifest = manifest
                    proxy._plugin_path = path
                    proxy._restart_attempts = 0
                    # attempt initial health
                    try:
                        proxy.health_status = proxy.health()
                    except Exception as he:
                        proxy.health_status = {"status": "error", "detail": str(he)}
                    self.plugins.append(proxy)
                    return
            except Exception as e:
                logger.error(
                    f"Failed to start isolated plugin {plugin_name}: {e}", exc_info=True
                )
                # If subprocess isolation was requested but failed, don't load the plugin at all
                logger.error(
                    f"Skipping plugin {plugin_name} - isolation requested but failed"
                )
                return

        # Fallback: load plugin in-process as before (only for non-isolated plugins)
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = (
                module  # Add to sys.modules for proper imports within plugins
            )
            spec.loader.exec_module(module)
            logger.debug(f"Module {module_name} executed.")

            found_plugin_class = False
            # Iterate through all members of the module
            for name, obj in getmembers(module, isclass):
                logger.debug(
                    f"  Checking class: {name}, issubclass(obj, self._BasePluginClass) = {issubclass(obj, self._BasePluginClass)}, obj is not self._BasePluginClass = {obj is not self._BasePluginClass}"
                )
                if obj != self._BasePluginClass and issubclass(
                    obj, self._BasePluginClass
                ):
                    # Check for required methods (get_name, get_keywords, run)
                    if all(
                        hasattr(obj, method)
                        for method in ("get_name", "get_keywords", "run")
                    ):
                        logger.debug(
                            f"  Found valid plugin class {name}. Instantiating..."
                        )
                        plugin_instance = obj()

                        # attach path and manifest for lifecycle operations
                        plugin_instance._plugin_path = path
                        plugin_instance._restart_attempts = 0

                        # Attach manifest if present
                        if manifest:
                            try:
                                plugin_instance.manifest = manifest
                            except Exception:
                                pass

                        # Check if plugin should be sandboxed
                        should_sandbox = self.sandbox_manager is not None
                        if manifest:
                            should_sandbox = should_sandbox and manifest.get(
                                "isolate", True
                            )

                        if should_sandbox:
                            # Wrap in sandbox for isolation with config + overrides
                            isolation_mode = self.isolation_mode
                            if manifest:
                                isolation_mode = manifest.get(
                                    "isolation_mode", isolation_mode
                                )
                                if manifest.get("isolate_process"):
                                    isolation_mode = "process"
                            if isolation_mode not in ("thread", "process"):
                                isolation_mode = self.isolation_mode

                            sandbox_config = {
                                "timeout": (
                                    manifest.get("timeout", cfg.PLUGIN_DEFAULT_TIMEOUT)
                                    if manifest
                                    else cfg.PLUGIN_DEFAULT_TIMEOUT
                                ),
                                "memory_limit_mb": (
                                    manifest.get(
                                        "memory_limit_mb",
                                        cfg.PLUGIN_DEFAULT_MEMORY_LIMIT_MB,
                                    )
                                    if manifest
                                    else cfg.PLUGIN_DEFAULT_MEMORY_LIMIT_MB
                                ),
                                "cpu_time_limit": (
                                    manifest.get(
                                        "cpu_time_limit",
                                        cfg.PLUGIN_DEFAULT_CPU_TIME_LIMIT,
                                    )
                                    if manifest
                                    else cfg.PLUGIN_DEFAULT_CPU_TIME_LIMIT
                                ),
                                "allow_network": (
                                    manifest.get(
                                        "allow_network", cfg.PLUGIN_ALLOW_NETWORK
                                    )
                                    if manifest
                                    else cfg.PLUGIN_ALLOW_NETWORK
                                ),
                                "max_retries": (
                                    manifest.get("max_retries", cfg.PLUGIN_MAX_RETRIES)
                                    if manifest
                                    else cfg.PLUGIN_MAX_RETRIES
                                ),
                                "auto_escalate": self.auto_escalate,
                                "escalation_threshold": self.escalation_threshold,
                            }
                            if manifest and manifest.get("run_as_user"):
                                sandbox_config["run_as_user"] = manifest.get(
                                    "run_as_user"
                                )

                            sandboxed = self.sandbox_manager.register_plugin(
                                plugin_instance,
                                config=sandbox_config,
                                isolation_mode=isolation_mode,
                            )
                            logger.info(
                                "🔒 Plugin '%s' running in sandbox (%s)"
                                % (plugin_instance.get_name(), isolation_mode)
                            )

                            # Store reference to original plugin in sandbox wrapper
                            sandboxed._plugin_path = path
                            sandboxed._restart_attempts = 0
                            if manifest:
                                sandboxed.manifest = manifest

                            self.plugins.append(sandboxed)
                        else:
                            # Run in-process (no sandbox)
                            logger.warning(
                                f"⚠️ Plugin '{plugin_instance.get_name()}' running WITHOUT sandbox isolation"
                            )

                            # Evaluate health if available and attach status
                            try:
                                if hasattr(plugin_instance, "health") and callable(
                                    plugin_instance.health
                                ):
                                    plugin_instance.health_status = (
                                        plugin_instance.health()
                                    )
                                else:
                                    plugin_instance.health_status = {
                                        "status": "unknown"
                                    }
                            except Exception as _herr:
                                plugin_instance.health_status = {
                                    "status": "error",
                                    "detail": str(_herr),
                                }

                            self.plugins.append(plugin_instance)

                        found_plugin_class = True
                        break  # Only load the first found plugin class per file
                    else:
                        logger.warning(
                            f"  Class {name} in {path} is a BasePlugin subclass but missing required methods (get_name, get_keywords, run)."
                        )

            if not found_plugin_class:
                logger.warning(
                    f"No valid plugin class found in {path} (missing BasePlugin inheritance or required methods)."
                )

        except Exception as e:
            logger.error(f"❌ Error loading {path}: {e}", exc_info=True)

    def _start_subprocess_plugin(self, path, manifest=None):
        """Starts a plugin in a subprocess using `plugin_worker.py` and returns a proxy object."""
        worker = os.path.join(os.path.dirname(__file__), "plugin_worker.py")
        python = sys.executable or "python"
        # Prefer per-plugin venv python if available
        try:
            from . import plugin_env_manager as env_mgr

            name = os.path.splitext(os.path.basename(path))[0]
            candidate = Path(env_mgr.PLUGIN_VENV_ROOT) / name
            # Only use per-plugin venv when requirements are specified
            has_reqs = bool(manifest and manifest.get("requirements"))
            try:
                manifest_path = os.path.splitext(path)[0] + ".json"
                if has_reqs and os.path.exists(manifest_path):
                    try:
                        env_mgr.create_or_update(manifest_path)
                    except Exception as _e:
                        logger.warning(
                            f"Failed to create/update plugin venv for {name}: {_e}"
                        )
            except Exception:
                pass
            if has_reqs and candidate.exists():
                if os.name == "nt":
                    pybin = candidate / "Scripts" / "python.exe"
                else:
                    pybin = candidate / "bin" / "python"
                if pybin.exists():
                    cmd = [str(pybin), worker, path]
                else:
                    cmd = [python, worker, path]
            else:
                cmd = [python, worker, path]
        except Exception:
            cmd = [python, worker, path]

        # Network restrictions: respect global config and per-manifest allow_network
        allow_network = getattr(cfg, "PLUGIN_ALLOW_NETWORK", False) or (
            manifest and manifest.get("allow_network")
        )

        # Attempt to use `unshare -n` to drop network namespace if available and not allowed
        env = None
        if not allow_network:
            unshare_bin = shutil.which("unshare")
            if unshare_bin and os.geteuid() == 0:
                cmd = [unshare_bin, "-n"] + cmd
                logger.info(
                    f"Starting plugin without network using unshare: {' '.join(cmd[:3])}..."
                )
            else:
                # Remove common proxy envs and signal no-network via env var
                env = os.environ.copy()
                for k in list(env.keys()):
                    if (
                        k.lower().startswith("http_proxy")
                        or k.lower().startswith("https_proxy")
                        or k.lower().startswith("no_proxy")
                    ):
                        env.pop(k, None)
                env["KILO_PLUGIN_NO_NETWORK"] = "1"
                logger.info(
                    "Starting plugin subprocess with NO_NETWORK env (unshare not available or not root)"
                )

        logger.info(f"Starting isolated plugin subprocess: {' '.join(cmd[:3])}...")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # start a thread to read stderr and log it
        def _drain_stderr(p):
            for line in p.stderr:
                logger.error(f"[plugin-stderr] {line.rstrip()}")

        threading.Thread(target=_drain_stderr, args=(proc,), daemon=True).start()

        # Proxy object to interact with subprocess
        class Proxy:
            def __init__(self, proc, plugin_name="unknown"):
                self.proc = proc
                self.plugin_name = plugin_name
                self._lock = threading.Lock()
                self._id = 0
                self._responses = {}
                self._reader = threading.Thread(target=self._read_loop, daemon=True)
                self._reader.start()

            def _read_loop(self):
                for line in self.proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = _json.loads(line)
                        mid = msg.get("id")
                        if mid is not None:
                            self._responses[mid] = msg
                    except Exception:
                        logger.warning(f"Failed to parse plugin stdout line: {line}")

            def _call(self, method, params=None, timeout=5.0):
                params = params or {}
                with self._lock:
                    self._id += 1
                    mid = self._id
                    req = {"id": mid, "method": method, "params": params}
                    try:
                        logger.debug(
                            f"[{self.plugin_name}] Sending request: method={method}, id={mid}"
                        )
                        self.proc.stdin.write(_json.dumps(req) + "\n")
                        self.proc.stdin.flush()
                    except Exception as e:
                        logger.error(
                            f"[{self.plugin_name}] Failed to send to plugin subprocess: {e}"
                        )
                        raise RuntimeError(f"Failed to send to plugin subprocess: {e}")

                # wait for response
                start = time.time()
                while time.time() - start < timeout:
                    if mid in self._responses:
                        msg = self._responses.pop(mid)
                        logger.debug(
                            f"[{self.plugin_name}] Received response: method={method}, id={mid}"
                        )
                        if "error" in msg:
                            raise RuntimeError(msg.get("error"))
                        return msg.get("result")
                    time.sleep(0.01)

                logger.error(
                    f"[{self.plugin_name}] Timeout after {timeout}s waiting for {method} (id={mid}). Process alive: {self.proc.poll() is None}"
                )
                raise TimeoutError(f"Timeout waiting for plugin response to {method}")

            def get_name(self):
                return self._call("get_name")

            def get_keywords(self):
                return self._call("get_keywords")

            def run(self, query):
                return self._call("run", {"query": query}, timeout=60.0)

            def execute(self, query):
                """Execute method for plugin compatibility (calls run internally)"""
                return self._call("run", {"query": query}, timeout=60.0)

            def health(self):
                return self._call("health", {}, timeout=3.0)

            def stop(self):
                try:
                    return self._call("stop", {}, timeout=2.0)
                finally:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass

        # attach helper attributes to proxy before returning
        # (caller will set manifest and _plugin_path)
        plugin_name = os.path.splitext(os.path.basename(path))[0]
        return Proxy(proc, plugin_name)

    def start_all(self):
        """Starts the asynchronous background tasks for all loaded plugins."""
        logger.info("Starting all background tasks for loaded plugins.")
        with self._plugin_lock:
            plugins_copy = list(self.plugins)
        for p in plugins_copy:
            try:
                # Plugins may not have a background task
                if hasattr(p, "start_background_task") and callable(
                    p.start_background_task
                ):
                    thread = threading.Thread(
                        target=p.start_background_task, daemon=True
                    )
                    thread.start()
                    logger.info(f"Started background task for plugin: {p.get_name()}")
                else:
                    logger.debug(
                        f"Plugin {p.get_name()} does not have a start_background_task method."
                    )

            except Exception as e:
                logger.error(
                    f"Error starting background task for {p.get_name()}: {e}",
                    exc_info=True,
                )

    def get_plugin(self, name: str):
        """Retrieves a plugin instance by its exact name (thread-safe)."""
        with self._plugin_lock:
            for p in self.plugins:
                try:
                    if p.get_name() == name:
                        return p
                except Exception as e:
                    logger.warning(f"Error getting plugin name: {e}")
                    continue
        logger.debug(f"Plugin '{name}' not found.")
        return None

    def get_plugin_by_name(self, name: str):
        """Alias for get_plugin() - retrieves a plugin instance by name."""
        return self.get_plugin(name)

    # --- Watchdog / Health management ---
    def enable_watchdog(self):
        """Start the background watchdog thread if not already running."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            logger.debug("Watchdog already running.")
            return
        logger.info(f"Starting plugin watchdog (interval={self.health_interval}s)")
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True
        )
        self._watchdog_thread.start()

    def stop_watchdog(self):
        """Signal the watchdog to stop and wait for the thread to exit."""
        logger.info("Stopping plugin watchdog")
        self._watchdog_stop.set()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=2.0)

    def _watchdog_loop(self):
        while not self._watchdog_stop.is_set():
            try:
                for p in list(self.plugins):
                    name = None
                    try:
                        name = p.get_name()
                    except Exception:
                        name = getattr(p, "_plugin_path", "unknown")

                    # Try to obtain health
                    try:
                        if hasattr(p, "health") and callable(p.health):
                            status = p.health()
                        else:
                            status = getattr(p, "health_status", {"status": "unknown"})
                    except Exception as he:
                        status = {"status": "error", "detail": str(he)}

                    # Attach last known status
                    try:
                        p.health_status = status
                    except Exception:
                        pass

                    # If unhealthy or error, attempt restart for isolated plugins
                    st = (status or {}).get("status")
                    if st in ("error", "unhealthy", "down"):
                        logger.warning(
                            f"Watchdog: Plugin '{name}' reported unhealthy status: {status}"
                        )
                        # attempt restart
                        try:
                            self.restart_plugin(p)
                        except Exception as re:
                            logger.error(
                                f"Watchdog restart failed for '{name}': {re}",
                                exc_info=True,
                            )

            except Exception:
                logger.exception("Unexpected error in plugin watchdog loop")

            # Sleep until next round
            self._watchdog_stop.wait(self.health_interval)

    def restart_plugin(self, plugin_or_name):
        """Restart a plugin given the plugin object or its name.

        This will attempt to stop the existing plugin (if possible), remove it
        from the active list, and re-load it using its recorded _plugin_path.
        """
        # Resolve plugin object
        target = None
        if isinstance(plugin_or_name, str):
            target = self.get_plugin(plugin_or_name)
        else:
            target = plugin_or_name

        if not target:
            raise RuntimeError("Plugin not found for restart")

        path = getattr(target, "_plugin_path", None)
        name = None
        try:
            name = target.get_name()
        except Exception:
            name = str(path)

        # Try to stop it gracefully
        try:
            if hasattr(target, "stop") and callable(target.stop):
                target.stop()
        except Exception:
            logger.debug(f"Error when stopping plugin {name}, continuing to restart.")

        # Remove from list
        try:
            self.plugins = [p for p in self.plugins if p is not target]
        except Exception:
            pass

        if not path or not os.path.exists(path):
            raise RuntimeError(
                f"Cannot restart plugin {name}: original path not found: {path}"
            )

        # Increment restart attempts and fail after configured limit
        attempts = getattr(target, "_restart_attempts", 0) + 1
        target._restart_attempts = attempts
        if attempts > self.restart_retries:
            raise RuntimeError(
                f"Plugin {name} exceeded restart retries ({self.restart_retries})"
            )

        logger.info(
            f"Restarting plugin {name} (attempt {attempts}/{self.restart_retries})"
        )
        # Re-load the plugin (synchronous load of single plugin)
        try:
            self._load_single_plugin(path)
        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}", exc_info=True)
            raise

    def get_action(self, query: str):
        """
        Scans the user's query for keywords to determine which plugin to activate.
        Returns the first matching plugin instance or None.
        """
        query_lower = query.lower()
        for p in self.plugins:
            for k in p.get_keywords():
                if k in query_lower:
                    logger.info(
                        f"Tool match found: Activating plugin '{p.get_name()}' for query: '{query}'"
                    )
                    return p
        return None
