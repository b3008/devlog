---
title: "Per-day index in filenames + ISO timestamp in frontmatter"
date: 2026-05-02
timestamp: 2026-05-02T10:04:53
tags: [feature, architecture]
summary: "Entry filenames now carry a zero-padded per-day index (YYYY-MM-DD-NN-slug.md) and frontmatter gains an ISO 8601 timestamp, so entries sort deterministically and intra-day order is preserved."
---

## What changed

Two related additions to the entry-writing convention:

1. **Filename pattern** moved from `YYYY-MM-DD-slug.md` to `YYYY-MM-DD-NN-slug.md`. The `NN` is a zero-padded per-day index starting at `01`. Old rule: append `-2` only on collision. New rule: index is always present, picked by scanning `blog/` for the date and incrementing past the highest existing number.
2. **`timestamp` frontmatter field** — ISO 8601 local time (`YYYY-MM-DDTHH:MM:SS`) captured at the moment the entry is written. The `date` field still exists; `timestamp` adds intra-day precision.

The change touched three config sources (`convention.py` `DEFAULT_CONFIG`, `templates/config.yaml` for new projects, `.devlog/config.yaml` for this project), plus the rendered "How to write an entry" steps in `generate_convention()`. Re-running `devlog install --ai claude` regenerated this project's `CLAUDE.md` with the new instructions.

## Why it matters

Until now, entries from the same day had no canonical order. The first-collision-gets-no-suffix, second-gets-`-2` rule put the *original* entry chronologically *after* the supposedly-newer `-2` under lexical sort — confusing for anyone glancing at `ls blog/` or for tooling that relies on filename ordering. With `NN` always present and starting at `01`, lexical sort matches creation order on disk.

The `timestamp` field is independently useful: it captures *when in the day* a session happened, which `date` alone can't. For a workflow where multiple entries land on the same day — common when a single morning produces several decisions — that distinction matters for retrospection. Sorting by `timestamp` across the whole blog is also more honest than sorting by filename, because filename order is per-day-relative.

The two together give devlog two complementary ordering surfaces: filenames for quick visual scanning, frontmatter timestamp for precise programmatic sort.

## How it works

The convention text in step 1 now reads:

> Create a file: `blog/YYYY-MM-DD-NN-slug.md` — `NN` is a zero-padded per-day index (`01`, `02`, ...). Scan `blog/` for existing files matching the date and pick the next available number; start at `01` if none exist.

Step 2 instructs the agent to set `timestamp` to the current local time in ISO 8601. The frontmatter template now includes:

```yaml
timestamp: YYYY-MM-DDTHH:MM:SS  # ISO 8601 local time, captured when the entry is written
```

No code changed beyond the config defaults and the rendered step text — the existing `scan_entries()` regex (`^(\d{4}-\d{2}-\d{2})-`) still matches both old and new filename formats, so backwards compatibility is automatic. Tag discovery and the sentinel-injection pipeline didn't need touching. All 87 existing tests pass without modification.

This entry is the first written under the new format: filename ends in `-01-…`, frontmatter carries `timestamp: 2026-05-02T10:04:53`.

## What's next

Existing entries (six files dated 2026-04-16 through 2026-04-18) still use the old `YYYY-MM-DD-slug.md` format and lack `timestamp`. Migrating them would mean renames plus an `_index.md` update — mechanical but touches every old file. Open question: leave them as legacy, or backfill so the whole archive is uniform. No decision yet; flagging it for the next session that touches the blog.

Optional follow-ups if this proves useful:
- A `devlog new` helper that picks the next `NN` and stamps the current time, so the agent doesn't have to compute either by hand.
- A `devlog doctor` check that flags entries missing `timestamp` or with malformed `NN`.

## Surprises

The change was smaller than I expected. I'd budgeted for tests breaking — `scan_entries()` parses filenames and I assumed it would need a regex update. It didn't: the existing regex anchors only on the leading `YYYY-MM-DD-`, which `YYYY-MM-DD-NN-…` still satisfies. The new format slots in without touching the parser. A reminder that the convention surface (what we ask the agent to write) and the parser surface (what we read back from disk) are coupled less tightly than they look — the regex is permissive enough to absorb format drift, which is probably the right default for a project meant to evolve.
