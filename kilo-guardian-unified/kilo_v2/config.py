# Kilo Core Configuration
# -----------------------

import logging
import os
from pathlib import Path

logger = logging.getLogger("KiloConfig")

# Detect if running under pytest or test harness so code can adapt (used by
# server_core to show a simple placeholder instead of serving built frontend
# during tests). This is a best-effort check using argv and environment.
try:
    import sys as _sys

    IS_TESTING = any("pytest" in str(a) for a in _sys.argv) or bool(
        os.environ.get("PYTEST_RUNNING") or os.environ.get("PYTEST_CURRENT_TEST")
    )
except Exception:
    IS_TESTING = False


# Helper to coerce boolean-like environment vars to True/False
def _env_to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes", "on")


# --- Load credentials from secure manager ---
try:
    from kilo_v2.credential_manager import credential_manager, get_credentials

    # Load and validate credentials
    _creds = get_credentials()
    credential_manager.log_status()

    # Export credentials for backward compatibility
    GEMINI_API_KEY = _creds.gemini_api_key
    KILO_API_KEY = _creds.kilo_api_key

    # Google OAuth paths
    GOOGLE_CREDENTIALS_FILE = _creds.google_credentials_path
    GOOGLE_TOKEN_FILE = _creds.google_token_path

    # External API keys
    OPENWEATHER_API_KEY = _creds.openweather_api_key or ""
    NEWS_API_KEY = _creds.news_api_key or ""

    # Production settings
    ENVIRONMENT = _creds.environment
    IS_PRODUCTION = _creds.is_production()
    DOMAIN = _creds.domain
    SESSION_SECRET = _creds.session_secret

    # SMTP settings
    SMTP_HOST = _creds.smtp_host
    SMTP_PORT = _creds.smtp_port
    SMTP_USER = _creds.smtp_user
    SMTP_PASSWORD = _creds.smtp_password
    ALERT_EMAIL = _creds.alert_email

    # Stripe settings
    STRIPE_SECRET_KEY = _creds.stripe_secret_key or ""
    STRIPE_WEBHOOK_SECRET = _creds.stripe_webhook_secret or ""

except ImportError:
    logger.warning("credential_manager not available, falling back to direct env vars")

    # Fallback to direct environment variable access
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    # Detect when running under pytest to give tests a predictable default
    # key. This avoids requiring tests to manage environment state before
    # importing the config module.
    try:
        import sys as _sys

        _running_pytest = any("pytest" in str(a) for a in _sys.argv)
    except Exception:
        _running_pytest = False

    if _running_pytest or os.environ.get("PYTEST_RUNNING"):
        _default_key = os.environ.get("KILO_API_KEY", "test-api-key")
    else:
        # Fallback to None if the environment variable is not set.
        # A hardcoded key is a security risk. The application must handle a missing key gracefully.
        _default_key = os.environ.get("KILO_API_KEY")

    KILO_API_KEY = _default_key

    GOOGLE_CREDENTIALS_FILE = None
    GOOGLE_TOKEN_FILE = None

    OPENWEATHER_API_KEY = ""
    NEWS_API_KEY = ""

    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT.lower() in ("production", "prod")
    DOMAIN = None
    SESSION_SECRET = None

    SMTP_HOST = None
    SMTP_PORT = 587
    SMTP_USER = None
    SMTP_PASSWORD = None
    ALERT_EMAIL = None

    STRIPE_SECRET_KEY = ""
    STRIPE_WEBHOOK_SECRET = ""

    if not KILO_API_KEY and not IS_TESTING:
        logger.warning(
            "KILO_API_KEY environment variable not set. Some features may be disabled."
        )

# --- Gemini Model Name ---
# Default model name can be overridden via env var `GEMINI_MODEL_NAME`.
GEMINI_MODEL_NAME = os.environ.get(
    "GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-09-2025"
)

# Whether to enable remote LLM integrations (Gemini/OpenAI). When False,
# the system uses a local-only reasoning model and no external LLM calls
# will be attempted.
USE_REMOTE_LLM = _env_to_bool(os.environ.get("USE_REMOTE_LLM", "false"))

# Backwards compatibility: Local reasoning-only flag
LOCAL_REASONING_ONLY = not USE_REMOTE_LLM

# --- Local LLM Settings ---
# Path to the GGUF model file for the local LLM.
# This is used as a fallback for conversational AI when plugins can't handle a query.
# Using Phi-3-mini for production-level intelligence
LOCAL_LLM_MODEL_PATH = "/home/kilo/Desktop/getkrakaen/kilos-bastion-ai/kilo_v2/models/Phi-3-mini-4k-instruct-q4.gguf"

# --- System Settings ---

# Server identification and naming
SERVER_NAME = "Kilo Guardian Backend API"
SERVER_DESCRIPTION = "Kilo Bastion AI - Core API Server"

# The port the FastAPI server will run on (can be overridden by env var)
SERVER_PORT = int(os.environ.get("KILO_SERVER_PORT", 8000))

# Directory for long-term vector storage (FAISS index)
INDEX_STORAGE_PATH = os.environ.get("INDEX_STORAGE_PATH", "kilo_memory_index")

# Directory for memory logs and other persistent data
DATA_DIR = os.environ.get("DATA_DIR", "kilo_data")


# --- Helper function for boolean environment variables ---
def _env_to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes", "on")


# --- Plugin runtime settings ---
# How often (seconds) to poll plugin health
PLUGIN_HEALTH_INTERVAL = int(os.environ.get("PLUGIN_HEALTH_INTERVAL", 20))
# How many times to attempt restart for a plugin before giving up
PLUGIN_RESTART_RETRIES = int(os.environ.get("PLUGIN_RESTART_RETRIES", 3))
# Directory where per-plugin virtualenvs will be created (medium term)
PLUGIN_VENV_DIR = os.environ.get(
    "PLUGIN_VENV_DIR", os.path.join(os.path.dirname(__file__), "plugin_venvs")
)

# --- Smart Hybrid Plugin Sandbox System ---
# Enable sandbox isolation for plugins (strongly recommended for security)
# Default: enabled in production, disabled in development/testing
_sandbox_env = os.environ.get("PLUGIN_SANDBOX_ENABLED")
if _sandbox_env is not None:
    PLUGIN_SANDBOX_ENABLED = _env_to_bool(_sandbox_env)
elif IS_TESTING:
    PLUGIN_SANDBOX_ENABLED = False
else:
    PLUGIN_SANDBOX_ENABLED = IS_PRODUCTION if "IS_PRODUCTION" in dir() else False

# Isolation: "thread" (fast, easy dev) or "process" (maximum safety)
PLUGIN_ISOLATION_MODE = os.environ.get("PLUGIN_ISOLATION_MODE", "thread").lower()
if PLUGIN_ISOLATION_MODE not in ("thread", "process"):
    logger.warning(
        "Invalid PLUGIN_ISOLATION_MODE '%s', defaulting to 'thread'"
        % PLUGIN_ISOLATION_MODE
    )
    PLUGIN_ISOLATION_MODE = "thread"

# Sandbox resource and retry settings
PLUGIN_DEFAULT_TIMEOUT = int(os.environ.get("PLUGIN_DEFAULT_TIMEOUT", "30"))
PLUGIN_DEFAULT_MEMORY_LIMIT_MB = int(
    os.environ.get("PLUGIN_DEFAULT_MEMORY_LIMIT_MB", "512")
)
PLUGIN_DEFAULT_CPU_TIME_LIMIT = int(
    os.environ.get("PLUGIN_DEFAULT_CPU_TIME_LIMIT", "60")
)
PLUGIN_MAX_RETRIES = int(os.environ.get("PLUGIN_MAX_RETRIES", "3"))

# Auto-escalation: if plugin fails too many times, move to process isolation
PLUGIN_AUTO_ESCALATE_ON_FAILURE = _env_to_bool(
    os.environ.get("PLUGIN_AUTO_ESCALATE_ON_FAILURE", "true")
)
PLUGIN_FAILURE_THRESHOLD_FOR_ESCALATION = int(
    os.environ.get("PLUGIN_FAILURE_THRESHOLD_FOR_ESCALATION", "3")
)

# Whether plugins are allowed network access by default. Individual plugin
# manifests may include `allow_network: true` to opt in, but the global
# default is controlled by this env var (false by default in production).
PLUGIN_ALLOW_NETWORK = _env_to_bool(os.environ.get("PLUGIN_ALLOW_NETWORK", "false"))

# Force SQLAlchemy usage (disable sqlite fallback paths).
# Set to 'true' to strictly use SQLAlchemy engine only.
FORCE_SQL_ALCHEMY = _env_to_bool(os.environ.get("FORCE_SQL_ALCHEMY", "true"))

# --- Plugin Settings ---

# List of plugins to ignore (use the filename without .py,
# e.g., ["google_services"])
BLACKLISTED_PLUGINS = []

# --- Security Camera Settings (For security_camera.py plugin) ---

# Camera index (0 is usually the built-in webcam)
CAMERA_INDEX = 0

# Frames per second for background video analysis
CAMERA_FPS = 5

# Resolution (width, height)
CAMERA_RESOLUTION = (640, 480)

# --- Caddy / Logging Integration ---
# Path to Caddy JSON access log for tail-based intrusion detection.
# Can be overridden by env var CADDY_LOG_PATH.
CADDY_LOG_PATH = os.environ.get(
    "CADDY_LOG_PATH",
    "/home/kilo/Desktop/getkrakaen/kilos-bastion-ai/logs/caddy_access.log",
)

# Enable network honeypot decoy service (experimental).
# Override via ENABLE_NETWORK_HONEYPOT.
ENABLE_NETWORK_HONEYPOT = _env_to_bool(
    os.environ.get("ENABLE_NETWORK_HONEYPOT", "false")
)
NETWORK_HONEYPOT_PORT = int(os.environ.get("NETWORK_HONEYPOT_PORT", 8888))

# --- IP Enrichment Settings ---
# Optional passive IP enrichment (GeoIP/ASN). Disabled by default to avoid
# external calls. Set ENABLE_IP_ENRICHMENT=true to activate. If enabled and
# IP_ENRICHMENT_API_KEY provided, provider-specific enrichment
# (e.g., ipinfo, ipdata) may be attempted. Otherwise a local
# passive stub (reverse DNS + private network classification) is returned.
ENABLE_IP_ENRICHMENT = _env_to_bool(os.environ.get("ENABLE_IP_ENRICHMENT", "false"))
IP_ENRICHMENT_PROVIDER = os.environ.get(
    "IP_ENRICHMENT_PROVIDER", "stub"
)  # stub | ipinfo | ipdata | ipapi
IP_ENRICHMENT_API_KEY = os.environ.get("IP_ENRICHMENT_API_KEY", "")

if (
    ENABLE_IP_ENRICHMENT
    and not IP_ENRICHMENT_API_KEY
    and IP_ENRICHMENT_PROVIDER != "stub"
):
    logger.warning(
        ("IP enrichment enabled but no API key supplied; " "falling back to stub mode.")
    )

# --- Stripe Payment Settings ---
# Stripe API keys for subscription management
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Stripe price IDs for each tier
STRIPE_PRICE_IDS = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", "price_pro_monthly"),
    "business": os.environ.get("STRIPE_PRICE_BUSINESS", "price_business_monthly"),
}

if not STRIPE_SECRET_KEY:
    logger.info("Stripe not configured. License monetization disabled.")

# --- Meshtastic Integration Settings ---
# Optional mesh radio tracking via Meshtastic
MESHTASTIC_ENABLE = os.environ.get("MESHTASTIC_ENABLE", "false").lower() == "true"
MESHTASTIC_HOST = os.environ.get("MESHTASTIC_HOST", "localhost")
try:
    MESHTASTIC_PORT = int(os.environ.get("MESHTASTIC_PORT", "2960"))
except ValueError:
    MESHTASTIC_PORT = 2960
MESHTASTIC_SERIAL = os.environ.get("MESHTASTIC_SERIAL", "")

# --- Drone Control Settings ---
# Optional autonomous drone control with simulation-first default
DRONE_ENABLE = os.environ.get("DRONE_ENABLE", "false").lower() == "true"
DRONE_SIMULATION = os.environ.get("DRONE_SIMULATION", "true").lower() == "true"
DRONE_ENDPOINT = os.environ.get("DRONE_ENDPOINT", "udp://:14540")
DRONE_SAFETY_REQUIRE_CONFIRMATION = (
    os.environ.get("DRONE_SAFETY_REQUIRE_CONFIRMATION", "true").lower() == "true"
)
try:
    DRONE_MAX_ALT = float(os.environ.get("DRONE_MAX_ALT", "50.0"))
except ValueError:
    DRONE_MAX_ALT = 50.0
# Optional geofence polygon/bbox JSON string; parse where needed
DRONE_GEOFENCE = os.environ.get("DRONE_GEOFENCE", "")

# --- Drone Video Streaming Settings ---
# Enable FPV video streaming from drone camera
DRONE_VIDEO_ENABLE = os.environ.get("DRONE_VIDEO_ENABLE", "false").lower() == "true"
try:
    DRONE_CAMERA_INDEX = int(os.environ.get("DRONE_CAMERA_INDEX", "0"))
except ValueError:
    DRONE_CAMERA_INDEX = 0
try:
    DRONE_VIDEO_QUALITY = int(os.environ.get("DRONE_VIDEO_QUALITY", "80"))
except ValueError:
    DRONE_VIDEO_QUALITY = 80
try:
    DRONE_VIDEO_FPS = int(os.environ.get("DRONE_VIDEO_FPS", "30"))
except ValueError:
    DRONE_VIDEO_FPS = 30

# --- Drone Manual Control Settings ---
# Enable manual RC override via API/gamepad
DRONE_MANUAL_CONTROL_ENABLE = (
    os.environ.get("DRONE_MANUAL_CONTROL_ENABLE", "false").lower() == "true"
)
try:
    DRONE_DEADMAN_TIMEOUT = float(os.environ.get("DRONE_DEADMAN_TIMEOUT", "2.0"))
except ValueError:
    DRONE_DEADMAN_TIMEOUT = 2.0

# --- Google Maps Integration ---
# API key for Google Maps JavaScript API (required for mesh tracker UI)
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# --- Obstacle Avoidance Settings ---
# Enable pre-flight path collision detection against obstacle database
DRONE_OBSTACLE_CHECK_ENABLE = (
    os.environ.get("DRONE_OBSTACLE_CHECK_ENABLE", "false").lower() == "true"
)
