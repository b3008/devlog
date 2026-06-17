---
title: "/devlog-upgrade: a slash command that drives the two-layer upgrade"
date: 2026-06-14
timestamp: 2026-06-14T11:22:08
tags: [feature, cli, ux]
summary: "Added a fourth slash command, /devlog-upgrade (v0.4.0), a thin AI-driven driver over the devlog upgrade CLI so the maintenance verb is reachable from inside any Claude Code session — not just the terminal."
---

## What changed

devlog now ships a fourth slash command: **`/devlog-upgrade`**. It's a thin
driver over the `devlog upgrade` CLI [shipped this morning in
0.3.0](2026-06-14-01-devlog-upgrade-command.md) — the command that upgrades the
tool binary from GitHub and then resyncs this repo's convention to it. The CLI
existed; what was missing was a way to *reach* it from inside a Claude Code
session, the way `/devlog-catchup`, `/devlog-write`, and `/devlog-manicure`
expose the read / write / prune verbs.

Concretely:

- `src/devlog_cli/templates/commands/devlog-upgrade.md` — the new command body.
- Version bumped **0.3.0 → 0.4.0** (`_version.py`, `pyproject.toml`).
- README updated: "three slash commands" → "four", a new table row, and the
  `.claude/commands/` file tree.
- Tests extended (`tests/test_cli.py`): the manifest- and install-message
  assertions now cover `devlog-upgrade`, the idempotency test expects 4 files,
  and a new `test_upgrade_command_file_created` checks the body drives the CLI.
- Dogfooded: installed into this repo *and* the global `~/.claude/` install, so
  the command is live everywhere. 163/163 tests pass, ruff clean.

```text
$ uv run devlog install --ai claude
├── Installed slash command /devlog-catchup (.claude/commands/devlog-catchup.md)
├── Installed slash command /devlog-manicure (.claude/commands/devlog-manicure.md)
├── Installed slash command /devlog-upgrade (.claude/commands/devlog-upgrade.md)
├── Installed slash command /devlog-write (.claude/commands/devlog-write.md)
```

## Why it matters

This closes an asymmetry the project had been carrying. The convention preaches
"keep current" — `devlog status` reports drift, and 0.3.0 gave a CLI to fix it —
but the only way to act on that was to drop to a terminal and remember a command.
The other three verbs each have a slash command; maintenance didn't. Now it does,
and it sits in the same surface a session already lives in.

The interesting part is that a slash command can do what the bare CLI can't: it's
an *agent reading the CLI's own preview and branching on it*. `devlog upgrade`
already detects the install method and prints install-method-aware guidance; the
slash command runs `--check` first, reads that guidance, and acts —
offering to `git pull` when devlog is a source checkout, or pointing at a
persistent install when it's an ephemeral `uvx` run, rather than blindly invoking
an upgrade that would no-op.

## How it works

The wiring was almost nothing, by design: the installer auto-discovers command
templates with `glob("*.md")`, so dropping a new `.md` into
`templates/commands/` is the entire integration — no code changed in
`__init__.py` or `manifest.py`. The version sits in one module (`_version.py`),
imported by both the sentinel stamp and the tests, so bumping it propagated to
the convention block and every version assertion without touching them.

The command itself is a three-step driver:

1. **Preflight** — `command -v devlog`; if it's not on PATH there's nothing to
   upgrade through, so suggest a persistent install and stop.
2. **Preview** — `devlog upgrade --check` (forwarding `--check` / `--tool-only`
   / `--project-only`), then relay the plan.
3. **Apply** — if the preview shows a self-upgradeable install, run the real
   `devlog upgrade`; if it warns it can't (source / uvx / unknown), handle that
   specific case instead of running a command that would only reprint the warning.

## Surprises

- **The upgrade path can't bootstrap its own first appearance.** The obvious way
  to "install the new command" would be to run `devlog upgrade` — but that pulls
  from GitHub `main`, which doesn't have this still-uncommitted command yet. To
  land the new template from *local source* I had to use `uv run devlog install`,
  not the upgrade path. A small but real property of the two-layer model: upgrade
  moves you to what's *published*, install moves you to what's *here*.
- **The "stable surface" theme paid a dividend.** The global install was stamped
  `v0.2.0` — two minors behind — so I expected a global resync to rewrite the
  user's `~/.claude/CLAUDE.md` convention. A diff of the generated v0.4.0 body
  against the live one came back **byte-identical**: the resync was a stamp bump
  plus the new command file, nothing more. The convention text being inert across
  versions (only `learned.md` and discovered tags carry change) is exactly what
  made touching a multi-version-stale global config safe.
- **An adversarial review over-rated its own finding.** A verification agent
  diffing the command against the CLI flagged a "must-fix": my line said to
  surface "the fallback command it printed," which implies the CLI *always*
  prints one — it doesn't, on a resync failure. The fix was a one-word wording
  change ("*any* fallback command… from the streamed output"), not a functional
  gap. Useful skepticism; right to tighten the claim, wrong about the severity.

## What's next

- **A "maintenance" grouping.** Four commands is the point where the flat list
  wants structure — three authoring verbs (catchup / write / manicure) plus one
  maintenance verb (upgrade). Worth reflecting in docs if a fifth appears.
- **Remote version check.** Carried over from the CLI entry: `upgrade` always
  *attempts* the upgrade rather than first asking "is there even a newer
  version?" `--check` previews the action, not availability.
- **Stale historical entries.** Several older entries still say "three commands"
  (2026-05-02-04/05, 2026-06-12-02). Per the convention I annotated the one claim
  this entry directly supersedes and left the rest for a `/devlog-manicure` pass
  rather than rewriting history.
