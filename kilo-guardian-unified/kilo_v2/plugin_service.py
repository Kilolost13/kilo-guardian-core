"""Plugin service functions moved out of server_core.

This module holds the business logic of plugin operations so the server
router code can be small and the app stays modular and testable.
"""

from typing import Any, Dict


def list_plugins(pm) -> Dict[str, Any]:
    """Return a summary of plugins.

    This function expects the caller to pass in a PluginManager-like
    object with a .plugins attribute.
    """
    plugins_out = []
    for p in pm.plugins:
        item = {
            "name": p.get_name(),
            "keywords": p.get_keywords(),
            "description": ", ".join(p.get_keywords()),
            "enabled": getattr(p, "enabled", True),
        }
        if hasattr(p, "manifest"):
            item["manifest"] = p.manifest
        if hasattr(p, "health_status"):
            item["health"] = p.health_status
        elif hasattr(p, "health") and callable(p.health):
            try:
                item["health"] = p.health()
            except Exception as e:
                item["health"] = {"status": "error", "detail": str(e)}

        plugins_out.append(item)
    return {"plugins": plugins_out}


def restart_plugin(pm, req) -> Dict[str, Any]:
    try:
        plugin = pm.get_plugin(req.name)
        if not plugin:
            return {"ok": False, "error": "Plugin not found"}
        pm.restart_plugin(plugin)
        return {"ok": True, "message": f"Restarted plugin {req.name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_plugin(pm, healer, req) -> Dict[str, Any]:
    try:
        plugin_name = req.plugin
        query = req.query
        if not plugin_name:
            return {"status": "error", "message": "Plugin name required"}
        plugin = pm.get_plugin(plugin_name)
        if not plugin:
            return {
                "status": "error",
                "message": f"Plugin '{plugin_name}' not found",
            }
        if hasattr(plugin, "execute") and callable(plugin.execute):
            result = plugin.execute(query)
        else:
            result = plugin.run(query)
        return {"status": "success", "plugin": plugin_name, "result": result}
    except Exception as e:
        if healer:
            healer.last_error = str(e)
        return {"status": "error", "message": str(e)}


def get_plugins_health(pm, sandbox_manager=None) -> Dict[str, Any]:
    summary = {
        "sandbox_enabled": False,
        "total": 0,
        "healthy": 0,
        "plugins": [],
    }
    sandbox_map = {}
    if sandbox_manager:
        summary["sandbox_enabled"] = True
        sandbox_map = sandbox_manager.sandboxed_plugins

    if pm is None:
        return summary
    for plugin in pm.plugins:
        try:
            name = plugin.get_name()
        except Exception:
            name = getattr(plugin, "_plugin_path", "unknown")
        record = {"name": name, "healthy": False}
        try:
            if hasattr(plugin, "health") and callable(plugin.health):
                record["healthy"] = bool(plugin.health().get("status") == "ok")
            else:
                record["healthy"] = True
        except Exception:
            record["healthy"] = False
        record["sandboxed"] = name in sandbox_map
        summary["plugins"].append(record)
        summary["total"] += 1
        if record["healthy"]:
            summary["healthy"] += 1
    return summary
