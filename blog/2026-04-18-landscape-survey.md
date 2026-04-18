---
title: "Landscape survey: who else is doing automatic dev journals?"
date: 2026-04-18
tags: [architecture, research]
summary: "A critical review of every comparable project we could find — commit-driven journals, changelog generators, markdown diary conventions, and agent-context standards — and what devlog should (and shouldn't) borrow from each."
---

## What changed

We ran a broad internet search for projects that overlap with devlog's goal: automatically producing a narrative, portfolio-ready development log. The results fell into five distinct categories, each with different tradeoffs. This entry catalogues every notable find, critiques it, and extracts lessons for devlog.

## The landscape

### 1. Commit-driven AI journals

**[DevDiary](https://devdiary.me/)** watches commits, PRs, and code reviews, clusters them into "work sessions," and generates a daily narrative page with AI summaries and diffs.

**[DevLog by zeshama](https://dev.to/zeshama/devlog-i-built-an-ai-powered-developer-journal-that-turns-git-commits-into-stories-3fdl)** feeds commit messages into an LLM and exports Markdown or JSON summaries.

**[AI Commit (`aic`)](https://russmckendrick.medium.com/introducing-ai-commit-68ec32716a6a)** rewrites commit messages and generates PR descriptions from a branch's commit history.

**Critique.** These tools work *after* the fact — they reconstruct narrative from commit metadata that was never written to carry narrative weight. The quality ceiling is the commit message. If commits are terse (`fix bug`, `wip`), the AI hallucinates context or produces bland summaries. More fundamentally, commits describe *what changed in code*, not *why a decision was made*, what alternatives were considered, or what the developer learned. The narrative is always reconstructed, never observed firsthand.

**What to borrow.** DevDiary's "session clustering" is smart — grouping related commits into a coherent work unit is something devlog gets for free (one agent session ≈ one work unit) but could lose if sessions become very long. If devlog ever needs to break a marathon session into multiple entries, session-boundary detection is worth studying.

**What to avoid.** Commit-message dependence. devlog's agent *is* the author, present during the work. It should never fall back to summarising its own commits — that would throw away its primary advantage.

### 2. Changelog generators

**[conventional-changelog](https://github.com/conventional-changelog/conventional-changelog)**, **[semantic-release](https://github.com/semantic-release/semantic-release)**, **[git-cliff](https://git-cliff.org/)**, **[auto-changelog](https://github.com/cookpete/auto-changelog)**.

A mature ecosystem. All require conventional commits or tags, and all produce structured release notes — bullet lists of features, fixes, and breaking changes.

**Critique.** Changelogs serve a fundamentally different audience (users upgrading) than dev journals (collaborators, evaluators, the developer's future self). The output is deliberately impersonal, scope-limited, and version-gated. A changelog that reads like a blog post is a bad changelog; a blog post that reads like a changelog is a bad blog post.

**What to borrow.** Tag vocabularies and the concept of a canonical, auto-extending taxonomy. devlog already does this with tag discovery, but the conventional-commits ecosystem proves the pattern scales. Also worth noting: these tools *enforce* structure at the commit level, which creates a flywheel — structured input makes structured output cheap. devlog could consider whether to nudge the agent toward structured session summaries (not commits) that feed into richer entries.

**What to avoid.** Version-gating. devlog entries should be tied to *sessions and decisions*, not releases. Tying entries to semver would make the blog go silent during long development stretches — exactly when a journal is most valuable.

### 3. Manual markdown journal conventions

**[Mark Erikson's Daily Work Journal](https://blog.isquaredsoftware.com/2020/09/coding-career-advice-daily-work-journal/)** — one file per day, freeform markdown, kept for personal retrospection.

**[Tom Cooper's git+markdown diary](https://tomcooper.dev/posts/2020-04-11-simple-text-diary/)** — bash script that creates a dated file and opens it in an editor.

**[Megadix's Markdown Journal](https://www.megadix.it/blog/keep-markdown-journal-get-your-projects-done/)** — structured templates for project tracking.

**[Flow / Developer Diary by Invide](https://flow.invidelabs.com/)** — minimalist privacy-focused journal app with markdown support.

**Critique.** These validate the *desire* — many developers want a work journal and know it would be valuable. But they all rely on discipline the developer doesn't have, which is why almost every article about keeping a dev diary opens with "I abandoned mine after two weeks." The format insights are real; the sustainability model is broken.

**What to borrow.** Mark Erikson's emphasis on recording *what you learned* and *what confused you*, not just what you shipped. devlog's convention currently biases toward "What changed / Why it matters / How it works" — all outward-facing. A "What I learned" or "Surprises" section could add real retrospective value without much cost. Worth proposing as an optional section in `config.yaml`.

**What to avoid.** Requiring human discipline as the write trigger. That's the whole point of devlog — the agent is the disciplined narrator. Any feature that shifts authorship burden back to the developer undermines the core proposition.

### 4. Agent-context standards

**[AGENTS.md](https://agents.md/)** (~60k repos) — a simple markdown file in the repo root that any coding agent reads for project conventions.

**[CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)** — Claude Code's project-specific context file, read automatically at session start.

**[agent-rules-skill](https://github.com/netresearch/agent-rules-skill)** — a Claude Code skill that generates AGENTS.md files.

**[OpenClaw's bootstrap files](https://www.stack-junkie.com/blog/openclaw-system-prompt-design-guide)** — SOUL.md, TOOLS.md, AGENTS.md injected into the system prompt.

**Critique.** These are devlog's *substrate*, not its competitors. AGENTS.md and CLAUDE.md solved "how do I give persistent instructions to an agent?" — devlog answers "what instructions should you give if you want a dev journal?" The interesting question is whether devlog's sentinel-block injection is the right integration pattern long-term. AGENTS.md is heading toward a world where agents read a single shared file; devlog currently needs per-agent injection because context files differ. If the ecosystem converges on AGENTS.md as the universal standard, devlog should converge with it.

**What to borrow.** The AGENTS.md spec's simplicity. devlog's `config.yaml` → rendered convention pipeline is more complex than it probably needs to be for most users. A mode where devlog just appends a well-crafted section to AGENTS.md (no YAML, no renderer) could lower the barrier.

**What to avoid.** Coupling too tightly to any single agent's file format. The 27-agent support matrix is a strength — but maintaining per-agent rendering paths that diverge will become expensive. Better to treat them all as "markdown file with sentinel block" and keep the rendered convention identical.

### 5. GitHub Agentic Workflows

**[gh-aw](https://github.com/github/gh-aw)** — describe desired outcomes in markdown, run them as agent-driven GitHub Actions workflows.

**Critique.** This is infrastructure, not a journal tool, but it represents a future where devlog-like behaviour could be triggered *by the platform* rather than injected into the agent's context. Imagine a GitHub Action that runs after every PR merge and asks an agent to write a blog entry about the change. That's a plausible alternative architecture — and one that doesn't require the developer to have devlog installed locally.

**What to borrow.** The CI/CD trigger model. devlog currently relies on the agent noticing its own triggers in-session. A complementary "post-merge hook" mode — where a lightweight CI job calls an LLM to draft an entry from the PR description and diff — could catch work that slipped through (e.g., quick manual fixes without an agent session).

**What to avoid.** Making CI the *primary* authorship path. An agent writing from a PR diff is back to the commit-driven problem — reconstructed narrative, not observed narrative. CI-triggered entries should be a safety net, not the main pipeline.

## The gap devlog occupies

No project we found does what devlog does: inject a self-adapting convention into the agent's own context so the agent narrates its work *as it happens*, with first-person knowledge of the reasoning, alternatives considered, and tradeoffs made.

Every other approach either:
- reconstructs narrative post-hoc from commit/PR metadata (lossy),
- requires human discipline to write (unsustainable), or
- provides agent-context infrastructure without opinionated content (substrate only).

The closest conceptual neighbour is DevDiary, but it's commit-driven and SaaS — not a portable convention you install once and forget.

## What's next

Three ideas surfaced from this survey worth exploring:

1. **Optional "Surprises" section** — borrowed from the manual-journal tradition. Let agents note what was unexpected or confusing, not just what shipped.
2. **CI safety-net mode** — a lightweight post-merge hook that drafts an entry when no agent session produced one, preventing gaps in the journal.
3. **AGENTS.md-native mode** — a simpler injection path for the growing number of agents that read AGENTS.md, reducing devlog's per-agent maintenance burden.
