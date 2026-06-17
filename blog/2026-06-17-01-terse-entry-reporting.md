---
title: "Tell the agent to report devlog writes in one line"
date: 2026-06-17
timestamp: 2026-06-17T08:22:58
tags: [feature, ux, documentation]
summary: "Added a reporting instruction to the convention so agents announce a blog write with just the file path instead of a paragraph of self-narration."
---

## What changed

The convention now tells the agent *how* to report its devlog work, not just when to do it. Two new sentences in the opener of both the global and per-project variants of `generate_convention()` (`src/devlog_cli/convention.py`):

> When you write or update an entry, report it in one line — just the file path (e.g. `blog/2026-06-14-01-slug.md`). When no entry is warranted, say nothing about the devlog at all. Don't narrate which triggers you checked, what you scaffolded, or why an entry wasn't needed.

Version bumped 0.4.0 → 0.4.1 (`_version.py` + `pyproject.toml`) per the project rule that convention changes must move the version stamp, and the global `~/.claude/CLAUDE.md` block was regenerated so the change takes effect immediately (sentinel now reads `v0.4.1`).

## Why it matters

The trigger was a real annoyance: at the end of nearly every turn the agent emitted a paragraph like —

> The devlog requirement is already satisfied this turn — I created blog/2026-06-14-01-knowledge-wiki-framework.md (a "new feature" + "architecture/scope decision" trigger), scaffolded blog/, blog/media/, and .devlog/learned.md, and added the entry to blog/_index.md. Nothing new happened since that needs capturing.

That self-justifying narration is noise. The convention spent ~1.5k tokens telling the agent *when* and *how* to write, but nothing on how to *report*, so the model defaulted to explaining its trigger-checking out loud — including on turns where it correctly decided to write nothing. The fix closes that gap from the same surface that created it.

## How it works

The reporting instruction lives in the convention text itself, so it ships through the existing install pipeline — no new mechanism. Both openers in `generate_convention()` carry it (the global "Every project…" variant and the per-project "This project…" variant); the thin project block needs nothing because it already defers to the global copy. It reached this repo's effective behavior via `devlog install --ai claude --global --with-hook`, which is idempotent and sentinel-wrapped.

One detail worth recording: the surrounding template strings encode em-dashes as `—` escapes to keep the Python source ASCII, while the `DEFAULT_CONFIG` data strings use literal `—`. The new lines were normalized to the `—` form to match their immediate neighbors in the f-string.

## What's next

- This only governs the *automatic* per-turn report. The `/devlog-write` slash command still has its own "Step 5 — Report back" that asks for path + NN + one-line summary; that's a deliberate, user-invoked verbosity and was left alone.
- Whether the instruction actually suppresses the narration is an empirical question — worth a glance over the next few sessions' `sessions.jsonl` to confirm the model honors "say nothing when no entry is warranted."
