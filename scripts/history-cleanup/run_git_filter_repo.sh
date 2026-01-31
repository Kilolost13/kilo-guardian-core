#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <mirror-repo-path> <output-path>" >&2
  exit 2
fi
MIRROR_PATH=$1
OUTPUT_PATH=$2

# Safety: operate on mirror clone only
cd "$MIRROR_PATH"

# Example: remove blobs larger than 5MB and also paths in paths-to-remove.txt
# Create a temp workdir to avoid modifying the mirror in place
TMPDIR=$(mktemp -d)
git clone --no-hardlinks "$MIRROR_PATH" "$TMPDIR/working-repo"
cd "$TMPDIR/working-repo"

# Example filters: strip blobs larger than 5MB
git filter-repo --strip-blobs-bigger-than 5242880

# If you have a paths-to-remove.txt, use:
# git filter-repo --invert-paths --paths-from-file ../paths-to-remove.txt

# After modifications, verify, then write out a bare repo
mkdir -p "$OUTPUT_PATH"
cd ..
rm -rf "$OUTPUT_PATH" || true
git clone --mirror "$TMPDIR/working-repo" "$OUTPUT_PATH"

echo "Dry-run complete. Inspect $OUTPUT_PATH. Do NOT push to origin until validated."
