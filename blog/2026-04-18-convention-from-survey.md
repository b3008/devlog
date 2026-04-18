---
title: "Applying the landscape survey: new section, voice rule, and tag"
date: 2026-04-18
tags: [feature, architecture]
summary: "Three concrete lessons from the competitive survey — a 'Surprises' section, a first-hand narration voice guideline, and a 'research' tag — folded into the default convention."
---

## What changed

The landscape survey (`2026-04-18-landscape-survey.md`) identified specific borrowable ideas from comparable projects. This session applied three of them to devlog's default convention:

1. **"Surprises" section** added to `DEFAULT_CONFIG["sections"]` — a fifth optional entry section for recording the unexpected: failed approaches, corrected assumptions, serendipitous discoveries. Inspired by the manual-journal tradition (Mark Erikson's daily work journal pattern), where the most retrospectively valuable entries were the ones about *what confused the author*, not what they shipped.

2. **"First-hand, not reconstructed" voice guideline** added to `DEFAULT_CONFIG["voice"]` — explicitly tells the agent to narrate from session-level observation (reasoning, alternatives, surprises) rather than reconstructing from commit messages or diffs. This is the survey's central finding: devlog's agent is present during the work, and the convention should tell it to exploit that advantage over commit-driven tools.

3. **`research` tag** added to `DEFAULT_CONFIG["tags"]` — the survey entry itself needed a tag that didn't exist. `documentation` was close but wrong (it implies project docs, not external investigation). Research and competitive-analysis sessions are a genuine recurring pattern.

All three changes applied to `convention.py` defaults, the template `config.yaml`, and this project's own `.devlog/config.yaml`. Running `devlog install --ai claude` regenerated the CLAUDE.md sentinel block.

## Why it matters

These are the first convention changes driven by external research rather than internal dogfooding. The survey pattern — study comparable tools, critique them, extract lessons, apply — is itself a template for how devlog's convention should evolve: case-study-driven, not speculative.

The "Surprises" section is particularly interesting because it shifts the convention from purely outward-facing (portfolio audience) to partially inward-facing (retrospective value for the developer). That dual audience — impressive to evaluators *and* useful to the author — is where dev journals become sustainable.

## How it works

No rendering logic changed. The existing convention template already says "skip any that don't apply" for sections, so the new "Surprises" section is opt-in by default. The voice guideline renders identically to the existing four (bold label, colon, description). The tag slots into the sorted vocabulary.

Files modified:
- `src/devlog_cli/convention.py` — `DEFAULT_CONFIG` dictionary (sections, voice, tags)
- `src/devlog_cli/templates/config.yaml` — template for `devlog init`
- `.devlog/config.yaml` — this project's live config

## What's next

Two ideas from the survey remain unimplemented:
- **CI safety-net mode** — a post-merge hook that drafts entries when no agent session produced one. Requires its own design cycle (which LLM to call, GitHub Action template, new CLI command).
- **AGENTS.md-native mode** — deferred because the current architecture already handles AGENTS.md agents with identical rendering. Worth revisiting if agent context file formats diverge.

## Surprises

The "AGENTS.md-native mode" idea from the survey turned out to be a non-issue on closer inspection. The blog entry theorized about "per-agent rendering paths that diverge," but reading the actual code revealed that all 27 agents already get the identical rendered convention — only the target file path differs. The concern was about a problem that doesn't exist yet. Good reminder to read the code before designing solutions.
