# Compatibility shim: alias `services.ml_engine` to `ml_engine`
import importlib, sys
_mod = importlib.import_module('services.ml_engine')
sys.modules['ml_engine'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
