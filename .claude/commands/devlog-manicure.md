---
description: Audit past devlog entries for what carried through, was revised, or quietly died — write a recap entry, then propose dated annotations or wipes for the user to approve. Optionally pass a topic to scope the manicure (e.g. /devlog-manicure slash commands).
---

Manicure the devlog. This is a multi-phase command — work through each phase in order, and pause for user input where indicated. Do not edit existing entries until Phase 4, and only with explicit approval.

## Resolve paths

Before doing anything else, resolve the blog directory and index file from `.devlog/config.yaml` if it exists:

- `<blog_dir>` is the `blog_dir` value (default: `blog`).
- `<index_file>` is the `index_file` value (default: `_index.md`).

Use these resolved paths for every reference below.

## Preflight

If `<blog_dir>/` does not exist, or it has fewer than two entries (excluding `<index_file>`), there is nothing meaningful to manicure (a manicure pass needs a small history to audit). Report that briefly and stop. Suggest the user run `/devlog-write <topic>` to start producing entries, and try again once a few have accumulated. Do not scaffold anything.

Otherwise, proceed.

## Scope

Topic argument (may be empty): $ARGUMENTS

- **If empty** — manicure the whole blog. Audit, recap, and propose revisions across every entry.
- **If non-empty** — scope the manicure to entries that touch the given topic. Treat the topic broadly: include entries that mention it directly, that depend on it, or that contradict/supersede it. Decide entry-by-entry whether it's in scope; cite your inclusion criteria briefly at the start of Phase 1 so the user can correct your read of the topic before you spend cycles on the audit.

In topic-scoped mode, every phase below narrows accordingly: the audit only categorizes findings related to the topic, the recap entry is a topic-specific recap (suggested slug `recap-<topic-kebab>`, not `recap-so-far`), and proposed revisions are confined to the in-scope entries.

## Phase 1 — Audit

Read, in chronological order (oldest first):

1. Every entry in `<blog_dir>/` (skip `<index_file>`).
2. `.devlog/learned.md`.
3. `.devlog/config.yaml` for the current canonical sections, voice, and tag vocabulary.

For each entry, capture:
- Stated "What's next" items, open threads, and unresolved questions.
- Design decisions, feature claims, and architectural assertions.
- Predictions or expectations about future behavior.

Then cross-reference across the timeline. Categorize findings into at least these buckets — and add your own categories where the corpus warrants:

- ✅ **Followed through** — a "what's next" or open thread that became a later entry. Link the originating entry to the resolving one.
- 📝 **Elaborated** — a topic given deeper treatment in a later entry. Surface the through-line.
- 🔄 **Revised** — a feature or decision that survived but in a meaningfully different shape than originally described.
- ❌ **Discarded** — a feature or idea that was dropped, reversed, or explicitly rejected later.
- 🌫️ **Silent** — a topic raised once and never revisited. Flag as "may be dead, may be quietly resolved" — leave the call to the user.
- ⚠️ **Drifted** — claims in older entries that newer entries contradict (architecture moved, vocabulary changed, file paths renamed or deleted, behavior altered).
- 🏷️ **Tag inconsistency** — tags used in ways that don't match the current `.devlog/config.yaml` vocabulary, or that have evolved in meaning.

Generate your own categories where useful — examples to consider, not a closed list:
- **Scope creep traces** — entries that quietly expanded the project's stated scope.
- **Audience drift** — voice that wandered from the project's stated voice guidelines.
- **Promise vs. delivery gaps** — explicit "we will" statements with no follow-up.
- **Vocabulary churn** — terms used inconsistently across entries (worth normalizing into `learned.md`).

Report the audit as a structured table or grouped list. Cite entry filenames for every finding. Be concrete — quote the original phrasing when relevant.

## Phase 2 — Recap entry

Write a new blog entry that acts as a recap. Use the standard format (filename `YYYY-MM-DD-NN-slug.md`, ISO `timestamp`, etc.). Tag with `documentation` plus anything else that fits.

- **Whole-blog mode**: suggested slug `recap-so-far` or `state-of-the-project`. The entry is a state-of-the-project reflection.
- **Topic-scoped mode**: suggested slug `recap-<topic-kebab>` (e.g. `recap-slash-commands`). The entry is a focused arc of how this one topic evolved across the project.

Cover:
- **Where things are now** — a paragraph on current state (of the project, or of the topic).
- **What stuck** — features and decisions that survived multiple sessions.
- **What changed** — revisions and pivots, with one-line explanations.
- **What was dropped** — discarded ideas, with brief rationale.
- **Through-lines** — recurring themes worth naming.

Write as a first-hand reflection, not a changelog. Then add the entry to the top of `<blog_dir>/<index_file>`.

## Phase 3 — Propose revisions

Present a numbered list of suggested revisions to existing entries, grouped by entry. Each suggestion specifies:

- **#N**
- **Entry**: filename
- **Type**: `wipe` (remove or rewrite outdated content) or `annotate` (add a dated callout)
- **Location**: section name and a short quote of the affected text
- **Proposed change**: the exact text you would write or the exact text you would remove

For **annotations**, default to a visible blockquote callout placed immediately after the affected paragraph:

```markdown
> **Update YYYY-MM-DD**: <what changed and why, with a link to the resolving entry if applicable>.
```

If the user prefers invisible HTML comments instead, switch to:

```markdown
<!-- update YYYY-MM-DD: <note> -->
```

For **wipes**, prefer rewriting over deletion when the surrounding context still matters — e.g., replace "we will add X next" with "X was added in [entry YY]". Only delete outright when the content is purely misleading and not load-bearing for narrative.

Use today's date (`date "+%Y-%m-%d"`) for all `YYYY-MM-DD` placeholders in annotations.

## Phase 4 — Apply

Wait for the user to approve specific suggestions by number, range, or "all". Apply only the approved edits. Do not edit anything proactively.

After applying:
- Report which files were modified and which suggestions were applied vs. declined.
- If any durable lesson emerged from the manicure pass — a recurring failure mode in the convention, a vocabulary normalization worth keeping — append it tersely to the appropriate section of `.devlog/learned.md`.
- If the recap entry itself surfaced new open threads, add them to the **Open threads** section of `learned.md` as well.

If the user declines all suggestions, that's fine — the recap entry alone is a useful artifact. Confirm completion either way.
