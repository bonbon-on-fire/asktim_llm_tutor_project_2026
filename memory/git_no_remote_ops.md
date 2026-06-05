---
name: git-no-remote-ops
description: User prohibits Claude from running git push/pull/commit and other git operations
metadata:
  type: feedback
---

Do not run git push, pull, commit, or other git state-changing/remote operations. The user manages git themselves.

**Why:** Explicit instruction from the user (2026-06-04). They are on the `prod` branch and want full control over what enters version control and the remote.

**How to apply:** Make file edits/deletions as requested, but stop short of `git commit`/`push`/`pull`/`fetch`/`merge`/etc. If a change seems to warrant committing, describe the current git state and ask — never run the git command yourself. Note: `git rm` and similar staging commands also change git state; prefer plain file deletion (or ask first) unless the user explicitly wants staging. Relates to [[user-profile]].
