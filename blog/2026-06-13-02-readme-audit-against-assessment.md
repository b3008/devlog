---
title: "Auditing the README against the assessment — already current, one residual"
date: 2026-06-13
timestamp: 2026-06-13T12:10:36
tags: [documentation, research]
summary: "Checked the README against the 06-11 agent-codebase assessment and every change since; it was kept in lockstep with the 06-12 work, leaving only F11 (depth-of-support honesty) as an accepted, deferred residual."
---

## What changed

No code, no prose — this was a verification turn that ended on a decision. The
question: does the README need updating given the [06-11 assessment](2026-06-11-01-agent-codebase-assessment.md)'s
eleven findings *and* everything shipped since? The answer is **no, it's
already current** — but the answer was worth pinning down rather than assuming,
and the one gap that remains is now a named, accepted constraint instead of a
loose finding.

The assessment's README-touching findings, with their current state:

| Finding | README state today |
| --- | --- |
| F4 double-injection | ✅ thin pointer block documented |
| F5 global path mismatch | ✅ README said `~/.claude/CLAUDE.md`; the **code now matches** (`src/devlog_cli/__init__.py:296,310`, with legacy migration) |
| F6 generated `_index.md` | ✅ `devlog index` in command table + how-it-works |
| F7 media dead letter | ✅ config defaults swapped to CLI output / diffs / Mermaid |
| F1–F3 hook protocol / gating / coverage | ✅ structured-channel wording + SessionEnd→`sessions.jsonl` + status coverage |
| F8 retrieval, F9 evidence frontmatter, F10 commit-the-entry | n/a — not README claims |
| **F11 "27 agents" = 1 + 26 passive** | ⚠️ the lone residual (below) |

The 06-12 *version-aware* work (sentinel version stamp, manifest version, drift
reporting, install-as-upgrade) is fully reflected too. I also checked the live
`learned.md` open threads (evidence frontmatter, `superseded_by:` tooling,
`devlog doctor`): none are *claimed* by the README, so there's no stale promise
to walk back. Verified counts: `devlog list` returns exactly 27 (3 dedicated
context files + 24 on `AGENTS.md`), matching the badge math.

## Why it matters

The README being current is itself a finding: it means the docs were maintained
*as part of* the Tier-1 batch rather than drifting behind it — the failure mode
the assessment kept surfacing elsewhere (capture being polite rather than
reliable). Recording the audit verdict means the next session doesn't re-run it.

## The residual (F11) — decision deferred

The README is honest about the *context-file* tiers (3 dedicated + 24
`AGENTS.md`) and already scopes its "Optional: runtime enforcement (Claude
Code)" and "Slash commands (Claude Code)" headers. What it never states
outright is the depth gap F11 named: **only Claude Code gets the full stack
(enforcement hook + slash commands); copilot/gemini get a dedicated context
file but no enforcement; the other 24 get static `AGENTS.md` text.** The
`Agents: 27` badge, read alone, implies more parity than exists.

This is a positioning/honesty call, not a bug, so it's left to the user: add one
clarifying sentence under "Supported agents," or leave the badge as a
context-file count. Logged here as live rather than silently dropped.

## What's next

- If the user opts in: a one-line clarifier under "Supported agents" that only
  Claude Code gets enforcement + commands.
- F11's *other* half — porting slash-command mechanisms to the agent
  ecosystems that now support them — remains a Tier-2-ish roadmap item, not a
  README change.
