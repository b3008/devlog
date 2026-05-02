# Project knowledge

<!--
This file is maintained by the AI agent as it works on the project.
It accumulates context that didn't fit in the stable convention:
domain vocabulary, entity names, recurring themes, open questions.

Humans can edit it freely. The agent should read it before writing
a blog entry and append to it when new durable context emerges.
-->

## Glossary

- **Sentinel block** — the `<!-- DEVLOG:START -->` / `<!-- DEVLOG:END -->`-wrapped section injected into an agent's context file. Must stay deterministic so re-installs produce clean diffs.
- **Convention** — the markdown text rendered from `config.yaml` and dropped inside the sentinel block.
- **Tag discovery** — the install-time scan of `blog/*.md` frontmatter that unions discovered tags into the rendered vocabulary.
- **Self-tailoring** — the convention's instruction to the agent to propose `config.yaml` edits when the defaults don't fit the project's domain.

## Entities

- `.devlog/config.yaml` — user-owned stable configuration (triggers, voice, tags, frontmatter, media).
- `.devlog/learned.md` — this file. Agent-owned adaptive surface.
- `.devlog/manifests/<agent>.manifest.json` — SHA-256 tracking per agent install. Includes `hooks` and `commands` arrays.
- `convention.py` — renderer plus `discover_tags()` and `scan_entries()` helpers.
- `manifest.py` — install manifest model. Kept intentionally small.
- `templates/commands/*.md` — slash command bodies, copied into `.claude/commands/` on Claude installs. Drop-in: any new `.md` here gets installed automatically.

## Recurring themes

- **Stable surface + adaptive surface.** The sentinel block is pinned and idempotent; `learned.md` and discovered tags carry anything that would otherwise make re-installs noisy. When adding new adaptivity, prefer pointers to external files over dynamic rendering into the sentinel block.
- **Case-study-driven design.** Feature additions on this project tend to come from observing the convention fail on a real project, rather than from up-front speculation. That framing belongs in blog entries when it applies.
- **Self-referential dogfooding.** devlog is installed on itself, so its own blog is both a test bed and a live example. Entries here should read as genuine project reflections, not demos.
- **Dogfooding the warm path.** Self-installing devlog on this repo doesn't exercise cold-start failure modes — this repo always has scaffolding present. New surfaces (slash commands, hooks) need explicit cold-repo verification or external review (e.g. PR #9's Copilot review caught the missing-scaffolding gap that local dogfooding could not).

## Landscape / competitors

- **Commit-driven journals** (DevDiary, DevLog-by-zeshama, AI Commit) — reconstruct narrative post-hoc from git metadata. Lossy by design; quality capped by commit message quality.
- **Changelog generators** (conventional-changelog, git-cliff, semantic-release) — structured release notes, not narrative. Different audience (upgraders vs. evaluators).
- **Manual markdown diaries** — validate demand but fail on sustainability (human discipline as write trigger).
- **Agent-context standards** (AGENTS.md, CLAUDE.md) — devlog's substrate, not competitors. AGENTS.md convergence trend worth tracking.
- **GitHub Agentic Workflows (gh-aw)** — platform-triggered agent tasks; plausible alternative trigger model for devlog entries.

## Open threads

- Does the agent actually read and extend `learned.md` over time, or does it get written once and ignored? Needs real usage data.
- A future `devlog doctor` or extended `status` could surface `learned.md` freshness, but it's premature without evidence that the file drifts.
- Claude Code `Stop` hooks as an enforcement mechanism for the "write-in-same-turn" rule remain the obvious next enhancement if the reworded convention proves insufficient.
- Six pre-2026-05-02 entries still use the old `YYYY-MM-DD-slug.md` format and lack the `timestamp` frontmatter field. Backfill vs. leave-as-legacy is an open call.
- `manifest.hooks` doesn't carry a `sha256` (unlike `files` and now `commands`). Same drift/customization/overwrite failure mode applies to the Stop hook script. Fix when next touching that surface.
- Manifest schema is now versioned-by-shape (old records lack `sha256` on commands; new records have it). Next schema change should think about an explicit migration story rather than relying on the loader's fallback to absent fields.
