#!/usr/bin/env bash
set -euo pipefail

# Cleanup helper: finds large objects in git history and prints recommended commands.
# Run locally to see candidates. WARNING: history rewrite is destructive; coordinate
# with team and follow instructions in README_CLEANUP.md below.

THRESHOLD_BYTES=$((100 * 1024 * 1024)) # 100MB
OUT_DIR="/tmp/repo-largefiles-$(date +%s)"
mkdir -p "$OUT_DIR"
cd "$(git rev-parse --show-toplevel)"

echo "Scanning repository history for large blobs (>${THRESHOLD_BYTES} bytes)..."

git rev-list --objects --all > "$OUT_DIR/allfiles.txt"
# produce object info: type sha size path
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' < "$OUT_DIR/allfiles.txt" \
  | sort -k3 -n > "$OUT_DIR/objects_by_size.txt"

awk -v thresh=$THRESHOLD_BYTES '$3 > thresh { printf("%s %s %s\n", $2, $3, substr($0, index($0,$4))) }' "$OUT_DIR/objects_by_size.txt" > "$OUT_DIR/candidates.txt"

if [[ ! -s "$OUT_DIR/candidates.txt" ]]; then
  echo "No blobs larger than ${THRESHOLD_BYTES} bytes found in history."
  exit 0
fi

echo "Found the following candidate objects (sha size path):"
cat "$OUT_DIR/candidates.txt"

echo
echo "Suggested remediation options (read scripts/README_CLEANUP.md before running):"

echo "1) To remove blobs larger than threshold across history using git-filter-repo (recommended):"
printf "\n  git filter-repo --strip-blobs-bigger-than %d\n\n" "$THRESHOLD_BYTES"

echo "2) To migrate large files (matching patterns) to Git LFS (keeps history but moves files to LFS):"
echo "  git lfs migrate import --include='*.zip,*.bin,*.tar,chrome*'"

echo
echo "3) To create a targeted filter-repo invocation to remove the listed blobs by SHA (manual):"
echo "  # Example: git filter-repo --invert-paths --paths-from-file <(awk '{print $1}' $OUT_DIR/candidates.txt)"

echo
echo "Output saved to: $OUT_DIR"

exit 0
