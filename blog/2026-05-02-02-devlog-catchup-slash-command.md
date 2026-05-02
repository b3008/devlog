---
title: "First slash command: /devlog-catchup for instant project context"
date: 2026-05-02
timestamp: 2026-05-02T10:14:09
tags: [feature, cli, ux]
summary: "devlog now ships a Claude Code slash command, /devlog-catchup, that instructs the agent to read the blog index, recent entries, and learned.md and report back a structured summary of project state."
---

## What changed

Three additions, working together:

1. **New slash command template** at `src/devlog_cli/templates/commands/devlog-catchup.md`. Body instructs the agent to read `blog/_index.md`, the 5 most recent entries, and `.devlog/learned.md`, then return a structured summary covering project arc, recent work, open threads, and glossary highlights.
2. **Install pipeline extended** — both `_install_local()` and `_install_global()` in `src/devlog_cli/__init__.py` now copy bundled command templates into `.claude/commands/` (or `~/.claude/commands/` for global installs) when the target agent is `claude`. Default-on, no flag required.
3. **Manifest tracks commands** — `Manifest.commands: list[dict]` parallels the existing `hooks` list (`src/devlog_cli/manifest.py:28-30`). Each record stores `{"name": ..., "path": ...}`. `uninstall` walks this list and deletes the files, then cleans up empty `.claude/commands/` and `.claude/` parents.

A new helper pair `_install_claude_commands()` / `_uninstall_claude_command()` mirrors the existing Stop-hook helpers. Tests in `tests/test_cli.py::TestSlashCommands` cover creation, manifest recording, idempotency on reinstall, the non-claude skip path, and clean removal — local and global. 95/95 passing.

## Why it matters

The agent's context window resets every session, but the project's accumulated history doesn't. Without help, a fresh session has to either read the whole `blog/` directory unprompted (rare — the convention only tells it to *write* entries, not *read* them) or work blind until the user nudges it. `/devlog-catchup` closes that loop with a single keystroke from the user: type `/devlog-catchup`, get a fast structured briefing tailored to this project, then proceed.

This is also devlog's first agent-side surface beyond the passive convention block and the optional Stop hook. The taxonomy now reads:

- **User-issued slash commands** — `/devlog-catchup` (new).
- **Harness-fired hooks** — optional `Stop` hook via `--with-hook`.
- **Agent-invokable tools** — none, still.

Slash commands are the right shape for "give me a summary": they're explicit, low-blast-radius, and the user controls when they fire. A tool the agent could decide to invoke on its own would be more invasive — slash commands keep the user in the driver's seat.

## How it works

A slash command in Claude Code is just a markdown file at `.claude/commands/<name>.md`. When the user types `/<name>`, the file's body becomes the user message sent to the agent. devlog ships the body as a template with frontmatter that sets the `description` field shown in `/help`:

```markdown
---
description: Read the project's devlog (blog/) and learned.md to gain context...
---

Read the devlog and report back so the rest of this session has full context...

Steps:
1. Read `blog/_index.md` to see the entry list.
2. Read the 5 most recent entries (or all of them if fewer than 5).
3. Read `.devlog/learned.md` for accumulated project knowledge — ...
```

Install uses `shutil.copy2` over every `.md` file in the templates' `commands/` subdirectory. That pattern means future slash commands need only a new file in the template directory; the install loop picks them up automatically. Each copied file gets one entry in the manifest.

Uninstall reads the manifest's `commands` list, removes each recorded path, and walks parents to drop empty `commands/` and `.claude/` directories — same cleanup discipline as the Stop hook. Existing per-project Stop hooks coexist cleanly because the helpers operate on disjoint paths (`hooks/` vs `commands/`) and disjoint manifest fields.

## What's next

Two open questions worth flagging:

- **Opt-out flag.** Currently default-on with no escape hatch. If a user has reason to skip slash commands (collision with another tool, minimalism), they have no flag for it. Worth adding `--without-commands` if anyone asks; not worth pre-empting.
- **Other agents.** Codex CLI, Cursor, etc. have their own command/prompt mechanisms. The current code guards on `agent.key == "claude"`, so nothing breaks — but the same catch-up prompt could be re-rendered for other ecosystems once their command formats are pinned down. Tracking this against the existing AGENTS.md convergence question.

Natural follow-on commands (not built, just sketched): `/devlog-write` to nudge an entry mid-session, `/devlog-status` to report on missing-but-warranted entries, `/devlog-search <query>` to grep the archive for prior context.

## Surprises

The install loop turned out simpler than I expected. I'd planned a per-command registration list in code (one entry per slash command, like `AGENTS` in `agents.py`), but realized partway through that globbing the templates directory and copying every `.md` file does the same job with less ceremony — and means adding a new slash command later is one file, not one file plus a code edit. That's the kind of mechanism the rest of devlog already favors (templates are data, code is the glue), so leaning into it kept the diff small. The whole feature added roughly 60 lines across `__init__.py` and `manifest.py` plus the template and tests.
