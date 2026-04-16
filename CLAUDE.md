<!-- DEVLOG:START - Do not edit this section manually -->
## Development Blog (Automatic)

This project keeps a development blog in `blog/`. **Before ending any response in which non-trivial work was produced**, check whether the session hit one of the triggers below. If it did, write or update the blog entry as part of the same turn — don't defer it to a future session and don't wait to be asked.

### When to write an entry

- New feature or command implemented
- Significant bug fix or refactor
- Architecture decision made
- Notable technical challenge solved
- Template or workflow changes

If none of these triggers match the kind of work happening in this project, the defaults are wrong for this domain. Propose edits to `.devlog/config.yaml` that fit this project — at minimum the `triggers` list, and likely `voice` and `tags` too — apply them once the user approves, and ask the user to re-run `devlog install` so this convention block regenerates.

### Project context (read first, extend over time)

Before writing an entry, read `.devlog/learned.md`. It holds project-specific vocabulary, entity names, recurring themes, and open threads that previous sessions have accumulated. Use what's there to stay consistent with prior entries.

When durable project knowledge emerges during the session — a new domain term worth naming, a pattern seen across multiple sessions, a tension or decision worth remembering — append it to the appropriate section of `.devlog/learned.md`. Keep additions terse; this file is a shared notebook, not a changelog.

### How to write an entry

1. Create a file: `blog/YYYY-MM-DD-slug.md`
2. If multiple entries share a date, append a number: `YYYY-MM-DD-slug-2.md`
3. Use this frontmatter template:

```yaml
---
title: "Short descriptive title"
date: YYYY-MM-DD
tags: [relevant, tags, from-list-below]
summary: "One-sentence summary of what was accomplished and why it matters."
---
```

4. Structure the body with these sections (skip any that don't apply):
   - **What changed** — concrete description of what was built/fixed
   - **Why it matters** — significance for the project, users, or architecture
   - **How it works** — brief technical explanation (portfolio audience: technical but not necessarily familiar with the codebase)
   - **What's next** — open threads or future directions

5. **Capture rich media** — screenshots and visuals are critical for portfolio impact:
   - Take screenshots of CLI output, generated files, or workflow artifacts
   - Save media to `blog/media/YYYY-MM-DD-slug/` (matching the entry filename)
   - Reference in markdown as `![Alt text](media/YYYY-MM-DD-slug/filename.png)`
   - If screenshots aren't feasible, add a `<!-- TODO: screenshot -->` placeholder

6. Update `blog/_index.md` — add the new entry to the list at the top.

### Voice and audience

- **Portfolio-oriented**: write for someone evaluating the work (potential collaborators, employers, researchers, or AI agents picking up the project later)
- **Narrative, not changelog**: explain the *why* and *so what*, not just the *what*
- **Concrete over abstract**: reference specific files, show output examples, describe real problems solved
- **Honest about tradeoffs**: mention what didn't work, what was scrappy, what's still rough

### Available tags

`architecture`, `cli`, `feature`, `bug-fix`, `refactor`, `testing`, `documentation`, `infrastructure`, `ux`, `demo`

Prefer tags from this list. If a new tag genuinely fits and recurs, use it in the entry's frontmatter — it will be folded into this list automatically on the next `devlog install`.
<!-- DEVLOG:END -->
