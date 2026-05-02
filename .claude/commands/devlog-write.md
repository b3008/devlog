---
description: Write a new devlog blog entry about a specific topic. Pass the topic as an argument, e.g. /devlog-write the new caching layer we shipped this morning.
---

Write a new devlog blog entry about: $ARGUMENTS

If the argument is empty or too vague to write a meaningful entry, ask one clarifying question instead of fabricating content. Otherwise, proceed.

## Preflight — bootstrap the project if needed

Check whether the devlog scaffolding exists in this project:

- If `.devlog/config.yaml`, `blog/`, and `blog/_index.md` are all present, skip this section and go to Step 1.
- If any are missing, the project hasn't been initialized yet. Resolve in this order:
  1. If a global devlog convention is loaded (look for a "First-time setup" subsection in the active CLAUDE.md), follow its bootstrap instructions: create `blog/`, `blog/media/`, `.devlog/`, `blog/_index.md` (heading = project directory name), and `.devlog/learned.md` (with section headings: Glossary, Entities, Recurring themes, Open threads).
  2. Otherwise, run `devlog init` if the `devlog` CLI is on PATH.
  3. Otherwise, ask the user to run `devlog init` and stop here — do not write a half-scaffolded entry.

Once scaffolding exists, proceed.

## Step 1 — Load context

1. Read `.devlog/config.yaml` to get this project's current sections, voice guidelines, tags, and frontmatter fields. The convention may be customized; defer to the config over your prior assumptions.
2. Read `.devlog/learned.md` for project-specific vocabulary, entity names, recurring themes, and open threads. Reuse established terms.
3. Read `blog/_index.md` and the 1–2 most recent entries to match the established voice, structure, and level of detail. Avoid repeating points already covered there.

## Step 2 — Compute filename and timestamp

1. Run `date "+%Y-%m-%d"` for today's date.
2. Run `date "+%Y-%m-%dT%H:%M:%S"` for the ISO 8601 local timestamp.
3. List `blog/` and find existing files matching `YYYY-MM-DD-*` for today's date. Pick the next available zero-padded `NN` (start at `01` if none exist; otherwise increment past the highest).
4. Derive a short kebab-case `slug` from the topic — 2–5 words, descriptive but compact.

The new entry's filename is `blog/YYYY-MM-DD-NN-slug.md`.

## Step 3 — Write the entry

Use the frontmatter and sections defined in this project's CLAUDE.md (rendered from `.devlog/config.yaml`). Always include the `timestamp` field. Pick tags from the available list; introduce a new tag only if it genuinely fits and recurs.

Write from first-hand knowledge:
- If the topic refers to work done in this session, narrate from what you observed — reasoning, alternatives considered, surprises.
- If the topic refers to work outside this session's context, ask the user for the relevant background before writing — do not reconstruct from commit messages or guesswork.

Skip any sections that don't apply. Keep the voice consistent with recent entries.

## Step 4 — Update the index and learned.md

1. Add the new entry to the top of `blog/_index.md` in the existing format.
2. If durable project knowledge emerged from this entry — a new term worth naming, a pattern, an open thread — append it tersely to the appropriate section of `.devlog/learned.md`. Do not duplicate what's already there.

## Step 5 — Report back

Confirm the entry path, the chosen `NN`, and a one-line summary of what was written. If you appended anything to `learned.md`, mention what.
