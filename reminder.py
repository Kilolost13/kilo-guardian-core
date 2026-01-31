# Compatibility shim: alias `services.reminder` to `reminder`
import importlib, sys
_mod = importlib.import_module('services.reminder')
sys.modules['reminder'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
