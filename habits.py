# Compatibility shim: alias `services.habits` to `habits`
import importlib, sys
_mod = importlib.import_module('services.habits')
sys.modules['habits'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
