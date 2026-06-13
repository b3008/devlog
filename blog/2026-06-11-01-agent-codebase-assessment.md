---
title: "Assessment: how useful is devlog for agent-coded codebases?"
date: 2026-06-11
timestamp: 2026-06-11T22:37:48
tags: [research, architecture, ux]
summary: "A full-system assessment from an unusual vantage point — the assessing agent was running inside devlog's own install — yielding eleven findings (including a likely root cause for the Stop hook's red-box problem) and a tiered roadmap toward 'institutional memory for agents'."
---

## What changed

No code. This session was a requested assessment: how useful is devlog for codebases that are *coded by agents*, and what would make it more useful? The assessing agent read the entire system — CLI, convention renderer, manifest, hook, slash commands, the dogfood corpus — while itself running under devlog's global + local install, with the Stop hook armed. Several findings came from that first-hand position rather than from code reading.

The eleven findings, compressed:

1. **Stop hook protocol bug (likely root cause of the red box).** `stop.py` prints `{"decision": "block"}` JSON to stdout but exits 2. Claude Code's structured channel for Stop hooks is exit **0** + JSON; exit 2 is the simple channel (stderr → model, red "Stop hook error" styling). The wallpaper effect the [05-31 trim](2026-05-31-01-stop-hook-reminder-trim.md) mitigated is probably self-inflicted — that entry's claim that "exit code 2 is the only channel" looks wrong against the hooks docs. Needs a scratch-session verification, then a two-line fix plus test updates (`test_hook.py` asserts `code == 2`).
2. **Every turn pays an extra model round-trip.** The hook blocks the first stop unconditionally — including pure Q&A turns and turns where the entry was *just written*. Mutation-gating via the `transcript_path` the hook already receives (pass silently when nothing mutated, or when `blog_dir` was touched) eliminates most of the tax.
3. **Gaps are invisible.** Nothing records that a session happened without producing an entry. A SessionEnd hook appending to `.devlog/sessions.jsonl` would turn `status` into a real coverage metric — and finally answer the learned.md open thread about whether the adaptive surface gets used.
4. **Double-injection observed live.** The assessing agent's context contained the full convention twice — `~/CLAUDE.md` (global) and project `CLAUDE.md`. ~1–1.5k duplicated tokens per session, plus drift risk (the copies already differ in tag order).
5. **Global path mismatch.** README says `~/.claude/CLAUDE.md`; `_install_global` writes `~/CLAUDE.md`. Different semantics (true global vs. ancestor traversal under home).
6. **`_index.md` + `NN` break under parallel sessions/worktrees.** Hand-maintained state, fully derivable from frontmatter, guaranteed merge conflicts. Should be generated (`devlog index`), with convention step 6 deleted.
7. **The media convention is a dead letter — falsified by this very corpus.** Fourteen entries, zero images, no `blog/media/` on disk. Terminal agents can't screenshot. Defaults should ask for what agents *can* produce: CLI output blocks, diffs, Mermaid.
8. **No retrieval past ~20 entries.** Catchup reads the last 5; everything older is write-only. Needs topic-scoped catchup, search, a frontmatter JSONL index — and eventually `devlog blame <file>`.
9. **Entries are unverifiable claims.** No `commit:`/`files:` frontmatter, so narrative can't be navigated to from code or checked against the diff it describes. Evidence frontmatter also mechanizes manicure's "drifted" category.
10. **The blog can silently never ship.** Observed: the 05-31 entry sat uncommitted for six weeks on a side branch. The convention never says "commit the entry with the work"; nothing publishes HTML/RSS.
11. **"27 agents" is 1 + 26 passive.** Only Claude Code gets enforcement and commands; the rest get static AGENTS.md text. Several of those ecosystems now have command mechanisms worth porting to.

> **Update 2026-06-13**: After the [README audit](2026-06-13-02-readme-audit-against-assessment.md), F11 is the *only* README-touching finding still open — F4–F7 and the hook findings all landed in the README via the 06-12 work. The depth-of-support gap remains unstated in the README (an accepted positioning call, deferred to the user); the port-commands-to-other-agents half remains roadmap.

## Why it matters

The assessment's core judgment: the premise is *more* right for agent-coded codebases than for human ones — the reasoning lives in discarded transcripts, the human didn't write the code, and commits only carry the *what* — but the current design assumes one human, one agent, serial sessions. Agent-coded repos are parallel, high-velocity, and partially headless. Capture is polite rather than reliable; consumption doesn't scale; concurrency breaks the index. None of these are fatal, and the strongest fixes are small.

The strategic reframe that came out of it: devlog's deepest value for this audience isn't the portfolio blog — it's being the only durable, git-versioned, cross-agent record of *why the code is the way it is*. The portfolio is a rendering of that record. Native agent memory can't compete (private, unversioned, harness-bound); commit archaeology can't either (lossy). That positions the Tier-3 features — SessionStart auto-brief, transcript-grounded distillation, `devlog blame` — as the actual product, with the blog as its human-facing view.

## What's next

Tiered roadmap proposed (not yet decided with the user):

- **Tier 1 (small diffs):** hook exit-0 fix; mutation/entry gating; generated `_index.md`; global → `~/.claude/CLAUDE.md` + thin local block; media defaults swap; "commit the entry" convention line; `commit:`/`files:` frontmatter.
- **Tier 2 (measurement + retrieval):** `sessions.jsonl` coverage tracking; topic catchup/search/JSONL index; `devlog doctor`; the CI safety-net check from the [landscape survey](2026-04-18-landscape-survey.md) — still unbuilt.
- **Tier 3 (strategic):** SessionStart auto-brief via `additionalContext`; transcript distillation at SessionEnd/PreCompact; `devlog blame`; `devlog export` / cross-repo digest.

## Surprises

- The red "Stop hook error" box — the thing an entire prior session was spent mitigating — appears to be a two-line protocol mismatch, not a Claude Code constraint. The 05-31 entry reasoned carefully *from a wrong premise* and still reached a defensible decision; the premise itself was never checked against the hooks docs.
- The dogfood corpus falsified the media convention by pure absence: the instruction that "screenshots are critical" produced zero images in fourteen entries on the tool's own repo, and nobody noticed because nothing measures convention compliance (finding 3, again).
- Assessing from inside the install kept generating evidence the code couldn't: the double-injection was visible in the assessor's own context window, and the uncommitted 05-31 entry was visible in `git status`. The system's gaps are easier to *experience* than to *read*.
