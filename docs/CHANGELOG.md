# Changelog

## [Unreleased]

### Added
- Consolidated frontend improvements: tightened TypeScript types, fixed ESLint hook warnings, added CI workflow, merged enhanced Dashboard & Tablet UI features. (See PR #1)

### Fixed
- Jest/ESM issues for unit tests and runtime stability (regenerator-runtime added, axios transform); guarded DOM calls in tests.

### Notes
- Production build succeeds with non-blocking TypeScript parser warnings (consider pinning TS if desired).

---

Released commits:
- Merge PR #1 — "frontend: tighten types, fix ESLint hooks, add CI & integrate UI enhancements" (merged 2025-12-24)
