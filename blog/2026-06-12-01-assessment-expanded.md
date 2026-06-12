---
title: "Assessment expanded: the constraint flipped from capture to consumption"
date: 2026-06-12
timestamp: 2026-06-12T14:34:27
tags: [research, architecture, ux]
summary: "Re-opening the agent-codebase assessment produced a verified fix (the Stop hook exit-code theory confirmed against the docs), a refutation of the prior entry's own correction, and a reframed thesis: agents solved capture discipline by construction, so retrieval and trust are now the binding constraints."
---

## What changed

No code. The user re-opened the [06-11 assessment question](2026-06-11-01-agent-codebase-assessment.md) — how useful is devlog for agent-coded codebases, and what would make it more useful — explicitly to expand the themes and capture more points. Two things happened beyond discussion:

1. **The exit-code theory was verified against the current Claude Code hooks docs** (via a docs-grounded subagent). Confirmed: `{"decision": "block", "reason": ...}` JSON with **exit 0** blocks the stop without the red "Stop hook error" styling; exit 2 + stderr is the channel that renders as an error. The Tier-1 hook fix is now fact, not hypothesis — two lines in both `stop.py` copies plus updating `test_hook.py`'s `code == 2` assertions.
2. **The 06-11 entry's own correction was refuted.** That entry noted "`additionalContext` is UserPromptSubmit/SessionStart only, not Stop." The current docs list Stop (and SubagentStop) among the events supporting `hookSpecificOutput.additionalContext` — either the claim was wrong or the docs changed since. Either way the deferred hybrid hook (mutation-gated loud block + silent advisory) is **fully unblocked**: Stop hooks receive `transcript_path`, can block via exit-0 JSON, and can whisper via `additionalContext`. One genuine ambiguity remains: the docs don't say whether Stop hooks fire in headless (`claude -p`) mode.

## Why it matters

The refutation is the most important finding, because of what it demonstrates. The corpus now contains a three-generation chain of confident claims about one protocol: the [05-31 entry](2026-05-31-01-stop-hook-reminder-trim.md) reasoned from "exit 2 is the only channel" (wrong); the 06-11 entry corrected that but added its own wrong claim about `additionalContext`; today's check corrected both. Nothing in the corpus marks the stale entries. A future agent reading any single entry inherits its errors at face value — the entire deferred-hook design was shaped by the wrong premise for six weeks. For human readers stale claims are friction; for agent readers they compound.

The session also reframed the central thesis. devlog has solved the problem that kills every competitor in the landscape survey — capture discipline — by construction, because agents write tirelessly. The binding constraint has therefore flipped to **consumption**: the future reader's token budget and trust in what they read. This session's own catchup is the evidence: `/devlog-catchup` produced a complete working model of the project in one command (~25k tokens of reads at 15 entries — works now, won't at 150), and `learned.md`'s Open threads section carried most of the load, not the entries. The compressed view is the real interface; the blog is its archive.

## What's next

New points captured for the roadmap, beyond the eleven findings of 06-11:

- **Supersession at write time.** When an entry corrects an earlier one, the convention should require a dated annotation on (or `superseded_by:` frontmatter in) the superseded entry immediately — not during an occasional manicure. Convention-text rule first, tooling later.
- **Shrink the convention to a stub.** ~1.5k tokens ride in every session (×2 with the dup bug). A 5-line stub pointing at `/devlog-catchup` and `.devlog/config.yaml`, with details lazy-loaded, follows the ecosystem trend and shrinks both the standing tax and re-install diff noise.
- **Retrieval beats voice.** Having now been the consuming agent: the portfolio narrative voice is *good* for agent consumption — Surprises sections carry exactly the misconception-corrections that prevent repeated mistakes. The dual-audience tension is smaller than feared; the gap is topic retrieval, a frontmatter index, and epoch distillation of older entries.
- **A knowledge-placement policy.** Harnesses give agents private persistent memory; without a routing rule, project knowledge leaks into surfaces that are unversioned and invisible to other agents. The convention should declare: durable project facts → `learned.md`; why-narrative → entries; stable rules → CLAUDE.md; user preferences only → harness memory.
- **A decision register.** Formalize Open threads into a queryable live/superseded decision surface (possibly generated from entry frontmatter) so parallel agents can check "is this settled?" without reading the corpus.
- **Measure before the smarter hook.** The hybrid design being unblocked doesn't change the 05-31 sequencing instinct: `sessions.jsonl` coverage tracking should land first so the hook's effect is observable. Headless capture likely wants per-merge distillation regardless.
- **Honest non-fit scoping**: throwaway prototypes and very-high-velocity repos (dozens of agent PRs/day) want per-PR or per-epoch grain, not per-session entries.

Immediate implementation order implied: exit-0 fix + global/local dedup together (both hooks fired with diverging texts on this session's catchup turn — the drift is still generating live evidence), then measurement, then the hybrid.

## Surprises

- The verification subagent refuted the very entry that had set up the verification. The 06-11 assessment correctly flagged "verify before building" — and the thing needing verification turned out to include its own correction note. Two consecutive entries were each wrong about a different half of the same protocol, which is a better argument for evidence frontmatter and supersession marking than any hypothetical.
- `learned.md` quietly outperformed the blog at its own job. The catchup's working model came mostly from Open threads — the agent-owned compressed surface — with entries serving as drill-down. That inverts the implicit hierarchy (blog primary, learned.md auxiliary) and supports making the compressed view the first-class product.
