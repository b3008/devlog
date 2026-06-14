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
- `devlog upgrade` (0.3.0) — two-layer self-upgrade: upgrades the tool binary (via `_detect_install_method`), then re-invokes the *freshly installed* binary as a subprocess to resync the repo's convention. `--check`/`--project-only`/`--tool-only`. Subprocess seams (`_run_tool_upgrade`, `_run_resync`, `_query_version`) are isolated for monkeypatched tests. `__main__.py` is the `python -m devlog_cli` fallback entry point.

## Recurring themes

- **Stable surface + adaptive surface.** The sentinel block is pinned and idempotent; `learned.md` and discovered tags carry anything that would otherwise make re-installs noisy. When adding new adaptivity, prefer pointers to external files over dynamic rendering into the sentinel block.
- **Case-study-driven design.** Feature additions on this project tend to come from observing the convention fail on a real project, rather than from up-front speculation. That framing belongs in blog entries when it applies.
- **Self-referential dogfooding.** devlog is installed on itself, so its own blog is both a test bed and a live example. Entries here should read as genuine project reflections, not demos.
- **Canonical public positioning (README, 2026-06-13):** lead with the durable, git-versioned, cross-agent *why-record* as the real product; the portfolio blog is its human-facing rendering. Capture is framed as best-effort (firmer with the `Stop` hook), never infallible. Keep messaging consistent with this ordering. The README's most persuasive copy is its most candid — an adversarial honesty-skeptic pass improved it by *removing* marketing (cut "walk away with four things", "Every … is captured", "navigable").
- **Dogfooding the warm path.** Self-installing devlog on this repo doesn't exercise cold-start failure modes — this repo always has scaffolding present. New surfaces (slash commands, hooks) need explicit cold-repo verification or external review (e.g. PR #9's Copilot review caught the missing-scaffolding gap that local dogfooding could not).
- **"Trivial" is about reusable insight, not diff size.** A one-line README logo swap (2026-06-13) looked too small to log, but it carried a design *decision* (four candidate fonts → ANSI Shadow) and a reusable method (deterministic ASCII via `uvx pyfiglet`, which sidesteps the LLM alignment failure mode of hand-rolled art). The Stop hook caught the skip. When judging triggers, weigh the insight that would be lost, not the size of the change.
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
- Auto-resync via hooks: recommended against and not built (mid-session CLAUDE.md mutation, surprise VCS diffs, CLI-on-PATH assumption). The accepted model is reinstall-as-upgrade with `status` flagging drift; revisit only if users demonstrably don't run the resync. **Update 2026-06-14:** `devlog upgrade` (0.3.0) now packages reinstall-as-upgrade into one *user-invoked* command (still not a hook) — tool bump + resync-via-re-invoked-binary. The hook objection stands; this is the explicit-command alternative.
- CLI logo drift: `devlog version`/`status`/`init`/`upgrade` print the old half-block `LOGO` (in `__init__.py`), but the README now uses the ANSI Shadow wordmark (2026-06-13). Unify on next housekeeping pass — note ANSI Shadow is 6 rows, taller in terminal output.
- Version discipline now matters: `__version__`/pyproject must be bumped when templates or the convention change, or the 0.2.0 version-stamp machinery reports nothing. No enforcement exists (a CI check comparing template hashes against the last release could provide it).
- Evidence frontmatter (`commit:`/`files:` on entries) was in the 06-11 Tier-1 list but silently fell out of the 06-12 implementation batch — a live example of a dropped thread that only a manual sweep caught. Still unbuilt; also the mechanization manicure's "drifted" category needs.
- PR #7 (Surprises section, 2026-04-18) has been open ever since although its content shipped long ago — stale; close or rebase on next housekeeping pass.
- Remaining 06-12 expansion threads (not yet built): `superseded_by:` frontmatter/tooling (the convention rule shipped; tooling didn't); shrink the *global* convention toward a lazy-loading stub (the thin local block shipped — global text is still full-size); knowledge-placement policy section (project facts → learned.md, not private harness memory); decision register (formalize Open threads into live/superseded status); epoch distillation for retrieval past ~20 entries. Voice is NOT the problem — agent consumption of the narrative entries worked well; retrieval is.

## Resolved (kept for the record)

- 2026-06-12 (second pass): version-aware installs — bumped to 0.2.0, sentinel now carries a version stamp (`<!-- DEVLOG:START v0.2.0 ... -->`, prefix-matching keeps old blocks parseable), manifest version finally meaningful, and `devlog status` reports drift (older install version, unstamped block, artifacts differing from shipped templates) with `devlog install` as the upgrade command.

- 2026-06-12 shipped, in one pass (branch `assessment-tier1`): exit-0 structured block channel for the Stop hook (red box was self-inflicted protocol mixing); global path fix `~/CLAUDE.md` → `~/.claude/CLAUDE.md` with legacy migration; thin local block when a global install is detected (+ `--full`); `manifest.hooks` sha256 + carry-forward + customization preservation; runtime global-defers-to-local for both hooks (ends double reminders); `devlog index` (generated `_index.md`, convention step 6 updated); SessionEnd → `sessions.jsonl` coverage + `status` reporting; convention steps 7 (supersession annotation) and 8 (commit the entry); media defaults swapped to agent-feasible artifacts.
