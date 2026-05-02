---
title: "Third slash command: /devlog-manicure for auditing and pruning the blog"
date: 2026-05-02
timestamp: 2026-05-02T10:24:35
tags: [feature, cli, ux, architecture]
summary: "A four-phase /devlog-manicure [topic] command audits past entries for what carried through, was revised, or quietly died, writes a recap entry, and proposes dated annotations or wipes for the user to approve before applying. Optional topic argument scopes the audit to a single thread."
---

## What changed

A third slash command, `/devlog-manicure [topic]`, shipped at `src/devlog_cli/templates/commands/devlog-manicure.md`. It accepts an optional topic argument via `$ARGUMENTS`: with no argument it audits the whole blog; with an argument (`/devlog-manicure slash commands`) it scopes every phase to entries that touch that topic. It runs in four phases:

0. **Scope** — declare whether this is a whole-blog manicure or topic-scoped, and (if scoped) cite the inclusion criteria the agent will use to decide which entries are in scope. Lets the user correct a misread of the topic before the audit work begins.
1. **Audit** — read every (in-scope) entry, `learned.md`, and `config.yaml` in chronological order. Categorize findings into ✅ followed-through, 📝 elaborated, 🔄 revised, ❌ discarded, 🌫️ silent, ⚠️ drifted, 🏷️ tag-inconsistent, plus agent-generated categories ("scope creep traces", "audience drift", "promise vs. delivery gaps", "vocabulary churn"). Report with filename citations.
2. **Recap entry** — write a state-of-the-project entry (whole-blog mode, slug `recap-so-far`) or a topic-arc entry (scoped mode, slug `recap-<topic-kebab>`) covering what stuck, what changed, what was dropped, and through-lines. Add to the index.
3. **Propose revisions** — present a numbered list of suggested edits to in-scope entries, each tagged `wipe` (rewrite or remove outdated content) or `annotate` (add a dated callout). Default annotation format is a visible blockquote `> **Update YYYY-MM-DD**: …`; HTML comments are an opt-in alternative for users who want them invisible.
4. **Apply** — wait for explicit approval (by number, range, or "all"), apply only those edits, then optionally append durable lessons to `learned.md`.

No installer code changed — same drop-in template pattern as `/devlog-catchup` and `/devlog-write`. Tests in `TestSlashCommands` extended (new `test_manicure_command_file_created`, manifest and install-message assertions cover all three names, idempotency expects 3 files now). 97/97 passing.

## Why it matters

The first three commands form a coherent loop: `/devlog-catchup` reads the blog into context, `/devlog-write` adds new entries, and `/devlog-manicure` prunes and reflects on what's already there. A blog without manicure inevitably drifts — predictions stop matching reality, "what's next" lists fossilize, vocabulary forks, features get rewritten without the original entry being updated. Without a maintenance pass, the blog's value as a context-loading surface degrades over time.

The optional topic argument matters because whole-blog manicures get expensive fast as the archive grows — and most maintenance moments are local, not global. The user notices a specific thread is stale ("did the AGENTS.md-native idea ever go anywhere?", "what's the current state of slash commands?") and wants to audit and recap *that*, not the whole project. Topic-scoping makes those small, frequent passes cheap, while whole-blog mode stays available for deliberate state-of-the-project reflections.

`/devlog-manicure` makes that maintenance an explicit, on-demand operation rather than something the agent should do continuously (which would be both expensive and high-risk). It's also the first command that proposes destructive edits — and so it's also the first that requires explicit approval before acting. That bright line keeps trust intact: the agent never silently overwrites narrative the user wrote.

The dated annotation pattern (`> **Update YYYY-MM-DD**: …`) is worth flagging on its own. It treats the blog like a Wikipedia article rather than a changelog: original content stays intact and visible, with timestamped corrections layered on top. A reader scrolling the entry sees both the original framing and what later happened, with the dates making the temporal structure obvious. That preserves the first-hand voice of the original entry — which the convention specifically asks for — while still letting the project's accumulated knowledge update the historical record honestly.

## How it works

The prompt is structured but not rigid. Each phase has explicit deliverables, but the categorization in Phase 1 invites the agent to generate its own buckets where the corpus warrants — the closed list (followed-through, elaborated, revised, etc.) is a floor, not a ceiling. That matches a recurring pattern in this project's design: ship a strong default, but build in escape hatches for cases the default doesn't cover.

A few opinionated choices in the prompt worth flagging:

- **Wipe prefers rewrite over deletion.** "We will add X next" should become "X was added in entry YY", not vanish — the through-line is more useful than a clean slate.
- **Use `date` for the timestamp on annotations**, same as `/devlog-write`. Removes ambiguity about timezone and format.
- **Phase 4 is gated on explicit approval.** "Wait for the user to approve specific suggestions by number, range, or 'all'." Without this, the command would slide from "audit and propose" into "audit and apply" — a much riskier operation.
- **Failure modes are surfaced into `learned.md`**, not just the recap entry. If the manicure pass reveals a recurring failure in the convention itself (an entire class of "what's next" items that never get followed up, say), that's a project-knowledge insight worth keeping outside the blog's narrative arc.

The recap entry generated in Phase 2 is itself a regular blog entry — same filename format, same frontmatter, same convention. So `/devlog-manicure` doesn't introduce a new entry type, it just nudges the agent to write a particular kind of entry that's hard to write spontaneously (because it requires the wide-scan view of the whole archive).

## What's next

This is now the full set of slash commands shipping in the first cut: read (`catchup`), write (`write`), prune (`manicure`). The natural next steps:

- **Run `/devlog-manicure` on this project** to dogfood it. Today already produced 4 entries; tomorrow's first session is a good moment to test the audit pass against a small but real corpus.
- **Decide whether the recap entry should have its own subtype** in the convention. Currently it's just a regular entry tagged `documentation`. A dedicated tag like `recap` could surface them faster in the index — worth considering after a few real recap entries exist to compare.
- **Surface dated annotations in tooling.** A future `devlog status` could count entries that have post-hoc annotations, giving a rough measure of how "live" the archive is vs. how much is frozen.

## Surprises

The hardest part of writing this prompt was deciding what *not* to include. The temptation was to enumerate every category of finding, every annotation style, every edge case — and the prompt would have ballooned past usefulness. Cutting back to a strong default-plus-extension-points structure (named categories, plus "add your own where the corpus warrants"; default annotation format, plus an opt-in alternative) made the prompt readable and gave the agent room to use judgment. That's a recurring shape on this project: the convention block, the config file, the templates directory — all of them ship strong defaults with a single named extension point, not a forest of knobs. The slash commands are evolving the same way.
