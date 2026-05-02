---
description: Read the project's devlog (blog/) and learned.md to gain context on recent decisions, work, and open threads.
---

Read the devlog and report back so the rest of this session has full context for what we've been working on.

## Preflight

If `blog/` does not exist, or it exists but has no entries beyond `_index.md`, this project does not have a devlog yet. Report that briefly and stop — there is nothing to catch up on. Suggest the user run `/devlog-write <topic>` if they want to start one (which will scaffold the project on first use). Do not scaffold anything yourself; this command is read-only.

Otherwise, proceed.

## Steps

1. Read `blog/_index.md` to see the entry list.
2. Read the 5 most recent entries (or all of them if fewer than 5).
3. Read `.devlog/learned.md` for accumulated project knowledge — glossary, entities, recurring themes, open threads.

Then summarize in this order:

- **Project arc** — a short paragraph on what this project is and where it's been going, based on the recent entries.
- **Recent work** — bullet list of the last 3–5 significant changes or decisions, each with a one-line takeaway and the entry filename in parentheses.
- **Open threads** — anything flagged as unresolved, deferred, or "what's next" across the entries and learned.md.
- **Glossary highlights** — domain vocabulary worth knowing (only include if `learned.md` has a non-trivial glossary).

Stay close to what's actually in the files — cite entry filenames so the user can dig into anything that catches their eye. Do not make changes; this is a context-loading command, not a work command.
