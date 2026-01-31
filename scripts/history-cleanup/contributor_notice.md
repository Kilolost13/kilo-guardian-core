# Contributor Notice — Planned History Cleanup

Date/Time (scheduled): **2025-12-27 10:00 UTC**

What will happen:
- We will perform a destructive history rewrite to remove large blobs (binaries) from the repository history and migrate necessary assets to Git LFS.
- A backup tag and branch have been created: `backup/history-cleanup-20251224` and tag `history-cleanup-backup-20251224`.

Impact for contributors:
- After the force-push, your local clones will be incompatible with the rewritten history.
- You will need to re-clone or follow these steps:
  1. Backup any local branches you need: `git branch -vv`
  2. Re-clone the repository: `git clone <repo-url>`
  3. Re-apply any local work on new branches from the current master

If you have PRs open, they will be updated against the new history; please re-open or rebase if necessary.

Contact & rollback:
- If anything goes wrong, we have a backup tag and branch and can revert the change if needed.
- Post any concerns on Issue #12.

Thank you for your attention — the maintenance window is short and planned. Please comment on Issue #12 if you need a different time or have critical objections.