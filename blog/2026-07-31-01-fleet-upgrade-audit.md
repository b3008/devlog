---
type: "Devlog Entry"
title: "The upgrade path was pointing at a branch four releases behind"
date: 2026-07-31
timestamp: 2026-07-31T12:16:26
tags: [infrastructure, research, cli]
description: "A fleet-wide audit of 25 installed devlogs, prompted by a simple 'do I need to reinstall?', found that `uv tool upgrade devlog` would have downgraded the tool — and that three install layers drift independently with no command that sweeps them."
---

## What changed

Nothing shipped. This was an audit, prompted by a one-line question: *after the
latest changes, do I need to reinstall devlog in the places where it's used?*

The honest answer turned out to be "yes, but you can't yet," and finding out why
required actually looking at the fleet rather than reasoning about it.

## Why it matters

devlog's upgrade story has been written about twice
([the CLI verb](2026-06-14-01-devlog-upgrade-command.md),
[the slash command](2026-06-14-04-devlog-upgrade-slash-command.md)), both times
from inside this repo, where the tool is an editable install and everything is
current by construction. Neither entry checked what the path does for the 24
*other* projects that have devlog installed. This is the
[dogfooding-the-warm-path](../.devlog/learned.md) failure mode, showing up in
exactly the place the theme predicts.

## How it works

The audit came out in three layers, each drifting independently.

**Layer 1 — the tool binary.** `uv tool list` says `devlog v0.3.0`, and the
receipt says where it comes from:

```toml
[tool]
requirements = [{ name = "devlog", git = "https://github.com/b3008/devlog.git" }]
```

No branch, no tag — so it tracks the default branch. And `main` is at **0.2.0**:

```console
$ git show main:pyproject.toml | grep '^version'
version = "0.2.0"
```

Everything from 0.3.0 through 0.6.0 — `devlog upgrade`, OKF conformance,
first-class OpenCode install, the `source_sha256` preservation fix — lives on an
unmerged branch. **`uv tool upgrade devlog` today would take the fleet from
0.3.0 to 0.2.0.** Not a no-op. A downgrade, silently, with the version stamp
machinery dutifully reporting it as an install.

**Layer 2 — the global convention block.** `~/.claude/CLAUDE.md` carries
`<!-- DEVLOG:START v0.4.1 ... -->`. That's *newer* than the 0.3.0 binary that's
supposed to have written it — proof the layers move independently, because it was
injected by a dev build run out of this repo's venv. It still tells every agent
to write `blog/_index.md`, the pre-OKF name.

**Layer 3 — per-repo data.** This is the one a global install cannot reach.
Of 25 repos with a `.devlog/`, exactly one — this one — has migrated to OKF:

| | count |
|---|---|
| repos with `.devlog/` | 25 |
| still on `blog/_index.md` | 24 |
| local sentinel block, stamped | 2 (v0.3.0) |
| local sentinel block, **unstamped** | 7 (pre-0.2.0) |
| relying on the global block only | 15 |

`_install_local` auto-migrates (`__init__.py:230-236`), so the fix exists — but it
only fires in the repo you're standing in. There is no `devlog fleet` verb, and
`devlog status` is likewise cwd-scoped: the drift is individually detectable and
collectively invisible.

So the resync order is: merge to `main` → `uv tool upgrade devlog` →
`devlog install --ai claude --global` (one command, covers the 15 global-only
repos) → `devlog migrate` in each of the remaining 24 for the OKF data.

## Surprises

**My own audit script had the exact bug the project keeps writing about.** First
pass classified repos by grepping `DEVLOG:START v[0-9.]*` for the block version.
Seven repos came back "no local block" — and I nearly reported that number. They
all *have* blocks; they're 0.1.0-era blocks, from before the version stamp
existed, so they read `<!-- DEVLOG:START -->` with nothing to match. The regex
assumed the presence of the field it was measuring, and the failure mode was a
confident wrong count rather than an error.

That's the same shape as the
[`sha256` overloading that ate a customization](2026-07-29-03-preservation-baseline.md):
a schema that grew a field, and a reader that treats "field absent" as "thing
absent." `status` handles this correctly ("convention block predates the version
stamp"); my throwaway script did not. Ad-hoc measurement of a versioned schema is
where these bugs go to hide.

**The generalization in `learned.md` was one word too loose.** It said upgrade
pulls what's *published on GitHub*. Pushing a branch is publishing; it isn't
enough. It pulls the **default branch**, specifically, which is a much sharper
constraint — and the one that actually bit.

## What's next

- **Merge `terser-output` to `main`.** Nothing about the upgrade path works until
  the releases are where the installer looks. Four versions of work are currently
  unreachable by every consumer including this machine.
- **A fleet-scoped verb.** `devlog status --all <root>` (report) before
  `devlog fleet migrate` (act) — read-only first, since a sweep that rewrites
  frontmatter across 24 repos is exactly the kind of surprise-VCS-diff the project
  has already argued against for hooks.
- **Release discipline has teeth now.** The existing open thread noted that
  version bumps matter or the stamp machinery reports nothing. The stronger
  version: if the default branch lags, the machinery reports *backwards*. A CI
  check that the default branch's version is the highest released version would
  catch it.
