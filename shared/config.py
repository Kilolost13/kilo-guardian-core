"""
Kilo Guardian - Centralized Configuration

All service URLs, ports, and hardware IPs in one place.
Environment variables override defaults for flexibility.
"""
import os

# ==================== Hardware ====================
BEELINK_IP = os.getenv("BEELINK_IP", "192.168.68.60")
HP_IP = os.getenv("HP_IP", "192.168.68.56")
KILO_IP = os.getenv("KILO_IP", "192.168.68.66")  # Main access point

# ==================== LLM ====================
LLM_URL = os.getenv("LLM_URL", f"http://{BEELINK_IP}:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3-mini")

# ==================== K3s ====================
KUBECONFIG = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/hp-k3s-config"))
K3S_NAMESPACE = "kilo-guardian"

# ==================== Service Ports ====================
SERVICE_PORTS = {
    "habits": 9003,
    "meds": 9001,
    "reminder": 9002,
    "financial": 9005,
    "library": 9006,
    "ai_brain": 9004,
    "cam": 9007,
    "ml_engine": 9008,
    "voice": 9009,
    "socketio": 9010,
    "usb_transfer": 8006,
    "gateway": 8000,
    "ollama": 11434,
}

# ==================== Service URLs (K3s DNS) ====================
def get_service_url(service: str, use_k3s: bool = True) -> str:
    """Get URL for a Kilo service. Checks env var first, then K3s DNS, then localhost."""
    env_var = f"{service.upper()}_URL"
    url = os.getenv(env_var)
    if url:
        return url
    port = SERVICE_PORTS.get(service, 9000)
    if use_k3s:
        return f"http://kilo-{service}.{K3S_NAMESPACE}.svc.cluster.local:{port}"
    return f"http://localhost:{port}"

# ==================== Frontend ====================
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "30000"))
GATEWAY_NODEPORT = int(os.getenv("GATEWAY_NODEPORT", "30800"))

# ==================== Database ====================
DEFAULT_DB_DIR = os.getenv("KILO_DB_DIR", "/data")
