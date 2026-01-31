# Compatibility shim: alias `services.gateway` to `gateway`
import importlib, sys
_mod = importlib.import_module('services.gateway')
sys.modules['gateway'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
