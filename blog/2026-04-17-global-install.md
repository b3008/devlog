---
title: "Global install: one command, every project blogs"
date: 2026-04-17
tags: [feature, architecture, cli]
summary: "devlog install --ai claude --global injects a self-bootstrapping convention into ~/.claude/CLAUDE.md so every project gets blogging without per-project setup."
---

## What changed

A new `--global` flag on both `install` and `uninstall`. When passed:

- The convention is injected into `~/.claude/CLAUDE.md` (Claude Code's
  global instructions file) instead of the project-local `CLAUDE.md`.
- The convention gains a "First-time setup" section that tells the agent
  to auto-scaffold `blog/`, `blog/media/`, `blog/_index.md`, and
  `.devlog/learned.md` in any project that doesn't have them yet.
- Per-project `.devlog/config.yaml` overrides are honored when present.
- The Stop hook, when `--with-hook` is also passed, goes to
  `~/.claude/settings.json` and `~/.devlog/hooks/stop.py`, using
  `$HOME` instead of `$CLAUDE_PROJECT_DIR` in the command path.
- The manifest lives at `~/.devlog/manifests/claude.manifest.json`.

The per-project `devlog install` continues to work unchanged for users
who prefer explicit per-project setup.

## Why it matters

The original design required `devlog init` + `devlog install` in every
project. That's fine for a handful of repos but scales badly — the user
has to remember to install in each new project, and any project they
forget gets no blog. The global install inverts the default: every
project blogs unless opted out. Per-project customization becomes
optional, via `devlog init` + config edits.

The two models layer cleanly. Claude Code reads `~/.claude/CLAUDE.md`
first, then the project-local `CLAUDE.md`. When both exist, the agent
sees both convention blocks — but for most users, you'd pick one: global
for breadth, per-project for precision.

## How it works

The convention text is the same except for two additions when
`global_mode=True`:

1. The opener changes from *"This project keeps..."* to *"Every project
   you work on keeps..."*.
2. A "First-time setup" subsection instructs the agent to scaffold
   `blog/` and `.devlog/` on first entry if the directory structure
   doesn't exist yet. It also says: if `.devlog/config.yaml` exists,
   use its settings instead of the defaults below.

The `install` command splits into `_install_local` (unchanged behavior)
and `_install_global` (writes to `Path.home()`). The hook helpers gained
a `global_mode` parameter that switches the command string from
`$CLAUDE_PROJECT_DIR/...` to `$HOME/...`. The rest of the hook machinery
— idempotent settings.json merging, manifest recording, uninstall
cleanup — is reused without changes.

## What's next

- Currently `--global` only supports `claude`. Other agents could follow
  once their ecosystems define a global instructions file.
- `devlog status` doesn't yet know about global installs — running it in
  a project won't detect that a global convention is active. A future
  `devlog status --global` or automatic detection could close that gap.
