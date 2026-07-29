---
type: "Devlog Entry"
title: "Landing a three-feature working tree"
date: 2026-07-29
timestamp: 2026-07-29T13:52:00
tags: [infrastructure, cli, documentation]
description: "Verified the OKF migration end-to-end, found that install's customization-preservation can misfire on a stale file, and split a weeks-old 54-file working tree into two coherent commits."
---

## What changed

The OKF work had been sitting uncommitted for weeks — 54 files, `v0.5.0` already stamped. Landing it turned out to be less about writing code than about establishing that the code did what its entry claimed, and then getting it into history without bundling three unrelated things together.

Verification, on a synthetic pre-OKF blog rather than this repo:

```
$ devlog migrate --check
Would migrate blog to OKF v0.1
├── 2 entries
│   ├── 2026-01-01-01-first.md — summary→description, added type
│   └── 2026-01-02-01-second.md — summary→description, added type
├── index: _index.md would be renamed to index.md
└── config: would set index_file: index.md

$ devlog migrate && devlog migrate
Blog is already OKF v0.1 conformant. Nothing to migrate.
```

Auto-migration inside `devlog install` fired on a legacy blog, `devlog status` reported `OKF: v0.1 conformant`, and the hand-written index heading survived the rewrite. Idempotence holds.

## Surprises

**`devlog status` caught its own repo drifting.** It reported *"4 installed artifacts differ from the current templates"* — this repo's dogfooded copies were stale against templates changed earlier the same day. The drift detection shipped in 0.2.0 and this is the first time it has flagged something I didn't already know.

**Then the resync refused the fix.** `devlog install` skipped the Stop hook:

```
├── Preserved customized Stop hook script (.devlog/hooks/stop.py →
│   .claude/settings.json — local edits kept)
```

That is the preservation logic working exactly as designed and producing the wrong outcome. The heuristic is *"the installed file's hash differs from the shipped template, therefore a human customized it — don't clobber it."* But a hash mismatch has two causes, and the check cannot tell them apart: a genuine local edit, or an **older draft of the template itself**, which is what this was. A hash says *different*, not *deliberately different*.

The consequence is quiet and asymmetric: the file most likely to be mid-iteration is the one the tool most reliably refuses to update, so a project can sit indefinitely on a stale hook while `install` reports success every time. The convention's own budget warning was the thing being suppressed here — the hook was still warning at 100KB after the template moved to 60KB.

Worth noting this is the *safe* failure direction. Silently overwriting a real customization is worse than declining to update a stale one. But "preserved" reads as a decision the tool made on evidence, and it isn't one. Something like a `--force-hooks` escape hatch, or recording the hash of the template a file was installed *from* so drift can be told apart from customization, would close it. Not built yet.

## How it works

The commit split was the other half. The working tree held three separable changes — OKF conformance, first-class OpenCode install, and the previous session's `learned.md`-as-wiki work — interleaved in the same files. `convention.py` hunks 10–12 contained two of them at once, so `git add -p` was not going to produce a clean boundary.

What worked instead: splice the earlier state back in from `git show HEAD:...` using short unambiguous anchors, rather than reconstructing text by hand. The file mixes literal `—` with `—` escapes depending on which session wrote each line, so any approach that retyped the text was going to mismatch. Reverting to bytes git already had avoided the problem entirely.

The generated artifacts (`CLAUDE.md`, `.claude/commands/`, `blog/index.md`) were rebuilt at each stage rather than hand-edited, which is the only way they stay consistent with the templates in *both* commits. Commit 1 was then checked out into a throwaway worktree and tested in isolation — 190 tests, clean ruff, and a rendered convention containing the OKF text with none of the wiki text leaked in. Verifying a commit in place proves less than it appears to; the worktree was the only thing that could show it stands alone.

## What's next

The stale-vs-customized ambiguity is the live thread. It sits underneath `install`, `upgrade`, and the manifest, and it will misfire again on the next template change that lands while a project is mid-iteration.
