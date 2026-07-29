---
type: "Devlog Entry"
title: "Blog entries now conform to the Open Knowledge Format"
date: 2026-06-17
timestamp: 2026-06-17T13:16:32
tags: [feature, architecture, cli, documentation]
description: "Made devlog entries valid OKF concept documents, added a self-healing `devlog migrate` command, and wired auto-migration into install."
---

## What changed

Google published the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) (OKF v0.1) — a vendor-neutral spec for representing knowledge as directories of markdown files with YAML frontmatter, so AI agents can read, cross-reference, and update each other's knowledge bundles. A devlog *is* exactly that shape already, so conforming was mostly a matter of aligning field names and the index.

The work landed in one pass (v0.4.1 → **0.5.0**):

- **New entries are born conformant.** The frontmatter template gained `type: "Devlog Entry"` (OKF's one required field) as the lead key, and `summary` was renamed to OKF's canonical `description`. Both the in-source `DEFAULT_CONFIG` and the shipped `templates/config.yaml` carry the new list.
- **The index became an OKF bundle root.** `_index.md` → `index.md` (OKF reserves the bare name), and `build_index()` now emits a `--- okf_version: "0.1" ---` frontmatter block — the one place OKF permits frontmatter on an index. The heading-preservation scan learned to skip a leading frontmatter block.
- **`devlog migrate`** — a new, idempotent command that brings an *existing* blog into conformance: backfills `type`, renames `summary`→`description`, renames the index, stamps `okf_version`, and rewrites `.devlog/config.yaml` (both `index_file` and the `frontmatter` list). `--check` previews.
- **Self-detection + auto-run.** A shared `plan_migration()` planner is the single source of truth for "does this blog need migrating?". `devlog install` runs it and auto-migrates before regenerating the convention; `devlog status` reports conformance (`OKF: v0.1 conformant` or the specific gaps).

This repo dogfooded it: 27 entries backfilled, `blog/_index.md` renamed via `git mv` (history preserved), config rewritten.

```
$ devlog status
Blog: blog/ — 27 entries, most recent 2026-06-17
OKF: v0.1 conformant
```

## Why it matters

OKF's only hard requirement is a non-empty `type` field per document — everything else is recommended and consumers must tolerate its absence. So conformance was cheap, but the *payoff* is real: a devlog becomes readable by any OKF-aware tool or agent, not just devlog's own commands. The blog stops being a devlog-specific artifact and becomes a portable knowledge bundle, which is squarely on this project's "durable, cross-agent, no lock-in" thesis.

The second half — "can devlog know by itself and run migrate?" — is the more interesting design move. A format change to a *tool used by many projects* is worthless if every existing blog has to be migrated by hand. `install` is already the upgrade path (`/devlog-upgrade` runs it), so folding auto-migration there means a legacy blog heals itself the moment its owner next upgrades — no new ritual to learn. This is also the project's first real **schema-migration story**, which [an earlier open thread](2026-06-12-04-version-aware-status.md) flagged as missing.

## How it works

Detection and execution share one planner so they can't drift:

```
plan_migration(root, config) → MigrationPlan
   .entry_changes   # per-file: "added type", "summary→description"
   .index_rename    # an index exists under a non-OKF name
   .index_needs_stamp
   .config_update / .config_frontmatter_update
   .needed          # any of the above
```

`migrate`, `install`, and `status` all call it; `_apply_migration()` mirrors its decisions when writing. Two design choices kept the migration safe:

- **Raw-text frontmatter edits, not YAML round-trips.** `migrate_entry_text()` operates on the frontmatter *lines* — inserting `type` and renaming the `summary:` key — so field order, comments, and quoting survive untouched. A `yaml.safe_load` → `yaml.dump` would have reformatted all 27 entries and stripped the `# ISO 8601…` comment.
- **`git mv` with a plain-rename fallback** for the index, so history follows the file in a repo and the command still works outside one.

The config's `frontmatter` list needed migrating too — easy to miss. The convention an agent reads is *generated from* that list, so a stale list would keep producing non-conformant entries even after the existing ones were fixed. Caught it while verifying, not while designing.

## What's next

- The **global** `~/.claude/CLAUDE.md` convention block is still v0.4.1 (`summary`, `_index.md`). Since this repo uses the thin block that defers to global, the *active* instruction an agent sees won't carry the new template until `devlog install --ai claude --global --with-hook` is re-run. That's a one-liner but touches the user's global config across all projects, so it's left as an explicit step.
- OKF supports a richer cross-link graph between concepts; devlog entries only link on supersession today. A future pass could auto-link related entries (shared tags, referenced files) to make the bundle a real graph.
- `resource:` is legitimately omitted (entries describe abstract work, not physical assets), but a per-entry `resource:` pointing at the commit or PR is a plausible future addition.

## Surprises

The gap was almost entirely *naming*, not structure — devlog had been accidentally ~90% OKF-shaped since the start (markdown + frontmatter + a generated index + per-file concepts). The one genuine structural snag was the index filename: `_index.md` is *not* an OKF reserved name, so a strict consumer would treat it as a concept document missing its `type` — the leading underscore, chosen long ago to sort the index first, was the single thing making the bundle non-conformant.
