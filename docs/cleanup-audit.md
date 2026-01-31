# Cleanup Audit

This automatically generated audit highlights large files and suggested actions.

Large-file candidates (>10 MB):

- `.git/objects/pack/*.pack` (large git packs) — consider `git gc` and clean history if needed
- `microservice/frontend/kilo-react-frontend/node_modules/.cache/*` — remove from repo/history, add to `.gitignore`
- `.venv` native libs (OpenCV) — ensure virtualenv not tracked, move heavy deps to images
- `microservice/cam/yolov3-tiny.weights` — put models into LFS or external asset hosting
- `microservice/library_of_truth/books/*` — move to a `data/` or external storage

Proposed conservative steps:
- Add `.gitattributes` entries for LFS and add the LFS recommendation to `MAINTENANCE.md`.
- Move large docs to `docs/` and replace with references.
- Open a follow-up PR for history cleanup if you approve the candidate list.
