# Compatibility shim: alias `services.voice` to `voice`
import importlib, sys
_mod = importlib.import_module('services.voice')
sys.modules['voice'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
