#!/usr/bin/env python3
"""
Simple plugin worker to run a single plugin in an isolated subprocess.
Parent process communicates over stdin/stdout using JSON-lines messages.

Usage: python plugin_worker.py /absolute/path/to/plugin_file.py

Supported messages (JSON per line):
{ "id": 1, "method": "run", "params": {"query": "..."} }
{ "id": 2, "method": "health", "params": {} }
{ "id": 3, "method": "get_name", "params": {} }
{ "id": 4, "method": "get_keywords", "params": {} }

Responses are JSON objects with the same id: {"id": 1, "result": ...} or {"id":1, "error": "..."}
"""
import importlib.util
import json
import os
import sys
import traceback


def send(obj):
    sys.stdout.write(json.dumps(obj, default=str) + "\n")
    sys.stdout.flush()


def main(plugin_path):
    try:
        # Ensure the plugin can import `from plugins.base_plugin import BasePlugin`
        plugin_dir = os.path.dirname(plugin_path)
        base_plugin_path = os.path.join(plugin_dir, "base_plugin.py")
        try:
            if os.path.exists(base_plugin_path):
                spec_base = importlib.util.spec_from_file_location(
                    "plugins.base_plugin", base_plugin_path
                )
                base_module = importlib.util.module_from_spec(spec_base)
                sys.modules["plugins.base_plugin"] = base_module
                spec_base.loader.exec_module(base_module)
        except Exception:
            # If base plugin fails to load here, the plugin import below will likely fail too.
            pass
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        spec = importlib.util.spec_from_file_location("isolated_plugin", plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find first BasePlugin subclass
        from plugins.base_plugin import BasePlugin

        plugin_cls = None
        for name, obj in module.__dict__.items():
            try:
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                ):
                    plugin_cls = obj
                    break
            except Exception:
                continue

        if not plugin_cls:
            send({"id": None, "error": "No BasePlugin subclass found in plugin"})
            return 1

        instance = plugin_cls()

    except Exception as e:
        send(
            {
                "id": None,
                "error": f"Failed to load plugin: {e}",
                "trace": traceback.format_exc(),
            }
        )
        return 1

    # main loop: read JSON lines from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            mid = msg.get("id")
            method = msg.get("method")
            params = msg.get("params", {}) or {}

            if method == "run":
                q = params.get("query", "")
                try:
                    res = instance.run(q)
                    send({"id": mid, "result": res})
                except Exception as e:
                    send({"id": mid, "error": str(e), "trace": traceback.format_exc()})
            elif method == "health":
                try:
                    res = (
                        instance.health()
                        if hasattr(instance, "health")
                        else {"status": "unknown"}
                    )
                    send({"id": mid, "result": res})
                except Exception as e:
                    send({"id": mid, "error": str(e), "trace": traceback.format_exc()})
            elif method == "get_name":
                try:
                    send({"id": mid, "result": instance.get_name()})
                except Exception as e:
                    send({"id": mid, "error": str(e), "trace": traceback.format_exc()})
            elif method == "get_keywords":
                try:
                    send({"id": mid, "result": instance.get_keywords()})
                except Exception as e:
                    send({"id": mid, "error": str(e), "trace": traceback.format_exc()})
            elif method == "stop":
                send({"id": mid, "result": "stopping"})
                break
            else:
                send({"id": mid, "error": f"Unknown method: {method}"})

        except Exception as e:
            send(
                {
                    "id": None,
                    "error": f"Invalid request: {e}",
                    "trace": traceback.format_exc(),
                }
            )

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: plugin_worker.py /path/to/plugin.py", file=sys.stderr)
        sys.exit(2)
    plugin_path = sys.argv[1]
    sys.exit(main(plugin_path))
