---
title: "Second slash command: /devlog-write for on-demand entries"
date: 2026-05-02
timestamp: 2026-05-02T10:17:16
tags: [feature, cli, ux]
summary: "A new /devlog-write <topic> slash command lets the user explicitly request an entry about anything, validating the drop-in extensibility of the templates/commands/ pattern shipped earlier today."
---

## What changed

A second slash command, `/devlog-write`, shipped at `src/devlog_cli/templates/commands/devlog-write.md`. It takes a free-form topic via Claude Code's `$ARGUMENTS` substitution — `/devlog-write the new caching layer we shipped` — and instructs the agent to load context (config, learned.md, recent entries), compute the next per-day `NN` and ISO timestamp, derive a kebab-case slug, write the entry following this project's convention, and update `_index.md` plus `learned.md` if anything durable surfaced.

Crucially, **no install code changed**. The earlier `_install_claude_commands()` helper globs every `.md` in `templates/commands/`, so dropping a new template was the entire diff (template + tests). The install tree now reports both commands:

```
├── Installed slash command /devlog-catchup (.claude/commands/devlog-catchup.md)
├── Installed slash command /devlog-write   (.claude/commands/devlog-write.md)
```

Tests in `TestSlashCommands` extended: a new `test_write_command_file_created`, `test_manifest_records_command` now asserts both names are tracked, `test_install_message_lists_command` checks both are surfaced, and the idempotency test now expects 2 files instead of 1. 96/96 passing.

## Why it matters

Two related things:

1. **The user now has both ends of the loop.** `/devlog-catchup` reads the blog into context; `/devlog-write` pushes new context into the blog. Together they make the blog a working memory the user can interact with directly, not just a passive artifact the agent maintains in the background.

2. **The drop-in extensibility shipped this morning was the right call.** When the templates-as-data pattern was chosen for `_install_claude_commands()` (see entry 02 today), it was a small bet — globbing `*.md` instead of registering each command in code. The bet paid off within hours: this entire feature was a template file plus test additions, no installer logic touched. That's a good signal that future commands (`/devlog-status`, `/devlog-search`, etc.) will land at the same low cost.

The `$ARGUMENTS` mechanism is also the first time devlog leans on a Claude-Code-specific feature beyond the file-drop convention. That couples the slash command surface a little more tightly to Claude than the convention block is — but the coupling is honest: slash commands are inherently agent-specific, and pretending otherwise would mean shipping a worse UX to be portable to ecosystems that may never adopt the same convention.

## How it works

The template's body uses `$ARGUMENTS` as a literal token. When the user types `/devlog-write the caching layer`, Claude Code substitutes the rest-of-line into the body before sending it to the agent. The agent then follows the prompt's five steps: load context → compute filename and timestamp → write the entry → update index + learned.md → report back.

The prompt is opinionated about a few things worth flagging:

- **Defer to `.devlog/config.yaml`** for sections, voice, and tags — not assumed defaults. The convention can be customized per project; the slash command should respect that without re-implementing the renderer.
- **First-hand voice enforced.** If the topic refers to in-session work, narrate from session memory. If not, ask the user for context rather than reconstruct from commits — same rule as the "first-hand, not reconstructed" voice guideline added in the survey-driven update.
- **Refuse vague input.** If `$ARGUMENTS` is empty or too thin to write meaningfully, ask one clarifying question instead of fabricating. Keeps the slash command from polluting the blog with low-signal entries.

The shell-out to `date` for timestamp and date-string is deliberate — the agent can compute these but `date` is unambiguous about timezone (local) and format (ISO 8601 to seconds), and it removes a small source of drift between entries.

## What's next

This is now the full set of slash commands worth shipping in the first cut. Sketched but not built:

- **`/devlog-status`** — agent-side mirror of `devlog status`, but answering "is there an entry I should be writing right now?" rather than "are the install files present."
- **`/devlog-search <query>`** — grep the blog for prior context on a topic and summarize. Useful for "have I dealt with this before?" loops.

Both wait for a real felt need rather than speculation. The drop-in pattern means either is a one-template change when the time comes.

## Surprises

Nothing this round — the work was a clean test of the prior session's design. That's worth noting on its own: when a feature lands without surprises, it usually means the underlying abstraction was correctly shaped. The interesting moment was the *absence* of installer changes, which confirmed the `_install_claude_commands()` glob was the right granularity and not premature generality.
