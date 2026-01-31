# Compatibility shim: alias `services.meds` to `meds`
import importlib, sys
_mod = importlib.import_module('services.meds')
sys.modules['meds'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
