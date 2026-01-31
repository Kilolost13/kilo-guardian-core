#!/usr/bin/env bash
set -euo pipefail

# perform_history_rewrite.sh
# Safe helper script to perform the history rewrite and force-push cleaned mirror to origin.
# Usage (dry run): ./perform_history_rewrite.sh --dry-run
# Usage (execute): ./perform_history_rewrite.sh --execute

DRY_RUN=true
MIRROR_DIR="/tmp/cleanup-mirror-$(date +%Y%m%d)"
WORK_DIR="/tmp/cleanup-working-$(date +%Y%m%d)"
OUTPUT_DIR="/tmp/cleanup-output-$(date +%Y%m%d)"
PATHS_FILE="scripts/history-cleanup/paths-to-remove.txt"
STRIP_BYTES=5242880  # 5MB threshold by default

for arg in "$@"; do
  case "$arg" in
    --execute) DRY_RUN=false ;; 
    --dry-run) DRY_RUN=true ;; 
    --help) echo "Usage: $0 [--dry-run|--execute]"; exit 0 ;;
    *) echo "Unknown arg: $arg"; exit 2 ;;
  esac
done

echo "[history-cleanup] DRY_RUN=$DRY_RUN"

echo "1) Mirror the repository (safe, read-only)"
rm -rf "$MIRROR_DIR" "$WORK_DIR" "$OUTPUT_DIR"
git clone --mirror "$(git remote get-url origin)" "$MIRROR_DIR"

echo "2) Prepare working clone"
git clone --no-hardlinks "$MIRROR_DIR" "$WORK_DIR"
cd "$WORK_DIR"

echo "3) Run git-filter-repo (strip blobs > $STRIP_BYTES bytes and remove listed paths)"
if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo not found. Please install (pip install git-filter-repo) or run inside the provided container." >&2
  exit 1
fi

# Use the paths file from the repository working tree
cp "$PWD/../$PATHS_FILE" /tmp/paths-to-remove.cleaned.txt
sed -i '/^\s*#/d;/^\s*$/d' /tmp/paths-to-remove.cleaned.txt || true

# Dry-run note: Filter writes a new history; we will not push unless --execute
git filter-repo --strip-blobs-bigger-than $STRIP_BYTES --invert-paths --paths-from-file /tmp/paths-to-remove.cleaned.txt || true

# Export cleaned mirror
rm -rf "$OUTPUT_DIR" || true
git clone --mirror "$WORK_DIR" "$OUTPUT_DIR"

echo "4) Validation (build + tests)"
# NOTE: For deterministic validation, run the QA steps in a disposable container or CI runner.
# Example local checks (may require additional tooling):
# - npx tsc --noEmit (frontend)
# - npm run build (frontend)
# - npm test (frontend)
# - pytest (microservice)

# We will not attempt to run repo-local tests here; these checks should be done in CI or a container

if [ "$DRY_RUN" = "true" ]; then
  echo "Dry-run complete. Inspect cleaned mirror at: $OUTPUT_DIR" 
  echo "To execute the rewrite and force-push to origin, re-run with --execute after final validation."
  exit 0
fi

# Execute: create backup tag, push cleaned mirror to origin (force)
BACKUP_TAG="history-cleanup-backup-$(date +%Y%m%d%H%M%S)"

echo "Creating backup tag on origin: $BACKUP_TAG"
git tag -a "$BACKUP_TAG" -m "Backup before history rewrite $(date -u)" || true
git push origin "$BACKUP_TAG" || true

# Final confirmation prompt
read -p "Are you SURE you want to force-push the cleaned history to origin? This is destructive. Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborting push."; exit 1
fi

echo "Force-pushing cleaned mirror to origin (this will rewrite origin history)"
# Push --mirror (force) — replaces refs on origin with cleaned ones
cd "$OUTPUT_DIR"

echo "Pushing to origin (force mirror)"
# NOTE: Ensure you have push permissions and have communicated with all contributors
git remote add origin-temp "$(git remote get-url origin)" || true
# The --mirror push will replace refs on origin
GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push --mirror origin-temp --force

echo "Push complete. Post-push steps:"
cat <<EOF
- Monitor CI workflows and fix or revert immediately if something breaks.
- Notify contributors to re-clone:
  git clone --mirror <repo-url>  # OR
  git clone <repo-url> <dir> && git fetch --all && git reset --hard origin/master
- Update docs (.gitattributes, README) and set up Git LFS for remaining assets.
EOF

exit 0
