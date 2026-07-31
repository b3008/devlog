---
type: "Devlog Entry"
title: "Teaching learned.md to become a wiki"
date: 2026-07-29
timestamp: 2026-07-29T13:06:17
tags: [architecture, documentation, refactor]
description: "The convention now describes learned.md as a progression — flat file first, splitting into .devlog/knowledge/ topic files behind an index of one-line hooks once it passes ~60KB — because trimming alone could not keep a heavy project's context file loadable."
---

## What changed

`.devlog/learned.md` is the read-first context file: the generated convention tells every session to read it before writing an entry, and `/devlog-catchup`, `/devlog-write` and `/devlog-manicure` all open it as step one. On one heavy project it reached 467KB and quietly stopped working.

An earlier pass had already added the subtraction rules — closure semantics for Open threads, a stated size budget, `.devlog/archive/`, and a stop-hook size warning. This pass adds the thing subtraction could not provide: **structure**.

The convention now describes two shapes for the same file, and says how to move between them:

- **Flat** — the four sections (Glossary, Entities, Recurring themes, Open threads) in one file. Still the starting shape, and still what `devlog init` scaffolds.
- **Indexed** — `learned.md` becomes a list of one-line pointers into `.devlog/knowledge/<topic>.md`, with Open threads still written out inside it.

Changes landed across the whole generated surface, so it agrees with itself:

| File | Change |
|---|---|
| `convention.py` | Two-shape read/write model, ~60KB split trigger, split procedure, `knowledge/` in the commit step |
| `templates/commands/devlog-write.md` | Index-then-load on read; new facts go to the right topic file **and** refresh its hook |
| `templates/commands/devlog-catchup.md` | Read the index and Open threads; never load the whole directory |
| `templates/commands/devlog-manicure.md` | Two new audit dimensions: outgrown topic files, stale/missing index hooks |
| `templates/hooks/stop.py` | Budget 100KB → 60KB; detects `knowledge/` and names the remedy that applies |
| `templates/learned.md` | A comment describing the growth path, without changing the flat shape |

## Why it matters

Three trimming passes took that 467KB file to 137KB and then the well ran dry. The section breakdown is the whole argument: Glossary cut 87% and Open threads 88% — both were full of narration the blog told better — but **Recurring themes cut only 15%**, because its 148 bullets are durable API gotchas, not ledgers. 129 were kept verbatim.

That is a structural ceiling, not a discipline problem. A flat file must load all of its knowledge or none, and the durable reference material is exactly the part you are not allowed to delete. An index of one-line hooks costs a few hundred tokens regardless of how much sits behind it, and the reader pays only for what they open.

## How it works

The load-bearing detail is the **hook** — the clause after the dash:

```markdown
- [Stop hook protocol](knowledge/stop-hook.md) — exit codes, block JSON, what fires in headless mode
```

Without it the split is worse than not splitting. A bare title gives a session nothing to triage on, so it either opens everything (no gain over flat) or opens nothing — and now the knowledge is invisible, where an oversized flat file at least still greps. The convention says this in as many words, and `/devlog-manicure` gained a dimension for hooks that have drifted from their file's contents, because a stale hook actively misroutes triage rather than merely failing to help.

Open threads stay inline in the index in both shapes. They are a live list with a lifecycle, not reference nodes, and they are what a session actually needs first.

## Surprises

**The byte budget was wrong, and wrong in the dangerous direction.** The real limit is ~25,000 tokens per read, and past it you get a *truncated page* that looks exactly like a successful read. Bytes are only a proxy for that, and the conversion depends on density: ordinary prose runs ~4 bytes/token, but this file measured **2.5** — it is thick with backticked identifiers, paths and code fragments. Its real capacity was therefore ~61KB, not the ~100KB a byte estimate promises.

Which means it had stopped loading *in full* months before anyone noticed, and the previous pass's 100KB budget would have stayed silent through the entire window where reads were already truncating. The hook now warns at 60KB and explains the density reasoning in a comment, so the next person to raise it has to argue with the arithmetic.

The other surprise was how well-hidden the root cause was. The convention had an append rule and no eviction rule — but three of the four sections are atemporal (a term stays a term), so append-only is genuinely correct for them. Open threads was the only section with a lifecycle, and it inherited the same rule. The gap survived because the rule works for three quarters of the file.

## What's next

This is deliberately a progression, not a mandate. 26 projects on this machine have a `learned.md`; one was 467KB, the next largest is 57KB, and most are under 15KB. A wiki adds indirection with nothing to pay for it at that size, so `devlog init` keeps scaffolding the flat form and the convention states a concrete trigger rather than a preference.

Untested: whether an agent that hits 60KB actually performs the split, or just notes it and appends anyway. The split procedure is written to be followable, but the same could have been said of the eviction rule.
