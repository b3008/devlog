---
title: "Dogfooding catch: devlog litters every repo with an untracked session log"
date: 2026-06-14
timestamp: 2026-06-14T09:21:12
tags: [infrastructure, bug-fix]
summary: "The SessionEnd hook writes .devlog/sessions.jsonl into every installing project but nothing gitignores it — so it sits untracked forever. Fixed here; the real fix belongs in `devlog init`."
---

## What changed

Added `.devlog/sessions.jsonl` to this repo's `.gitignore`. It's the
session-coverage log the SessionEnd hook appends to (one JSON line per session,
machine-local) and that `devlog status` reads to report sessions-without-entries.
It is runtime data, not source — but nothing was ignoring it, so it showed up as
untracked across the whole session and begged to be accidentally committed.

## Why it matters

This is a dogfooding catch of exactly the kind this project says it relies on
("feature additions tend to come from observing the convention fail on a real
project"). The hook ships a write-side — it *creates* `sessions.jsonl` in any
project that installs `--with-hook` — but no corresponding ignore-side. So
**every** repo that adopts the hook inherits a permanently-untracked file that
its owner has to notice and ignore by hand. I hit it three times in one session
before fixing it.

The one-line `.gitignore` here fixes *this* repo. The actual fix is tool-level:
`devlog init` (or the hook install) should scaffold the ignore rule so installed
projects never see the file — either appending to the project `.gitignore` or
dropping a `.devlog/.gitignore`. Logged as an open thread.

## What's next

- `devlog init`/hook-install should gitignore `sessions.jsonl` automatically.
  Decide between editing the project `.gitignore` (visible, but mutates a
  user-owned file) and a self-contained `.devlog/.gitignore` (tidier, scoped).
