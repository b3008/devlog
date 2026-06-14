---
title: "The README finally states the thesis: why-record first, blog as rendering"
date: 2026-06-13
timestamp: 2026-06-13T12:19:42
tags: [documentation, ux, research]
summary: "Added 'Why devlog?' and 'What you get' sections to the README, leading with the durable cross-agent why-record as the real product — drafted via a judge-panel-plus-honesty-skeptic workflow that caught three overclaims before they shipped."
---

## What changed

The README had a tight two-line hook but never developed the *why*. The
project's actual thesis — articulated in the [06-11 assessment](2026-06-11-01-agent-codebase-assessment.md)
and `learned.md`, but never on the front door — was that devlog's real output
isn't the blog; it's the durable, git-versioned, **cross-agent record of why
the code is the way it is**, of which the portfolio blog is a rendering.

Two new sections now carry that, placed between the table of contents and
Quickstart (and added to the TOC):

- **`## Why devlog?`** — the why-record thesis up front; the "premise holds
  harder for agent-written code" three-item list (the reasoning never lived in
  your head / commits carry the *what* not the *why* / native agent memory is
  private, unversioned, harness-bound); the write-trigger relocation; and an
  honest best-effort caveat scoped to the Claude-Code `Stop` hook.
- **`## What you get`** — concrete outcomes (surviving why-record, cross-agent
  institutional memory via `learned.md` + `/devlog-catchup`, onboarding,
  durability with no lock-in, portfolio byproduct, self-maintenance), capped by
  a four-row comparison table against commit-driven journals, changelog
  generators, and manual diaries.

## Why it matters

This is a positioning decision, not just copy: the front door now **leads with
the why-record as the product and frames the blog as its rendering**, the order
both the assessment and `learned.md` rank it. Anyone evaluating the project —
or any future session writing about it — now inherits that framing from the
README instead of having to reconstruct it from the blog corpus.

## How it works

Drafted with a small `Workflow`: three agents each wrote the sections from a
distinct angle (institutional-memory-first, sustainability/trigger-first,
results-first), then a skeptical-editor judge ranked them, extracted the
strongest phrasings, and — the point of the exercise — flagged overclaims
against the project's "honest about tradeoffs" ethos. I synthesized the final
from Draft 1's spine + Draft 2's sharpest one-liners + Draft 3's comparison
table.

The honesty pass earned its keep. It caught three things I'd likely have shipped:

- **"Run it once and you walk away with four things"** — front-loaded certainty
  before the best-effort caveat; cut wholesale.
- **"Every non-trivial decision… is captured"** — "Every" overclaims for
  best-effort capture; softened to "Decisions, tradeoffs, and dead ends get
  captured… as they happen."
- **"A durable, navigable *why*"** — "navigable" was an unsupported
  marketing-adjacent adjective (nothing offers search/navigation yet); cut.

## Surprises

The single best line in the whole set was an honesty move, not a sales one:
*"`devlog status` reports when sessions ended without producing an entry — so
the blind spot is at least visible."* It turns a genuine weakness (capture
isn't guaranteed) into a named, observable property. The skeptic explicitly
protected it. Worth remembering that on this project the most persuasive copy
tends to be the most candid — the adversarial editor improved the marketing by
*removing* the marketing.

## What's next

- The comparison table makes the support-tiering question (F11) more visible by
  contrast — still the lone open README call from the audit.
- "Navigable" was cut because it isn't true *yet*; retrieval/search past ~20
  entries remains a Tier-2 thread. If it ships, the word earns its place back.
