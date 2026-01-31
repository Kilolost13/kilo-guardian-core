# Bridge package to expose services.integration as microservice.integration for tests
try:
    from services.integration import test_runner
    # re-export
    __all__ = ['test_runner']
except Exception:
    # Best-effort: keep module importable even if services package not available
    __all__ = []
