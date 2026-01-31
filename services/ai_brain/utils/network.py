"""Network gating helpers for air-gapped deployments.

Use the ALLOW_NETWORK environment variable to enable/disable outbound
network access at runtime. Defaults to disabled (False) so services will
not attempt external HTTP/API calls unless explicitly allowed.
"""
import os


def allow_network() -> bool:
    return os.environ.get("ALLOW_NETWORK", "false").lower() in ("1", "true", "yes")


def require_network_or_raise(reason: str = "network access required") -> None:
    if not allow_network():
        raise RuntimeError(f"network disabled: {reason}")
