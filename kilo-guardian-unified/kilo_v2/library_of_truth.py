# Compatibility shim: alias `services.library_of_truth` to `library_of_truth`
import importlib, sys
_mod = importlib.import_module('services.library_of_truth')
sys.modules['library_of_truth'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
