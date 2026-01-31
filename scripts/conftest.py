import os
import sys
from pathlib import Path


def pytest_sessionstart(session):
    # ensure imports work when tests run in isolation
    repo_root = str(Path(__file__).resolve().parent)  # microservice dir
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    # make admin endpoints open by default for integration tests
    prev = os.environ.get('ADMIN_TOKEN')
    session.config._prev_admin_token = prev
    # set to empty string so truthiness checks treat it as unset
    os.environ['ADMIN_TOKEN'] = ''


def pytest_sessionfinish(session, exitstatus):
    prev = getattr(session.config, '_prev_admin_token', None)
    if prev is None:
        os.environ.pop('ADMIN_TOKEN', None)
    else:
        os.environ['ADMIN_TOKEN'] = prev
# Set PYTHONWARNINGS early to silence SQLAlchemy SAWarning during test collection
import os
import sys
import warnings
from pathlib import Path

# Ensure SQLAlchemy SAWarning and FastAPI on_event deprecation are ignored as early as possible
# This avoids warnings emitted during module import/collection before pytest's warning filters apply.
prev_warnings = os.environ.get('PYTHONWARNINGS', '')
filters = ["ignore::sqlalchemy.exc.SAWarning", "ignore:.*on_event is deprecated:DeprecationWarning"]
if prev_warnings:
    filters.insert(0, prev_warnings)
os.environ['PYTHONWARNINGS'] = ",".join(filters)
# Reduce noisy SQLModel/SQLAlchemy warnings during test runs
try:
    from sqlalchemy.exc import SAWarning
    warnings.filterwarnings("ignore", category=SAWarning)
except Exception:
    pass


def pytest_sessionstart(session):
    # ensure imports work when tests run in isolation
    repo_root = str(Path(__file__).resolve().parent)  # microservice dir
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    # make admin endpoints open by default for integration tests
    prev = os.environ.get('ADMIN_TOKEN')
    session.config._prev_admin_token = prev
    # set to empty string so truthiness checks treat it as unset
    os.environ['ADMIN_TOKEN'] = ''

    # also silence FastAPI on_event deprecation noise in tests if present
    warnings.filterwarnings("ignore", message="on_event is deprecated")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    # suppress SQLModel/SQLAlchemy duplicate-declaration warnings which include this phrase
    warnings.filterwarnings("ignore", message=".*This declarative base already contains a class with the same class name.*")


def pytest_sessionfinish(session, exitstatus):
    prev = getattr(session.config, '_prev_admin_token', None)
    if prev is None:
        os.environ.pop('ADMIN_TOKEN', None)
    else:
        os.environ['ADMIN_TOKEN'] = prev


# --- Normalize package imports to avoid duplicate SQLAlchemy table declarations ---
# Ensure tests import a single authoritative models module and that
# importing via 'models' or 'microservice.models' refers to the same module.
try:
    import importlib, types
    repo_root = str(Path(__file__).resolve().parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    micro_dir = os.path.join(repo_root, 'microservice')
    if os.path.isdir(micro_dir) and micro_dir not in sys.path:
        sys.path.insert(0, micro_dir)
    # If 'microservice.models' is importable, set 'models' to point to it.
    try:
        ms_models = importlib.import_module('microservice.models')
        sys.modules['models'] = ms_models
    except Exception:
        # Fallback: if top-level 'models' exists, ensure 'microservice.models' maps to it.
        try:
            top_models = importlib.import_module('models')
            sys.modules['microservice.models'] = top_models
        except Exception:
            pass
except Exception:
    pass

# If the `microservice` package name is not present (files live at repo root),
# build a small synthetic package so imports like `microservice.cam` resolve.
try:
    if 'microservice' not in sys.modules:
        import types, importlib
        ms_pkg = types.ModuleType('microservice')
        for sub in ('cam', 'ai_brain', 'financial', 'gateway', 'reminder', 'library_of_truth', 'usb_transfer', 'habits'):
            try:
                mod = importlib.import_module(sub)
                setattr(ms_pkg, sub, mod)
                # also register fully qualified module name so importlib finds it
                sys.modules[f'microservice.{sub}'] = mod
            except Exception:
                pass
        sys.modules['microservice'] = ms_pkg
except Exception:
    pass
