---
type: "Devlog Entry"
title: "A sharper README wordmark — and why I stopped hand-rolling ASCII art"
date: 2026-06-13
timestamp: 2026-06-13T11:53:29
tags: [documentation, ux]
description: "Replaced the hand-tweaked half-block DEVLOG logo with figlet's ANSI Shadow font, generated deterministically via uvx pyfiglet — and let the Stop hook talk me out of treating a design decision as trivial."
---

## What changed

The README's masthead used a hand-rolled half-block wordmark:

```
  ██▀▄ █▀▀ █ █ █   ▄▀▄ ▄▀▀
  █  █ █▀  ▀▄▀ █   █ █ █ █
  ▀▀   ▀▀▀  ▀  ▀▀▀  ▀  ▀▀▀
```

It read as DEVLOG, but the letterforms had been nudged into place by hand: the
`D`'s base was clipped to two cells under a four-cell top, and the `L` was
cramped against its neighbours. It's now the **ANSI Shadow** figlet font — the
de-facto standard for polished CLI-tool READMEs:

```
██████╗ ███████╗██╗   ██╗██╗      ██████╗  ██████╗
██╔══██╗██╔════╝██║   ██║██║     ██╔═══██╗██╔════╝
██║  ██║█████╗  ██║   ██║██║     ██║   ██║██║  ███╗
██║  ██║██╔══╝  ╚██╗ ██╔╝██║     ██║   ██║██║   ██║
██████╔╝███████╗ ╚████╔╝ ███████╗╚██████╔╝╚██████╔╝
╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝ ╚═════╝  ╚═════╝
```

Six rows, ~51 single-width columns, even baseline, consistent stroke weight.
Stays inside the centered `<div>` and renders the same on GitHub and in a
terminal.

## How it works

The interesting part isn't the font — it's the generation method. There's no
`figlet`/`toilet` on this machine, but `pyfiglet` bundles the fonts and runs
with zero install through the same `uvx` the project already leans on:

```bash
uvx pyfiglet -f ansi_shadow "DEVLOG" | sed 's/[[:space:]]*$//' | sed '/^$/d'
```

Before settling, I rendered DEVLOG across ~30 fonts (ANSI Shadow, Pagga,
Calvin S, `future`, DOS Rebel, Electronic, …) and offered four cleaned-up
directions to pick from. Deterministic generation matters here for a reason
worth naming: **hand-crafted ASCII art is a genuine LLM failure mode.**
Alignment is per-character, monospace-fragile, and easy to get subtly wrong —
exactly the kind of thing that looks fine in isolation and breaks when you
count cells. Letting `pyfiglet` own the letterforms removes that whole class of
error; my job shrinks to curation and trimming trailing whitespace.

## Surprises

I'd written this off as a trivial cosmetic tweak and explicitly *skipped* the
blog entry, reasoning that a logo swap matches none of the five triggers. The
Stop hook pushed back — "decisions count, not only code" — and it was right.
A design decision *was* reached: four candidate directions narrowed to one, plus
a reusable method (deterministic ASCII via `pyfiglet`) that this project will
reach for again. That's the convention's adaptive surface doing its job on its
own repo: the eager trigger caught an output-size bias I'd have otherwise
encoded as "too small to log." Worth remembering that "trivial" is about
reusable insight, not diff size.

## What's next

- Optional: lowercase `devlog` to match how the command is actually invoked —
  a one-character regenerate (`-f ansi_shadow "devlog"`).
- A commit-graph accent line (`●─●─●─●─`) under the wordmark would nod at the
  time-ordered-log concept; deferred as a nice-to-have, not shipped.

> **Update 2026-06-14**: this swap only touched the README; the CLI kept
> printing the old half-block art (the `LOGO` constant in `__init__.py`, shown by
> `devlog version`/`upgrade`), which surfaced as a drift thread while shipping
> [`devlog upgrade`](2026-06-14-01-devlog-upgrade-command.md). Now unified — the
> CLI prints the same ANSI Shadow wordmark (6 rows, so taller terminal output;
> no test pinned the art). Both surfaces match.
