# Contributing to Kilos Memory Microservices

Thank you for considering contributing! Please follow these guidelines:

## How to Contribute
- Fork the repository and create your branch from `main`.
- If you’ve added code, add tests.
- Ensure the test suite passes.
- Make sure your code lints.
- Submit a pull request with a clear description of your changes.

## CI and local integration notes

- The CI pipeline runs unit tests and an integration job via `docker compose up`.
- The integration job expects certain admin environment variables so tests can query admin endpoints. When running the integration stack locally or in CI, set the following env vars (CI creates a `.env` automatically for its integration runs):
	- `ADMIN_TOKEN` — simple token for admin endpoints (e.g. `ci-admin-token`).
	- `ADMIN_BASIC_USER` / `ADMIN_BASIC_PASS` — optional Basic Auth credentials for admin endpoints.
	- `ENABLE_NIGHTLY_MAINTENANCE` — set to `true` to enable the APScheduler nightly recategorization in the `financial` service.
	- `NIGHTLY_CRON` — cron spec for the scheduler (default `0 2 * * *`).

The CI integration job also validates that the `financial` service exposes a healthy `/admin/migration_status` endpoint before running integration tests.

CI secrets
-----------

For production-like integration runs, set the following GitHub Actions repository secrets so CI will inject them into the integration environment:

- `ADMIN_TOKEN` — admin token used by services (recommended)
- `ADMIN_BASIC_USER` and `ADMIN_BASIC_PASS` — optional basic auth credentials for admin endpoints

When the secrets are present CI will write a `.env` from them; otherwise CI falls back to safe defaults for ephemeral test runs.

Artifacts
---------

The integration job runs `scripts/check_services.py --json` and uploads the JSON results as an artifact named `service-check`. The frontend or monitoring tooling can download that artifact from the workflow run and ingest the JSON to display service readiness.

## Code Style
- Use Python 3.10+ and follow PEP8.
- Write clear, concise commit messages.

## Reporting Issues
- Use the issue template provided.
- Include as much detail as possible.

## Community
- Be respectful and inclusive.
