# Repo large-file cleanup plan

This document explains how to identify and safely remediate large files present in the Git history that are preventing pushes due to GitHub's 100MB limit.

Overview
- We found a large Chrome binary (or similar) earlier that caused `pre-receive` hook rejections.
- Two remediation options:
  1. Remove the blobs from history using `git filter-repo` (recommended for unwanted files).
  2. Migrate large files to Git LFS using `git lfs migrate` (recommended if the files must remain available but shouldn't be in normal git history).

Safety & workflow
1. Create a new branch that will be used to perform the rewrite (e.g., `cleanup/remove-large-blobs`).
2. Run the `scripts/cleanup_large_files.sh` script to list and examine candidate blobs.
3. If removing unwanted files, run the filter-repo command (example):
   - `git filter-repo --strip-blobs-bigger-than 100M`
   - or for targeted removals: `git filter-repo --invert-paths --paths-from-file <(awk '{print $3}' /tmp/repo-largefiles-*/candidates.txt)`
4. If migrating to LFS:
   - `git lfs migrate import --include='*.zip,*.bin,chrome*'`
   - Verify binaries are now LFS pointers and pushes are accepted.
5. Force-push the rewritten branches and coordinate with the team to rebase their branches (documented in PR).

Communication & coordination
- Rewriting history is disruptive: open a PR with the proposed changes and tag all contributors who may be affected.
- Provide a short window where all contributors freeze new branch pushes or accept rebase instructions.

If you want, I can prepare a draft PR with a runnable `scripts/cleanup_large_files.sh`, a proposed `filter-repo` command invocation, and a checklist in the PR description to guide maintainers during the cleanup window.