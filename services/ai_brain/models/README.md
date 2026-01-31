# Shared models

This package (`shared.models`) centralizes SQLModel model definitions used across microservices in this repository. Purpose:

- Provide a single source of truth for SQLModel classes (Transaction, ReceiptItem, Reminder, etc.).
- Prevent SQLModel/SQLAlchemy duplicate-declaration warnings that occur during pytest collection when multiple modules define the same models in the same process.
- Simplify cross-service imports and reduce drift when models evolve.

Usage

- Add new shared models to `shared/models/__init__.py` and import them from services:

  from shared.models import Transaction

- Keep service-specific business logic in each service's `main.py`. Only put model definitions in `shared.models` when they are shared or when centralizing improves test-time behavior.

Notes

- Services still run as separate containers in production; this centralization only affects the repository layout and how tests import models to avoid warnings.
- After all services import models from here, you can safely remove test-time warning suppressions in `conftest.py` (already done).
Note about `ai_brain` models

- The `ai_brain` service contains telemetry- and behavior-specific models in `services/ai_brain/models.py`. These models are intentionally left local to that service because they capture domain-specific events, user settings, and reminder telemetry which are not shared by other services. If in the future you decide any `ai_brain` model should be shared, move it into `shared/models/__init__.py` and update imports accordingly.
