import logging
from typing import Optional

from pydantic import BaseModel, Field

# Request models for API compatibility


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None


class PluginRestartRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


# Configure the logger for the base plugin
logger = logging.getLogger("BasePlugin")


class BasePlugin:
    """
    The abstract base class for all Guardian AI plugins.
    All plugins must inherit from this class and
    implement the required methods.
    """

    def __init__(self):
        # Base constructor can handle common setup if necessary
        logger.debug(f"Initializing BasePlugin for {self.__class__.__name__}")

    def get_name(self) -> str:
        """Returns the human-readable name of the plugin."""
        raise NotImplementedError("Plugins must implement the get_name() method.")

    def get_keywords(self) -> list[str]:
        """
        Returns a list of lowercase keywords that,
        if found in the user's query, will trigger this plugin.
        This is the primary tool-calling mechanism.
        """
        raise NotImplementedError("Plugins must implement the get_keywords() method.")

    def run(self, query: str) -> dict:
        """
        Executes the main functionality of the plugin
        based on the user's query. The return value should be a dictionary
        suitable for structured output.
        """
        raise NotImplementedError("Plugins must implement the run(query) method.")

    def start_background_task(self):
        """
        Optional: Start any long-running, asynchronous tasks
        (e.g., video monitoring, data fetching).
        This is run in a separate thread by the PluginManager.
        """
        pass  # Default implementation does nothing (no background task)

    def health(self) -> dict:
        """
        Optional health check for a plugin. Returns a small dict describing
        the plugin's current status. Default implementation reports 'ok'.
        Plugins with background tasks or external deps should override.
        """
        return {"status": "ok", "detail": "no health check implemented"}

    # Example Utility: Plugin-specific logging
    def log_info(self, message: str):
        """Helper for plugins to log messages with their name prepended."""
        logger.info(f"[{self.get_name()}] {message}")
