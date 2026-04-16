---
title: "Making the convention adaptive: learned.md + tag discovery"
date: 2026-04-16
tags: [architecture, feature, cli]
summary: "The injected convention no longer freezes at install time — it grows with the project via an agent-maintained notebook and a self-updating tag vocabulary."
---

## What changed

`devlog install` used to render `.devlog/config.yaml` into a static markdown
block and drop it between sentinel markers in the agent's context file. That
block was the convention, verbatim, forever — until someone hand-edited
`config.yaml` and ran install again. Two new mechanisms change that:

- **`.devlog/learned.md`** — an agent-maintained notebook with sections for
  glossary, entities, recurring themes, and open threads. The injected
  convention now instructs the agent to read it before writing each entry
  and append to it when durable project knowledge emerges.
- **Tag discovery on install** — a new `discover_tags()` helper scans
  `blog/*.md`, parses the YAML frontmatter, and returns every tag it finds.
  On each `devlog install` those tags are unioned with the base vocabulary
  from `config.yaml` before the convention is rendered. The CLI reports
  newly discovered tags in the install tree.

## Why it matters

The original design had one knob: `config.yaml`. If the agent discovered
domain vocabulary worth naming, or the user coined a new tag that stuck,
there was nowhere for that knowledge to land without someone editing the
config and re-running install. In practice, that means the knowledge
doesn't land at all.

A tempting fix was to render more dynamic content into the sentinel block
itself — recent tags, active areas, glossary snippets. That was rejected:
it breaks sentinel idempotence, makes `CLAUDE.md` diffs noisy, and turns
the injected block from a stable contract into a log.

The accepted approach splits the surface in two. The sentinel block stays
pinned to `config.yaml` (stable, human-reviewable). `learned.md` is the
agent's scratchpad, living outside the sentinels so it can accumulate
without triggering re-installs. Tag discovery is the one exception: it
feeds back into the sentinel block, but only on explicit `install` runs, so
the timing is always deterministic.

Neither mechanism requires the user to curate anything. Together they let
the convention absorb what the project has actually been doing.

## How it works

`learned.md` ships as a template with four `##` sections. `init` copies it
to `.devlog/learned.md`; `install` backfills it for users upgrading from
pre-learned.md versions. Humans can edit it; the agent treats it as a
shared notebook and is specifically told to keep additions terse.

`discover_tags()` lives in `convention.py`. It globs `blog/*.md`, skips the
index file, and tries to parse YAML frontmatter with a tolerant extractor
(missing or malformed frontmatter silently yields no tags rather than
raising). The result is a sorted list; `install` unions it with
`config["tags"]` before calling `generate_convention`. Newly-discovered
tags — ones not already in `config.yaml` — are called out in the Rich
tree:

```
Installing devlog convention — Claude Code
├── Discovered 2 new tag(s) from entries: new-tag-here, observability
├── Injected convention into CLAUDE.md
└── Manifest saved
```

A matching paragraph in the convention tells the agent it may introduce
new tags in entry frontmatter when they genuinely fit, and that the next
install will fold them into the canonical vocabulary.

## What's next

The open question is whether agents actually *use* `learned.md` in
practice, or whether it gets written once and quietly ignored. A future
`devlog status` iteration could surface freshness — when was `learned.md`
last touched, is it still empty, is it diverging from what entries
actually talk about — but that's speculative until there's usage data
from more than one project.
