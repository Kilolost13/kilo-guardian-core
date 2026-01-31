# History cleanup scripts & plan

This directory contains scripts and instructions to safely test and execute a history rewrite to remove large blobs and migrate assets to Git LFS.

Important: DO NOT run any destructive commands against `origin` until the plan is reviewed and a scheduled time is agreed upon.

Steps:
1. Create a mirror clone: `git clone --mirror https://github.com/Kilolost13/kilo-ai-memory-assistant.git /tmp/cleanup-mirror`
2. Prepare a `paths-to-remove.txt` listing files or directories to delete from history (one per line), and a `patterns-to-lfs.txt` describing files to move to LFS.
3. Run the test cleanup script: `./run_git_filter_repo.sh /tmp/cleanup-mirror /tmp/cleanup-output` — this will perform a dry-run and write the resulting repo to `/tmp/cleanup-output`.
4. Validate the resulting repository locally (run `npm test`, `npx tsc --noEmit`, pytest, etc.)
5. If validated, schedule the force-push window and push the cleaned mirror to `origin` (force push). Ensure everyone is notified to re-clone.

See `run_git_filter_repo.sh` for an example invocation and template commands.
