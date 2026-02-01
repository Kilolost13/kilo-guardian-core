# Re-export the canonical models defined at the package root to avoid duplicate table definitions.
# This ensures importing `ai_brain.models` returns the same classes used across
# the monorepo and prevents SQLModel/SQLAlchemy from re-defining tables.
from shared.models import *  # noqa: F401,F403

__all__ = []
try:
    from shared.models import __all__ as _root_all  # noqa: F401
    __all__ = list(_root_all)
except Exception:
    # Fallback; if importing fails in some contexts, leave __all__ empty.
    pass

# If the service defines local models in the sibling module `ai_brain/models.py`,
# load and re-export them here so imports like `from .models import SedentaryState`
# continue to work (avoids confusion between the package and the local module).
try:
    import importlib.util, pathlib
    base = pathlib.Path(__file__).parent.parent
    candidate = base / "models.py"
    if candidate.exists():
        spec = importlib.util.spec_from_file_location("ai_brain._local_models", str(candidate))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in ("SedentaryState", "CamReport", "MedRecord", "MedAdherence", "HabitEvent", "HabitProfile", "UserSettings", "SentReminder", "KiloResponse"):
            if hasattr(mod, name):
                globals()[name] = getattr(mod, name)
                if name not in __all__:
                    __all__.append(name)
except Exception:
    pass
