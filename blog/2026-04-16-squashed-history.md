---
title: "Squashing the repo history to one commit"
date: 2026-04-16
tags: [infrastructure]
summary: "Four working-day commits collapsed into a single 'Initial release' commit before anyone clones the repo."
---

## What changed

`main` on the public repo now contains a single commit titled *"Initial
release: devlog"*. The four prior commits — initial scaffold, README
polish, convention-enhancement batch, and a small README tweak — were
squashed via `git reset --soft <root>` followed by `git commit --amend`,
then force-pushed.

## Why it matters

The repo had been public for a few hours with no external consumers. The
working-day commit log was useful *while* iterating but would have been
noise for anyone cloning later — four messages describing a single
arrival, rather than one clean starting point. Squashing while the repo
is still effectively private trades nothing (there's no one to disrupt)
for a cleaner permanent log.

Going forward, the repo will preserve commits normally. The squash was a
one-time move on day zero, explicitly scoped to pre-release history.

## How it works

```
FIRST=$(git rev-list --max-parents=0 HEAD)
git reset --soft "$FIRST"
git commit --amend -m "Initial release: devlog …"
git push --force origin main
```

The `--soft` reset moves HEAD back to the root commit while leaving the
working tree and index at the tip — so every change from every subsequent
commit is staged against the root. `commit --amend` then replaces the root
commit's contents with the current index, giving us exactly one commit
containing everything. The orphaned commits become unreachable and will
be pruned by GitHub's GC.

## What's next

Nothing specific — this was a hygiene move, not a workflow change. Future
commits stay atomic and meaningful. If the repo ever gets contributors,
force-pushes to `main` stop being acceptable; that's well understood.
