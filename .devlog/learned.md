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
- **Defensive code introduces new failure surfaces.** Each "make this safer" pass on the install pipeline (PR #10 preflight, PR #11 hashing/reconciliation) introduced its own bugs that the next Copilot round caught. The pattern: new I/O without `try/except`, new schema fields without explicit encoding, new walks that assume the package is intact. Treat every defensive addition as a new failure site that itself needs testing.

## Landscape / competitors

- **Commit-driven journals** (DevDiary, DevLog-by-zeshama, AI Commit) — reconstruct narrative post-hoc from git metadata. Lossy by design; quality capped by commit message quality.
- **Changelog generators** (conventional-changelog, git-cliff, semantic-release) — structured release notes, not narrative. Different audience (upgraders vs. evaluators).
- **Manual markdown diaries** — validate demand but fail on sustainability (human discipline as write trigger).
- **Agent-context standards** (AGENTS.md, CLAUDE.md) — devlog's substrate, not competitors. AGENTS.md convergence trend worth tracking.
- **GitHub Agentic Workflows (gh-aw)** — platform-triggered agent tasks; plausible alternative trigger model for devlog entries.

## Open threads

- Does the agent actually read and extend `learned.md` over time, or does it get written once and ignored? `sessions.jsonl` (shipped 2026-06-12) now provides the denominator; needs accumulation time before it answers anything.
- A future `devlog doctor` or extended `status` could surface `learned.md` freshness, but it's premature without evidence that the file drifts.
- Six pre-2026-05-02 entries still use the old `YYYY-MM-DD-slug.md` format and lack the `timestamp` frontmatter field. Backfill vs. leave-as-legacy is an open call. (`devlog index` handles both formats.)
- Manifest schema is now versioned-by-shape (old records lack `sha256`; new records have it — true for both `commands` and, since 2026-06-12, `hooks`). Next schema change should think about an explicit migration story rather than relying on the loader's fallback to absent fields.
- Hybrid mutation-gated hook (loud block on mutation turns, silent `additionalContext` otherwise): protocol-verified possible (Stop hooks get `transcript_path`, support exit-0 block JSON and `additionalContext`), exit-0 fix shipped 2026-06-12, `sessions.jsonl` measurement shipped same day. Build only if coverage data shows the always-block reminder is being ignored. Unverified: whether Stop hooks fire in headless `claude -p` mode — docs are silent.
- Remaining 06-12 expansion threads (not yet built): `superseded_by:` frontmatter/tooling (the convention rule shipped; tooling didn't); shrink the *global* convention toward a lazy-loading stub (the thin local block shipped — global text is still full-size); knowledge-placement policy section (project facts → learned.md, not private harness memory); decision register (formalize Open threads into live/superseded status); epoch distillation for retrieval past ~20 entries. Voice is NOT the problem — agent consumption of the narrative entries worked well; retrieval is.

## Resolved (kept for the record)

- 2026-06-12 shipped, in one pass (branch `assessment-tier1`): exit-0 structured block channel for the Stop hook (red box was self-inflicted protocol mixing); global path fix `~/CLAUDE.md` → `~/.claude/CLAUDE.md` with legacy migration; thin local block when a global install is detected (+ `--full`); `manifest.hooks` sha256 + carry-forward + customization preservation; runtime global-defers-to-local for both hooks (ends double reminders); `devlog index` (generated `_index.md`, convention step 6 updated); SessionEnd → `sessions.jsonl` coverage + `status` reporting; convention steps 7 (supersession annotation) and 8 (commit the entry); media defaults swapped to agent-feasible artifacts.
