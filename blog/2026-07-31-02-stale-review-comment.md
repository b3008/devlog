---
type: "Devlog Entry"
title: "Closing a stale review comment without touching the code"
date: 2026-07-31
timestamp: 2026-07-31T09:36:18
tags: [bug-fix, documentation]
description: "A PR review asked for the sentinel version stamp to be regenerated, but the branch already carried the matching v0.6.0 stamp, so the right fix was to verify the current files and stop without editing anything."
---

## What changed

No product code changed. The work in this turn was deciding whether the linked PR review comment still described reality.

I checked the exact files the comment was about:

- `CLAUDE.md`
- `pyproject.toml`
- `src/devlog_cli/_version.py`

All three already agree on `0.6.0`, and the sentinel block in `CLAUDE.md` is stamped `v0.6.0`, so the requested regeneration had already effectively happened on the branch.

## Why it matters

This is a small but important devlog case: the decision was the work.

A stale review comment can easily provoke a pointless "fix" that only churns generated files or rewrites already-correct metadata. Here the right outcome was to confirm the branch state, explain that the comment was already satisfied, and avoid touching anything else.

## How it works

The review comment was about drift detection, which depends on the sentinel stamp matching the shipped version. Verifying that meant comparing the installed marker against the two canonical version sources:

```text
CLAUDE.md                       → <!-- DEVLOG:START v0.6.0 ... -->
pyproject.toml                  → version = "0.6.0"
src/devlog_cli/_version.py      → __version__ = "0.6.0"
```

Once those three matched, there was nothing left to regenerate. The correct response was a no-op backed by evidence, not a new commit.

## What's next

Nothing for the code itself. The open question is process: if review comments target generated versioned artifacts, they can go stale as the branch evolves, so the first step should stay "check the current file," not "apply the requested diff."

## Surprises

The interesting part was not the version match itself; it was that this turn still tripped the blog trigger even though it ended with no code changes. The project's own convention is explicit that architecture and scope decisions count, and this was the narrower maintenance version of that rule: deciding *not* to edit a generated artifact is still a decision worth recording when it prevents unnecessary churn.
