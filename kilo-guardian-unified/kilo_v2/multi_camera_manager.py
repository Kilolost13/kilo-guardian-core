# Compatibility shim: alias `services.cam.multi_camera_manager` to top-level name
import importlib, sys
_mod = importlib.import_module('services.cam.multi_camera_manager')
sys.modules['multi_camera_manager'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
