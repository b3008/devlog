---
title: "devlog upgrade: a one-command, two-layer self-upgrade"
date: 2026-06-14
timestamp: 2026-06-14T09:04:17
tags: [feature, cli, architecture]
summary: "Added a `devlog upgrade` command (v0.3.0) that upgrades the tool binary and resyncs this repo's convention in one step — detecting the install method and re-invoking the freshly upgraded binary to do the resync."
---

## What changed

`devlog upgrade` is new in **0.3.0**. Until now, getting current meant a manual
two-step that you had to *know* about: `uv tool upgrade devlog`, then
`devlog install --ai claude` to resync the repo's convention to the new
templates. The two layers — the **tool binary** and the **convention it
installed** — version independently, and nothing tied them together.

```
$ devlog upgrade
  devlog 0.3.0  (uv tool)

↑ upgrading tool
    uv tool upgrade devlog
    0.3.0 → 0.4.0  ✓

↻ resyncing with devlog 0.4.0
    claude — convention + hooks + commands refreshed (customized files preserved)

✓ upgraded 0.3.0 → 0.4.0; 1 agent resynced
```

Flags: `--check` (preview, mutate nothing), `--project-only` (resync this repo
to the installed tool), `--tool-only` (bump the binary, skip the resync). The
README gained an **Upgrading** section, and there's a `__main__.py` so
`python -m devlog_cli` works as a fallback entry point.

## Why it matters

This automates the project's long-standing **reinstall-as-upgrade** model (see
the [version-aware installs](2026-06-12-04-version-aware-status.md) work) without
betraying its caution: the command is user-invoked, not a hook, and it leans on
the same `status` drift logic to know which direction to move. It also closes
the gap behind a [recent question](2026-06-13-02-readme-audit-against-assessment.md)-adjacent
confusion — that there even *are* two layers to upgrade.

## How it works

Two design problems were the whole job:

**1. Which upgrade command to run.** `_detect_install_method()` inspects where
the package lives: `/uv/tools/` → `uv tool upgrade devlog`; `/pipx/` → pipx;
`site-packages` → a pip reinstall from the git URL; a `src/` tree beside a
`pyproject.toml` → a source checkout (`git pull`); the uv cache → ephemeral
`uvx`. Ordering matters — a uv-tool path *also* contains `site-packages`, so the
uv check runs first. When it can't find a managed binary to replace (source /
uvx), it refuses to guess: it prints the exact command and stops.

**2. The bootstrapping problem.** A running Python process can't render the new
templates right after it has replaced its own code on disk — it's still the old
code in memory. So after a successful tool upgrade, `upgrade` resolves the
freshly installed `devlog` binary and **re-invokes it as a subprocess** to do
the resync (`devlog install --ai <key>` per agent). `--project-only` skips the
tool step and resyncs in-process, since nothing changed underneath it. Every
subprocess seam — tool upgrade, version query, resync — is a small isolated
function, so the seven new tests monkeypatch them and never touch a real package
manager.

## Decisions

- **Scope was the user's call.** Self-upgrade is opinionated: it mutates a
  *global* binary, not just this repo. I asked, and the choice was "both layers"
  — with the graceful fallback for un-upgradeable installs.
- **Bumped to 0.3.0** (minor: additive feature). Tests already read
  `__version__` dynamically, so nothing pinned broke.
- **Global resync is included when a global install is detected** — leaving it
  stale after a tool bump would be inconsistent — but it's labelled clearly.
- **Did not auto-resync this dogfood repo.** Resyncing here would inject a *thin*
  pointer block (my machine has a global install), which is wrong for the
  committed `CLAUDE.md` that collaborators without the global install depend on.
  The convention templates didn't change between 0.2.0 and 0.3.0 anyway — only
  the version stamp drifts.

## Surprises

The re-exec realization was the pivot. My first mental model was "upgrade, then
resync" in one process — which silently would have written the *old* templates,
because the in-memory code never changes mid-run. Routing the resync through the
upgraded binary is the only correct version, and it made the command far more
testable as a side effect: the orchestration is pure, the I/O is at the edges.

## What's next

- **Logo drift:** the CLI still prints the old half-block wordmark (`LOGO` in
  `__init__.py`) while the [README now uses ANSI Shadow](2026-06-13-01-readme-logo-ansi-shadow.md).
  A consistency follow-up.
- No remote version check yet — `upgrade` always attempts the upgrade rather than
  first asking "is there even a newer version?" (the git source makes that
  non-trivial). `--check` previews the *action*, not the *availability*.
