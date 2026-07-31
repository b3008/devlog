---
type: "Devlog Entry"
title: "The upgrade path was pointing at a branch four releases behind"
date: 2026-07-31
timestamp: 2026-07-31T12:16:26
tags: [infrastructure, research, cli]
description: "A fleet-wide audit of 25 installed devlogs, prompted by a simple 'do I need to reinstall?', found that `uv tool upgrade devlog` would have downgraded the tool, that four 'customized' global artifacts were merely stale, and a cold-repo bug that orphaned the legacy index in 16 of 24 projects — fixed in 0.6.1."
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

## The resync, and what it turned up

`main` was updated the same day (PR #18), which unblocked the path — so the rest
of this entry is what actually happened when it ran.

The tool layer went cleanly: `uv tool upgrade devlog` moved 0.3.0 → 0.6.0. The
global layer did not. `devlog install --ai claude --global` reported four
artifacts **preserved as customized** — three slash commands and the Stop hook —
which would have meant real edits worth protecting. Diffing them against the
shipped templates showed the opposite:

```diff
-- `<index_file>` is the `index_file` value (default: `index.md`).
+- `<index_file>` is the `index_file` value (default: `_index.md`).
-BUDGET_BYTES = 60 * 1024
+BUDGET_BYTES = 100 * 1024
```

Every difference was template *evolution* — the pre-OKF index name, the old byte
budget, the pre-`knowledge/` wording. Not one personal edit. These were stale
0.4.x-era files that the preservation check could not distinguish from
customizations, which is precisely the ambiguity 0.6.0 shipped `--force` for.
`install --global --force` resynced all four, and this is the first time that
escape hatch has been needed on something other than a test.

Worth noting what the failure looked like from outside: the convention block said
`blog/index.md` while the slash commands sitting next to it said `blog/_index.md`.
A preserve is not a neutral act — it pins one artifact while its siblings move.

**The per-repo layer then hit a real bug, and the sweep is on hold because of it.**
`plan_migration()` reads the current index name from config only:

```python
current_index = config.get("index_file", OKF_INDEX_FILE)
```

Sixteen of the 24 repos have a `.devlog/` with no `config.yaml` — they were
scaffolded by the *global* convention, which never writes one. For those, the
default resolves to `index.md`, a file that does not exist, so `index_rename`
computes False and the real `_index.md` is never seen. Migration would write a
correct new `index.md` and leave the old one orphaned beside it — then count it as
a blog entry forever after, since the skip set only ever contained the two names
it already knew about.

Not destructive, and the 8 config-carrying repos migrate correctly. But it is
litter in 16 git repositories, so the fix belonged before the sweep, not after.

## The fix (0.6.1)

Config is the wrong sole authority for a filename when the file is right there to
look at. `plan_migration()` now probes disk when the configured index is absent:

```python
if not (blog_dir / current_index).exists() and (blog_dir / LEGACY_INDEX_FILE).exists():
    current_index = LEGACY_INDEX_FILE
```

That one substitution fixes three symptoms at once, because everything downstream
reads `plan.current_index`: the rename is planned, `_apply_migration` `git mv`s
instead of writing a second file, and `_index.md` enters the skip set so it stops
being tallied as a blog entry.

A second, quieter correction went in alongside it. `config_update` was
`current_index != OKF_INDEX_FILE`, so a config-less project now reaching that
branch via the probe would be told "config: would set index_file: index.md" —
an edit `_set_config_index_file()` silently declines, since there's no config to
edit. It's now gated on an `index_file:` key actually existing. A dry run that
promises work it won't do is worse than no dry run.

Before and after on a real repo (`accounting`, five entries, no config):

```console
- └── index: would stamp index.md with okf_version
- ├── 1 entries already conformant          # ← that was _index.md
+ └── index: _index.md would be renamed to index.md
```

Three tests cover it, two of which fail against the old code; the third pins the
probe against re-firing once `index.md` is real, which would otherwise make
`status` report non-conformance forever. Full suite 199 green, ruff clean.

## What's next
- **A fleet-scoped verb.** `devlog status --all <root>` (report) before
  `devlog fleet migrate` (act) — read-only first, since a sweep that rewrites
  frontmatter across 24 repos is exactly the kind of surprise-VCS-diff the project
  has already argued against for hooks. Six of those repos have dirty working
  trees right now, which is its own argument for reporting before acting.
- **Release discipline has teeth now.** The existing open thread noted that
  version bumps matter or the stamp machinery reports nothing. The stronger
  version: if the default branch lags, the machinery reports *backwards*. A CI
  check that the default branch's version is the highest released version would
  catch it.
