# Compatibility shim: alias `services.ai_brain` module to `ai_brain` to avoid duplicate imports
import importlib, sys
_mod = importlib.import_module('services.ai_brain')
# ensure both module names point to the same module object
sys.modules['ai_brain'] = _mod
# Export public symbols
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
