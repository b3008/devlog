---
title: "Version-aware installs: 0.2.0, sentinel stamps, and drift reporting"
date: 2026-06-12
timestamp: 2026-06-12T15:47:40
tags: [feature, cli, infrastructure]
summary: "devlog finally knows what version its installs are from: __version__ bumped to 0.2.0 after fourteen months at 0.1.0, the sentinel block now carries a version stamp, and devlog status reports drift with reinstall as the upgrade command — auto-resync was considered and deliberately rejected."
---

## What changed

The user asked whether projects using devlog could auto-upgrade, and whether installs could "mention version." The answer exposed an embarrassment: the manifest has dutifully recorded `version: "0.1.0"` in every install since April — through the slash commands, the hashing rounds, the hook bundle, all of it — because `__version__` was never bumped. Version *recording* existed; version *discipline* didn't.

The implemented slice:

- **`0.2.0`**, single-sourced in a new `_version.py` (imported by both `__init__` and `convention` — the sentinel needs it, and a separate module avoids the import cycle), bumped in `pyproject.toml` to match.
- **Sentinel version stamp**: blocks now open with `<!-- DEVLOG:START v0.2.0 - ... -->`. Backward compatible by construction — detection uses the `<!-- DEVLOG:START` prefix and removal tolerates anything before the closing `-->`, so pre-0.2.0 blocks still parse, and a reinstall upgrades the stamp in place.
- **`devlog status` drift reporting**: a Version column in the table, plus a warning line when anything a reinstall would change is detected — manifest version older than the running tool, an unstamped (pre-0.2.0) convention block, or installed artifacts whose recorded hashes differ from the currently shipped templates. The hint is always the same: `devlog install --ai <key>` is the upgrade command, and customized files are preserved.

> **Update 2026-06-12** (same day, post-review): "the hint is always the same" didn't survive Copilot. When the manifest or stamp is from a *newer* devlog than the running tool, a resync would downgrade templates — `status` now detects that direction and recommends upgrading the tool instead. The review also split "artifacts differ" from "artifacts lack a recorded hash" (pre-0.2.0 installs are unverifiable, not necessarily different). PR #14's threads carry the details.

**Auto-resync was considered and rejected.** A hook that rewrites CLAUDE.md mid-session mutates context the agent has already loaded, surprises collaborators through VCS diffs, and assumes the CLI is on PATH (the hooks are deliberately stdlib-only). The accepted model: reinstall-as-upgrade (made safe by the morning's carry-forward/hash work), with `status` as the nag. 142 → 150 tests.

## Why it matters

Every artifact devlog installs is a snapshot that drifts as the tool evolves — this repo spent the morning repairing exactly that kind of drift (a stale global hook, diverged reminder texts). The hashing work gave reinstall the ability to fix drift safely; this slice gives users a way to *see* drift before it bites. The division of labor: versions are for humans (one glance at the sentinel says what wrote it), hashes are for machines (they catch drift even when a version bump is forgotten — which, as fourteen months of `0.1.0` demonstrates, it will be).

## What's next

- Version discipline is now load-bearing: template changes without a version bump make the stamp lie. A CI check (template hashes vs last release) could enforce it; noted in learned.md.
- A SessionStart notification ("this project's devlog install is stale") remains the plausible middle ground between silent `status` and rejected auto-resync, if drift turns out to linger in practice.

## Surprises

The feature was nearly free because of work done for other reasons: the manifest already recorded versions (unused), the sentinel matcher was already prefix-tolerant (for wording changes, not stamps), and reinstall was already a safe upgrade path (for the dedup work). The whole slice is ~40 lines of logic plus tests — the morning's infrastructure did the heavy lifting.
