# Compatibility shim: alias `services.usb_transfer` to `usb_transfer`
import importlib, sys
_mod = importlib.import_module('services.usb_transfer')
sys.modules['usb_transfer'] = _mod
for _k in dir(_mod):
    if not _k.startswith('_'):
        globals()[_k] = getattr(_mod, _k)
