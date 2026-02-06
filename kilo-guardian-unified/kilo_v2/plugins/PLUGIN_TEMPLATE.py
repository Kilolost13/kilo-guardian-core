"""
🎯 Simple Plugin Template for Kilo Guardian

This is the EASIEST way to create a plugin for Kilo Guardian.
Just fill in the three required methods and you're done!

No serialization needed - just return Python objects.
The sandbox automatically handles everything.

Example: Weather Plugin
"""

import logging

from plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class SimpleTemplate(BasePlugin):
    """
    A simple plugin template showing the 3 things you need to implement.

    That's it! The sandbox handles:
    ✅ Timeouts (30 sec default)
    ✅ Crashes (isolated)
    ✅ Auto-escalation (if it breaks too much)
    ✅ Error handling (clean failures)
    """

    def get_name(self) -> str:
        """
        Return a short name for your plugin.
        This is what users see in the UI.

        Examples:
        - "Weather Forecast"
        - "Stock Price Tracker"
        - "Email Validator"
        """
        return "Simple Template"

    def get_keywords(self) -> list[str]:
        """
        Return words that trigger this plugin.
        When user's query contains any of these words,
        this plugin gets called.

        Examples:
        - ["weather", "forecast", "temperature"]
        - ["stock", "price", "ticker"]
        - ["email", "validate", "check"]
        """
        return ["template", "simple", "example"]

    def run(self, query: str) -> dict:
        """
        Your plugin's main logic.

        Args:
            query: What the user asked for

        Returns:
            A dict with your response (any structure you want!)

        Examples:
            return {
                "type": "weather",
                "temp": 72,
                "condition": "sunny"
            }

            return {
                "type": "stock",
                "symbol": "AAPL",
                "price": 150.25,
                "change": "+2.5%"
            }
        """
        logger.info(f"Template plugin received: {query}")

        return {
            "type": "response",
            "message": "Hello from template plugin!",
            "query": query,
        }


# ============================================================================
# 🚀 THAT'S ALL YOU NEED!
# ============================================================================
#
# Your plugin is now:
# ✅ Automatically isolated (crashes won't hurt Kilo)
# ✅ Monitored for health (auto-escalates if broken)
# ✅ Accessible via API
# ✅ Called when keywords match
#
# Optional: Add a background task
#
# def start_background_task(self):
#     """Optional: Start a background worker thread"""
#     # import threading
#     # threading.Thread(target=self._monitor_something, daemon=True).start()
#
# def health(self) -> dict:
#     """Optional: Report plugin health status"""
#     # return {"status": "ok", "detail": "Everything working"}
#
# ============================================================================
#
# 📝 TESTING YOUR PLUGIN:
#
# 1. Copy this file to: kilo_v2/plugins/my_plugin.py
# 2. Restart Kilo: systemctl restart kilo_guardian
# 3. Check it loaded: curl -H "X-API-Key: YOUR-KEY" \
#      http://localhost:8001/api/plugins | grep my_plugin
# 4. Test it: curl -X POST http://localhost:8001/api/plugins/execute \
#      -H "X-API-Key: YOUR-KEY" \
#      -H "Content-Type: application/json" \
#      -d '{"plugin":"my_plugin","query":"hello test"}'
#
# ============================================================================
#
# 🔧 REAL EXAMPLES:
#
# See these working plugins:
# - kilo_v2/plugins/finance_manager.py (complex, database access)
# - kilo_v2/plugins/vpn_client.py (system integration)
# - kilo_v2/plugins/briefing.py (API calls, multiple data sources)
#
# ============================================================================
#
# ⚡ SMART SANDBOX FEATURES:
#
# Thread Mode (Default):
#   ✅ Fast (no process overhead)
#   ✅ Simple (direct database access)
#   ✅ Easy debugging (full stack traces)
#   ⚠️ Slightly less isolated
#
# Process Mode (Auto-enabled on repeated crashes):
#   ✅ Maximum safety (plugin crashes = isolated process dies)
#   ✅ Automatic (switches if needed)
#   ⚠️ Slightly slower (process overhead)
#   ⚠️ Need JSON-serializable returns (usually ok)
#
# ============================================================================
