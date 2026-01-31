# Top-level shim to provide a common `db.get_engine` used by services
# Prefer `scripts.db.get_engine`, fall back to service-local helpers if needed.
import importlib, sys

_get_engine = None
try:
    mod = importlib.import_module('scripts.db')
    _get_engine = mod.get_engine
except Exception:
    try:
        mod = importlib.import_module('services.reminder.db')
        _get_engine = mod.get_engine
    except Exception:
        try:
            mod = importlib.import_module('services.financial.db')
            _get_engine = mod.get_engine
        except Exception:
            _get_engine = None

if _get_engine is None:
    raise ImportError('No db.get_engine implementation found; ensure `scripts.db` or service db modules are present')

# expose function
def get_engine(env_var_name: str, fallback_db_url: str):
    return _get_engine(env_var_name, fallback_db_url)

# Register module in sys.modules so `import db` resolves to this file
sys.modules['db'] = sys.modules.get('db') or sys.modules.setdefault('db', sys.modules.get(__name__))
