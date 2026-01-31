# Top-level alias module for centralized models
# All services should import from `microservice.models` when possible, but many modules
# historically do `from models import ...`. This alias ensures both names refer to
# the same module object and avoids duplicate SQLAlchemy table declarations.

from microservice import models as _mm
# Re-export everything
from microservice.models import *  # noqa: F401,F403

# Ensure that imports using either name map to the same module object
import sys
sys.modules['models'] = _mm
sys.modules['microservice.models'] = _mm
