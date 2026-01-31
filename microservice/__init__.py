"""Lightweight shim to make `import microservice.<service>` work in tests.
Attempts to load service modules from `services.<service>` and exposes them under
`microservice.<service>` so existing tests and imports keep working.
"""
import importlib

# List of expected service names to map
_SERVICES = [
    'cam', 'ai_brain', 'financial', 'gateway', 'reminder', 'library_of_truth',
    'usb_transfer', 'habits', 'meds', 'ml_engine', 'voice'
]

for name in _SERVICES:
    try:
        mod = importlib.import_module(f"services.{name}")
        globals()[name] = mod
        # also register fully qualified module name so importlib can find it
        import sys
        sys.modules[f"microservice.{name}"] = mod
    except Exception:
        # best effort, ignore missing services in test environments
        pass
