---
title: "Copilot review catches the slash commands' missing-scaffolding gap"
date: 2026-05-02
timestamp: 2026-05-02T11:43:18
tags: [bug-fix, ux, research]
summary: "GitHub Copilot's review of the README documentation PR flagged that /devlog-write would fail in any fresh repo with only the global install — the command bodies assumed scaffolding existed. Each command got a preflight section; /devlog-write now bootstraps on first use, the read-only commands exit gracefully."
---

## What changed

PR #9 (the README documentation pass) drew an automated Copilot review with one substantive comment on the new Slash commands section:

> This section implies the slash commands are immediately usable in any Claude Code session, including after `--global` installs, but the shipped command bodies don't self-bootstrap a project. For example, `/devlog-write` starts by reading `.devlog/config.yaml`, `.devlog/learned.md`, and `blog/_index.md`, so in a fresh repo that only has the global install these commands won't work until the project has already been scaffolded by `devlog init` or an automatic first entry.

That was correct. The fix landed in PR #10 — three template edits and one README clarification:

- **`/devlog-catchup`** — read-only. New preflight detects missing `blog/` (or empty `blog/`), reports "no devlog yet", points at `/devlog-write`, and exits. Does not scaffold.
- **`/devlog-write`** — new preflight bootstraps the project in priority order:
  1. If a global CLAUDE.md "First-time setup" subsection is loaded, follow it (creates `blog/`, `blog/media/`, `.devlog/`, `blog/_index.md` with project-name heading, and `.devlog/learned.md`).
  2. Else run `devlog init` if the CLI is on PATH.
  3. Else ask the user to run `devlog init` and stop. No half-scaffolded entries.
- **`/devlog-manicure`** — needs ≥2 entries to do meaningful work. Reports "nothing to manicure" and exits otherwise.
- **README** — added a paragraph under the Slash commands section so the docs match: `/devlog-write` bootstraps; the others are read-only and exit cleanly.

97/97 tests still pass — the preflight content is prompt text, not asserted by the test suite (the existing `test_*_command_file_created` checks confirm structural markers like "Phase 1" and "$ARGUMENTS" but don't enforce specific bullet content).

## Why it matters

Two things, one operational and one about the project itself.

**Operational**: the bug only affected the path that's most visible to new users. Anyone running `devlog install --ai claude --global` and immediately trying `/devlog-write topic` in any of their projects would see a confusing chain of file-not-found errors instead of a working blog. The whole point of `--global` is "every project gets a blog without per-project setup" — so a slash command that requires per-project setup before it works is a contradiction with the install mode's pitch. Fixing it preserves the global-install promise.

**About the project**: this was the first review-driven bug fix on devlog. Earlier work was internal critique (the landscape survey) or live dogfooding (the convention rewording from a case study). PR #9 was small enough that I assumed a doc change had no risk surface — and Copilot's review was the only thing that pointed at the real surface, which was the implicit *contract* between the README and the shipped templates. The doc said one thing; the templates did another. That class of bug — "the docs lie about the binary" — is exactly what an external reviewer is well-suited to catch, because they read both sides cold.

Worth keeping that in mind for future PRs that look "trivial". A README change that documents existing behavior carries an asymmetric risk: if the docs and the binary drift, the docs are usually wrong (the binary's been tested by users; the docs haven't).

## How it works

The fix is structural, not clever. Each command template now has a `## Preflight` section (or for the manicure command, a similar early gate inside its existing structure) that runs before any reads. The agent checks for the relevant scaffolding files and either bootstraps, exits gracefully, or asks the user.

The bootstrap path in `/devlog-write` is interesting because it explicitly defers to the global CLAUDE.md's "First-time setup" subsection. That subsection was added in the [global install entry from 2026-04-17](2026-04-17-global-install.md) — it tells the agent to scaffold `blog/`, `.devlog/`, and `learned.md` on its first entry in any project. The slash command can lean on that work without re-implementing it: "follow the bootstrap instructions you already have." That keeps the bootstrap logic in one place (the convention) and the slash commands as light pointers into it.

The trade-off the preflight adds: a tiny latency cost on every invocation (the agent has to check a few file paths before doing real work). For commands that already do substantial reads, that's noise. For `/devlog-write` specifically, it also means the agent needs to look at the active CLAUDE.md when the scaffold is missing — a slightly more involved check than just reading a file. Worth it, given the alternative is silent failure.

## What's next

The preflight pattern is now consistent across all three commands, so future commands inherit it for free. Two follow-ups worth flagging:

- **Test coverage for preflight**: the existing tests assert structural markers in the command bodies but don't try to simulate "what happens when the agent runs this prompt against a fresh repo." That's hard to unit-test (it's prompt content, not Python) but a manual verification checklist in the README's "How it works" section might help.
- **`devlog doctor`**: a CLI command that surfaces the same kind of "is this project set up correctly?" check from outside the agent loop. The slash commands handle the in-session case; a `doctor` command would handle the cold-start case where a user wants to verify the install before invoking anything.

## Surprises

The Copilot review arrived faster than I expected — within seconds of the PR opening, fully formed, citing the exact file paths and the exact failure mode. I'd treated the slash command templates as "shipped, working, dogfooded on this very project" — but the project they were dogfooded on (this repo) already had a fully scaffolded `blog/` and `.devlog/`. The dogfood didn't exercise the cold-start path because the dogfood environment isn't cold. That's a recurring failure mode worth naming: **"dogfooding the warm path"** — when the test environment doesn't reproduce the conditions that matter for new users. Adding to `.devlog/learned.md` as a recurring theme.
