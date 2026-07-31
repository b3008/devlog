"""
Convention text generator for devlog.

Reads .devlog/config.yaml and produces the blog convention markdown
that gets injected into agent context files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from devlog_cli._version import __version__

# The start sentinel carries the version that wrote the block, so staleness is
# visible to anyone reading the file. Backward compatible: matching uses the
# prefix marker below, and removal tolerates anything before the closing -->.
SENTINEL_START = (
    f"<!-- DEVLOG:START v{__version__} - Do not edit manually. "
    "Remove with: devlog uninstall --ai <key> -->"
)
SENTINEL_END = "<!-- DEVLOG:END -->"

# Stable substrings for matching — immune to sentinel wording changes.
_SENTINEL_START_MARKER = "<!-- DEVLOG:START"
_SENTINEL_END_MARKER = "<!-- DEVLOG:END"

_SENTINEL_VERSION_RE = re.compile(r"<!-- DEVLOG:START v([0-9A-Za-z.\-+]+)")

# ── Open Knowledge Format (OKF) conformance ───────────────────────────────
# Blog entries are OKF "concept documents": markdown files whose YAML
# frontmatter carries a non-empty `type` (OKF's one required field). The
# bundle-root index declares the format version via `okf_version`.
# Spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
OKF_VERSION = "0.1"
OKF_INDEX_FILE = "index.md"  # OKF reserves the bare `index.md` filename.
DEFAULT_ENTRY_TYPE = "Devlog Entry"


def sentinel_version(content: str) -> str | None:
    """Extract the version stamp from a devlog sentinel block, if present.
    Pre-0.2.0 blocks carry no stamp and return None."""
    m = _SENTINEL_VERSION_RE.search(content)
    return m.group(1) if m else None

DEFAULT_CONFIG: dict[str, Any] = {
    "blog_dir": "blog",
    "media_dir": "blog/media",
    "file_pattern": "YYYY-MM-DD-NN-slug.md",
    "index_file": "index.md",
    "sections": [
        {"name": "What changed", "description": "concrete description of what was built/fixed"},
        {"name": "Why it matters", "description": "significance for the project, users, or architecture"},
        {"name": "How it works", "description": "brief technical explanation (portfolio audience: technical but not necessarily familiar with the codebase)"},
        {"name": "What's next", "description": "open threads or future directions"},
        {"name": "Surprises", "description": "anything unexpected — a search that led to an insight, an approach that failed, a misconception corrected (skip if the session was routine)"},
    ],
    "voice": [
        "Portfolio-oriented: write for someone evaluating the work (potential collaborators, employers, researchers, or AI agents picking up the project later)",
        "Narrative, not changelog: explain the *why* and *so what*, not just the *what*",
        "Concrete over abstract: reference specific files, show output examples, describe real problems solved",
        "Honest about tradeoffs: mention what didn't work, what was scrappy, what's still rough",
        "First-hand, not reconstructed: narrate from what you observed during the session — the reasoning, the alternatives, the surprises — not from commit messages or diffs after the fact",
    ],
    "triggers": [
        "New feature or command implemented",
        "Significant bug fix or refactor",
        "Architecture or scope decision reached (even if no code changed yet)",
        "Notable technical challenge solved",
        "Template or workflow changes",
    ],
    "tags": [
        "architecture",
        "cli",
        "feature",
        "bug-fix",
        "refactor",
        "testing",
        "documentation",
        "infrastructure",
        "research",
        "ux",
        "demo",
    ],
    "frontmatter": [
        {"field": "type", "example": '"Devlog Entry"  # OKF concept type — the one field Open Knowledge Format requires'},
        {"field": "title", "example": '"Short descriptive title"'},
        {"field": "date", "example": "YYYY-MM-DD"},
        {"field": "timestamp", "example": "YYYY-MM-DDTHH:MM:SS  # ISO 8601 local time, captured when the entry is written"},
        {"field": "tags", "example": "[relevant, tags, from-list-below]"},
        {"field": "description", "example": '"One-sentence summary of what was accomplished and why it matters."'},
    ],
    "media": {
        "enabled": True,
        "instructions": [
            "Prefer artifacts you can produce from the terminal: fenced CLI output, key diffs, or Mermaid diagrams embedded directly in the entry",
            "When the user provides screenshots or images, save them to `{media_dir}/YYYY-MM-DD-NN-slug/` (matching the entry filename) and reference them as `![Alt text](media/YYYY-MM-DD-NN-slug/filename.png)`",
            "If a visual would genuinely help but can't be produced, add a `<!-- TODO: screenshot -->` placeholder rather than skipping it silently",
        ],
    },
}


def load_config(project_root: Path) -> dict[str, Any]:
    """Load .devlog/config.yaml, falling back to defaults."""
    config_path = project_root / ".devlog" / "config.yaml"
    config = dict(DEFAULT_CONFIG)
    if config_path.exists():
        user_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if user_config:
            config.update(user_config)
    return config


def _extract_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a markdown file. Returns None if absent or invalid."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None
    # Skip the opening fence
    rest = text.split("\n", 1)[1] if "\n" in text else ""
    end = rest.find("\n---")
    if end == -1:
        return None
    try:
        data = yaml.safe_load(rest[:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def scan_entries(project_root: Path, config: dict[str, Any]) -> tuple[int, str | None]:
    """Count blog entries matching the YYYY-MM-DD-slug pattern and return
    (count, most_recent_date_string). Returns (0, None) if none exist."""
    blog_dir = project_root / config["blog_dir"]
    if not blog_dir.is_dir():
        return 0, None
    index_file = config.get("index_file", OKF_INDEX_FILE)
    dates: list[str] = []
    for md in blog_dir.glob("*.md"):
        if md.name == index_file:
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-", md.name)
        if m:
            dates.append(m.group(1))
    if not dates:
        return 0, None
    return len(dates), max(dates)


def discover_tags(project_root: Path, config: dict[str, Any]) -> list[str]:
    """Scan existing blog entries and return tags found in their frontmatter."""
    blog_dir = project_root / config["blog_dir"]
    if not blog_dir.is_dir():
        return []
    index_file = config.get("index_file", OKF_INDEX_FILE)
    discovered: set[str] = set()
    for md in blog_dir.glob("*.md"):
        if md.name == index_file:
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _extract_frontmatter(text)
        if not fm:
            continue
        tags = fm.get("tags")
        if isinstance(tags, list):
            discovered.update(str(t) for t in tags if t)
    return sorted(discovered)


def build_index(
    project_root: Path, config: dict[str, Any], *, fallback_title: str | None = None
) -> tuple[str, int]:
    """Render the blog index from entry frontmatter, newest first.

    The index is fully derivable from the entries, and hand-maintaining it is
    a guaranteed merge conflict under parallel sessions/worktrees — so it is
    generated instead. Returns ``(content, entry_count)``.

    An existing index's top-level heading is preserved; otherwise a heading is
    built from ``fallback_title`` (default: the project directory name).

    The bundle-root index carries an ``okf_version`` frontmatter block — the one
    place OKF permits frontmatter on an ``index.md`` — declaring the format
    version so consumers can recognize the bundle."""
    blog_dir = project_root / config["blog_dir"]
    index_file = config.get("index_file", OKF_INDEX_FILE)

    entries: list[tuple[str, str, str, str]] = []
    for md in blog_dir.glob("*.md"):
        if md.name == index_file:
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _extract_frontmatter(text) or {}
        date = str(fm.get("date") or "")
        if not date:
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", md.name)
            date = m.group(1) if m else ""
        timestamp = str(fm.get("timestamp") or "")
        title = str(fm.get("title") or md.stem)
        entries.append((date, timestamp, md.name, title))
    entries.sort(key=lambda e: (e[0], e[1], e[2]), reverse=True)

    # Preserve an existing hand-written heading if there is one, skipping any
    # leading frontmatter block (the root index may carry `okf_version`).
    heading = None
    index_path = blog_dir / index_file
    if index_path.exists():
        try:
            raw_lines = index_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            raw_lines = []
        start = 0
        if raw_lines and raw_lines[0].strip() == "---":
            for i in range(1, len(raw_lines)):
                if raw_lines[i].strip() == "---":
                    start = i + 1
                    break
        for line in raw_lines[start:]:
            if line.startswith("# "):
                heading = line
                break
            if line.strip():
                break
    if heading is None:
        heading = f"# {fallback_title or project_root.name} — Development Blog"

    lines = [
        "---",
        f'okf_version: "{OKF_VERSION}"',
        "---",
        heading,
        "",
        "<!-- Generated by `devlog index` — newest first. Edit entries, not this list. -->",
        "",
    ]
    for date, _timestamp, name, title in entries:
        display_date = date or "undated"
        lines.append(f"- {display_date} — [{title}]({name})")
    return "\n".join(lines) + "\n", len(entries)


def migrate_entry_text(text: str, *, entry_type: str = DEFAULT_ENTRY_TYPE) -> tuple[str, list[str]]:
    """Bring one entry's frontmatter into OKF conformance. Idempotent.

    Works on the raw frontmatter lines (not a parsed-then-redumped dict) so
    existing field order, comments, and quoting survive untouched. Two edits:

      * insert a ``type`` field if absent — OKF's one required field;
      * rename a ``summary:`` key to OKF's canonical ``description:`` (skipped
        when a ``description:`` is already present, to avoid a collision).

    Returns ``(new_text, changes)``. ``changes`` is empty — and the text is
    returned verbatim — when nothing was needed or the file has no frontmatter
    (a missing frontmatter block is not malformed under OKF; it is just skipped)."""
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return text, []
    lines = text.split("\n")
    close = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == "---":
            close = i
            break
    if close is None:
        return text, []

    fm = lines[1:close]
    changes: list[str] = []
    has_type = any(re.match(r"\s*type\s*:", ln) for ln in fm)
    has_description = any(re.match(r"\s*description\s*:", ln) for ln in fm)

    new_fm = list(fm)
    if not has_description:
        for idx, ln in enumerate(new_fm):
            m = re.match(r"(\s*)summary(\s*:.*)$", ln, flags=re.DOTALL)
            if m:
                new_fm[idx] = f"{m.group(1)}description{m.group(2)}"
                changes.append("summary→description")
                break
    if not has_type:
        new_fm.insert(0, f'type: "{entry_type}"')
        changes.append("added type")

    if not changes:
        return text, []
    return "\n".join([lines[0], *new_fm, *lines[close:]]), changes


@dataclass
class MigrationPlan:
    """The work needed to bring a blog to OKF conformance, computed without
    writing anything. Shared by `devlog migrate`, `devlog status`, and the
    auto-migrate step of `devlog install` so detection and execution agree."""

    entry_changes: list[tuple[str, list[str]]] = field(default_factory=list)
    unchanged: int = 0
    current_index: str = OKF_INDEX_FILE
    index_rename: bool = False  # an index exists under a non-OKF name
    index_needs_stamp: bool = False  # index.md exists but lacks okf_version
    config_update: bool = False  # config index_file points somewhere other than index.md
    config_frontmatter_update: bool = False  # config frontmatter list lacks type / still has summary

    @property
    def needed(self) -> bool:
        return bool(
            self.entry_changes
            or self.index_rename
            or self.index_needs_stamp
            or self.config_update
            or self.config_frontmatter_update
        )


def plan_migration(project_root: Path, config: dict[str, Any]) -> MigrationPlan:
    """Inspect a blog and report what OKF migration would change. Pure: reads
    files, writes nothing. ``plan.needed`` answers "does this blog need migrating?"."""
    blog_dir = project_root / config["blog_dir"]
    current_index = config.get("index_file", OKF_INDEX_FILE)
    plan = MigrationPlan(current_index=current_index)
    skip = {current_index, OKF_INDEX_FILE}

    if blog_dir.is_dir():
        for md in sorted(blog_dir.glob("*.md")):
            if md.name in skip:
                continue
            try:
                text = md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            _, changes = migrate_entry_text(text)
            if changes:
                plan.entry_changes.append((md.name, changes))
            else:
                plan.unchanged += 1

    current_index_path = blog_dir / current_index
    target_path = blog_dir / OKF_INDEX_FILE
    plan.index_rename = current_index != OKF_INDEX_FILE and current_index_path.exists()
    if not plan.index_rename and target_path.exists():
        try:
            fm = _extract_frontmatter(target_path.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeDecodeError):
            fm = {}
        plan.index_needs_stamp = "okf_version" not in fm
    plan.config_update = current_index != OKF_INDEX_FILE

    # The convention template for NEW entries is generated from this list, so a
    # stale list (no `type`, or still using `summary`) would keep producing
    # non-conformant entries even after the existing ones are fixed.
    fm_fields = [str(f.get("field")) for f in config.get("frontmatter", []) if isinstance(f, dict)]
    plan.config_frontmatter_update = "type" not in fm_fields or "summary" in fm_fields
    return plan


def generate_convention(config: dict[str, Any], *, global_mode: bool = False) -> str:
    """Generate the blog convention markdown from config.

    When global_mode is True, the convention includes self-bootstrapping
    instructions and per-project config override guidance."""
    blog_dir = config["blog_dir"]
    media_dir = config["media_dir"]
    sections = config["sections"]
    voice = config["voice"]
    triggers = config["triggers"]
    tags = config["tags"]
    frontmatter = config["frontmatter"]
    media = config.get("media", DEFAULT_CONFIG["media"])

    # Build frontmatter example
    fm_lines = ["```yaml", "---"]
    for f in frontmatter:
        fm_lines.append(f"{f['field']}: {f['example']}")
    fm_lines.extend(["---", "```"])
    fm_block = "\n".join(fm_lines)

    # Build sections list
    section_lines = []
    for s in sections:
        section_lines.append(f"   - **{s['name']}** \u2014 {s['description']}")
    sections_block = "\n".join(section_lines)

    # Build voice list
    voice_lines = []
    for v in voice:
        voice_lines.append(f"- **{v.split(':')[0]}**:{v.split(':', 1)[1]}" if ":" in v else f"- {v}")
    voice_block = "\n".join(voice_lines)

    # Build triggers list
    trigger_lines = [f"- {t}" for t in triggers]
    triggers_block = "\n".join(trigger_lines)

    # Build tags
    tags_block = ", ".join(f"`{t}`" for t in tags)

    # Build media instructions
    media_lines = []
    if media.get("enabled", True):
        for instruction in media.get("instructions", []):
            media_lines.append(f"   - {instruction.format(media_dir=media_dir)}")
    media_block = "\n".join(media_lines)

    # Build opener — varies between per-project and global mode.
    if global_mode:
        opener = f"""\
## Development Blog (Automatic)

Every project you work on keeps a development blog in `{blog_dir}/`. **Before ending any response in which non-trivial progress was made**, check whether the session hit one of the triggers below. Progress includes decisions reached in discussion \u2014 not only code or files produced. If it did, write or update the blog entry as part of the same turn \u2014 don't defer it to a future session and don't wait to be asked.

When you write or update an entry, report it in one line \u2014 just the file path (e.g. `{blog_dir}/2026-06-14-01-slug.md`). When no entry is warranted, say nothing about the devlog at all. Don't narrate which triggers you checked, what you scaffolded, or why an entry wasn't needed.

### First-time setup (per project)

If the current project does not yet have a `{blog_dir}/` directory, scaffold it before writing the first entry:
1. Create `{blog_dir}/`, `{blog_dir}/media/`, and `.devlog/`.
2. Create `{blog_dir}/{config.get("index_file", OKF_INDEX_FILE)}` with a heading using the project\u2019s directory name.
3. Copy `.devlog/learned.md` from the template below or create an empty one with section headings: Glossary, Entities, Recurring themes, Open threads. Start it flat — one file is the right shape for most projects, and it only splits into `.devlog/knowledge/` if it outgrows the budget described under **Project context**. Create `.devlog/archive/` alongside it — resolved threads move there rather than accumulating in the live file.

If the project has a `.devlog/config.yaml`, use its settings for triggers, voice, and tags **instead of** the defaults below. If it doesn\u2019t, use the defaults."""
    else:
        opener = f"""\
## Development Blog (Automatic)

This project keeps a development blog in `{blog_dir}/`. **Before ending any response in which non-trivial progress was made**, check whether the session hit one of the triggers below. Progress includes decisions reached in discussion \u2014 not only code or files produced. If it did, write or update the blog entry as part of the same turn \u2014 don't defer it to a future session and don't wait to be asked.

When you write or update an entry, report it in one line \u2014 just the file path (e.g. `{blog_dir}/2026-06-14-01-slug.md`). When no entry is warranted, say nothing about the devlog at all. Don't narrate which triggers you checked, what you scaffolded, or why an entry wasn't needed."""

    text = f"""\
{opener}

### When to write an entry

{triggers_block}

A turn that ends on a decision \u2014 e.g., choosing one design over another, agreeing on a scope cut, naming a constraint \u2014 counts even if no code or files were touched. Write the decision now; the implementation can be a separate entry later.

If none of these triggers match the kind of work happening in this project, the defaults are wrong for this domain. Propose edits to `.devlog/config.yaml` that fit this project \u2014 at minimum the `triggers` list, and likely `voice` and `tags` too \u2014 apply them once the user approves, and ask the user to re-run `devlog install` so this convention block regenerates.

### Project context (read first, extend over time)

Before writing an entry, read `.devlog/learned.md`. It holds project-specific vocabulary, entity names, recurring themes, and open threads that previous sessions have accumulated. Use what's there to stay consistent with prior entries.

That file has two shapes, and it is the first thing you open in either one:

- **Flat** — four sections (Glossary, Entities, Recurring themes, Open threads) in the single file. This is the starting shape and the right one for most projects: read it and you have everything.
- **Indexed** — `learned.md` is a list of one-line pointers into `.devlog/knowledge/`, with Open threads still written out in full inside it. Read the index, then open **only** the topic files whose hooks relate to what you're working on. Do not load the whole directory: the index is cheap precisely so that everything behind it can be optional, and reading all of it forfeits the entire benefit.

`.devlog/archive/` holds closed and superseded material in either shape. Grep it when you need the history behind a resolved thread; never load it wholesale.

When durable project knowledge emerges during the session \u2014 a new domain term worth naming, a pattern seen across multiple sessions, a tension or decision worth remembering \u2014 write it where a later session will find it. In the flat shape that is the matching section of `.devlog/learned.md`. In the indexed shape it is the topic file it belongs to under `.devlog/knowledge/` \u2014 create one if no existing topic fits \u2014 and then add or refresh that file's one-line hook in the index. Keep additions terse; this is a shared notebook, not a changelog.

**Remove as deliberately as you add.** Durable knowledge is atemporal \u2014 a term stays a term, a hard-won gotcha stays true \u2014 so glossary, entity and recurring-theme material only ever grows, wherever it lives. **Open threads is the exception: it holds only what is still unresolved,** and it stays written out in `learned.md` itself in both shapes, because it is a live list rather than reference material and it is what a session needs first. When a thread closes, delete its line in the same turn; `{blog_dir}/` already narrates the resolution at better quality and git keeps every byte. Never let a bullet accumulate its own status history (`PROPOSED \u2192 IMPLEMENTED \u2192 CLOSED`) \u2014 a bullet doing that is telling you to remove it, not extend it. If a thread has a live remnant, cut it down to the one line that is still open. Resolved material worth keeping outside git history goes to `.devlog/archive/`, which is greppable but never auto-loaded.

**Keep what gets loaded small.** `learned.md` is meant to be read in full at the start of a session, and it stops being read in full long before it looks large. A read returns at most ~25,000 tokens; past that you silently get a **truncated page** instead of the file, which looks exactly like success. Bytes are a poor proxy for that limit and they mislead in the dangerous direction \u2014 ordinary prose runs about 4 bytes per token, but a notebook thick with identifiers, paths and code fragments runs nearer 2.5, so it can blow the limit at **~60KB** where a byte estimate would promise 100KB. Past roughly 250KB the read fails outright. Nothing reports either failure, so this budget is the only warning you get.

**At ~60KB, stop trimming and split.** Below that, subtraction is enough \u2014 archive what has closed and the file stays healthy. Above it, a flat file has a structural problem that trimming cannot fix: it must load all of its knowledge or none, and the durable reference material is exactly the part you are not allowed to delete. Splitting costs a few hundred tokens for the index and makes everything behind it load on demand. To split:

1. Create `.devlog/knowledge/` and move the durable material into topic files (`<topic>.md`). **Group by topic, not one file per fact** \u2014 related gotchas are worth reading together, and a few dozen files stay manageable in git and for a human where two hundred do not.
2. Replace that material in `learned.md` with one line per file: `- [Title](knowledge/slug.md) \u2014 what's inside, in one clause`. **The clause after the dash is the load-bearing part** \u2014 it is all a future session has to judge whether the file is worth opening. A bare title is worse than not splitting at all: with nothing to triage on, the reader either opens everything (no gain) or opens nothing (the knowledge is now invisible, where an oversized flat file at least still greps).
3. Leave **Open threads** written out in the index, and move anything already resolved to `.devlog/archive/` on the way past.

`learned.md` keeps its name through all of this \u2014 this convention, the devlog slash commands, and any project docs all cite that path.

### How to write an entry

1. Create a file: `{blog_dir}/YYYY-MM-DD-NN-slug.md` — `NN` is a zero-padded per-day index (`01`, `02`, ...). Scan `{blog_dir}/` for existing files matching the date and pick the next available number; start at `01` if none exist. The index keeps entries in deterministic chronological order under lexical sort.
2. Set `date` to today and `timestamp` to the current local time in ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) at the moment you write the entry. The timestamp captures when within the day the work happened — precise ordering for entries that share a date.
3. Use this frontmatter template. Entries are [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) concept documents, so `type` is required (keep it as `"Devlog Entry"` unless the project says otherwise); the other fields are recommended:

{fm_block}

4. Structure the body with these sections (skip any that don't apply):
{sections_block}

5. **Capture supporting artifacts** \u2014 concrete evidence makes entries credible and portfolio-ready:
{media_block}

6. Regenerate the index: run `devlog index` if the CLI is available; otherwise add the new entry to the top of the list in `{blog_dir}/{config.get("index_file", OKF_INDEX_FILE)}`.

7. If the entry corrects or supersedes a claim made in an earlier entry, annotate the superseded entry **in the same turn**: add a dated blockquote (`> **Update YYYY-MM-DD**: \u2026`) under the affected claim, linking to the new entry. Unmarked stale claims compound \u2014 future sessions act on them at face value.

8. Commit the entry (plus any `learned.md`, `.devlog/knowledge/`, `.devlog/archive/`, and index updates) together with the session's work. An uncommitted entry is invisible to other sessions, worktrees, and collaborators.

### Voice and audience

{voice_block}

### Available tags

{tags_block}

Prefer tags from this list. If a new tag genuinely fits and recurs, use it in the entry's frontmatter \u2014 it will be folded into this list automatically on the next `devlog install`."""

    return text


def generate_thin_convention(
    config: dict[str, Any],
    *,
    agent_key: str = "claude",
    global_context_path: str = "~/.claude/CLAUDE.md",
) -> str:
    """Generate the abbreviated project block used when the full convention is
    already injected globally (e.g. ~/.claude/CLAUDE.md).

    Injecting the full text in both places duplicates ~1.5k tokens in every
    session and lets the two copies drift; the thin block points at the global
    copy and carries only the project-specific pointers."""
    blog_dir = config["blog_dir"]
    context_name = global_context_path.rsplit("/", 1)[-1]
    return f"""\
## Development Blog (Automatic)

This project keeps a development blog in `{blog_dir}/`. The full convention — triggers, entry format, voice, tags — is in your global {context_name} (`{global_context_path}`, installed by devlog); follow it here. Project-specific settings live in `.devlog/config.yaml` and take precedence over the global defaults.

Before writing an entry, read `.devlog/learned.md` for accumulated project vocabulary, themes, and open threads — and extend it when durable knowledge emerges. If it is an index of pointers into `.devlog/knowledge/` rather than a flat file, load only the topic files whose hooks look relevant, and file new durable facts in the matching topic file.

Collaborators without the global devlog install: run `devlog install --ai {agent_key} --full` in this project to inject the standalone convention here instead."""


def wrap_with_sentinels(content: str) -> str:
    """Wrap convention text with sentinel markers for safe injection/removal."""
    return f"{SENTINEL_START}\n{content}\n{SENTINEL_END}\n"


def inject_convention(existing_content: str, convention: str) -> str:
    """Inject or replace convention text in an existing context file."""
    wrapped = wrap_with_sentinels(convention)

    # Strip ALL existing devlog blocks (handles old sentinel formats and duplicates).
    cleaned = remove_convention(existing_content) if _SENTINEL_START_MARKER in existing_content else existing_content

    # Append with a blank line separator.
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    if cleaned and not cleaned.endswith("\n\n"):
        cleaned += "\n"
    return cleaned + wrapped


def remove_convention(content: str) -> str:
    """Remove the convention section from a context file."""
    pattern = r"\n?" + re.escape(_SENTINEL_START_MARKER) + r"[^\n]*-->" + r".*?" + re.escape(SENTINEL_END) + r"\n?"
    result = re.sub(pattern, "", content, flags=re.DOTALL)
    # Clean up trailing whitespace
    return result.rstrip("\n") + "\n" if result.strip() else ""
