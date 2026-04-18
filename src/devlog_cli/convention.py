"""
Convention text generator for devlog.

Reads .devlog/config.yaml and produces the blog convention markdown
that gets injected into agent context files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

SENTINEL_START = "<!-- DEVLOG:START - Do not edit manually. Remove with: devlog uninstall --ai <key> -->"
SENTINEL_END = "<!-- DEVLOG:END -->"

# Stable substrings for matching — immune to sentinel wording changes.
_SENTINEL_START_MARKER = "<!-- DEVLOG:START"
_SENTINEL_END_MARKER = "<!-- DEVLOG:END"

DEFAULT_CONFIG: dict[str, Any] = {
    "blog_dir": "blog",
    "media_dir": "blog/media",
    "file_pattern": "YYYY-MM-DD-slug.md",
    "index_file": "_index.md",
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
        {"field": "title", "example": '"Short descriptive title"'},
        {"field": "date", "example": "YYYY-MM-DD"},
        {"field": "tags", "example": "[relevant, tags, from-list-below]"},
        {"field": "summary", "example": '"One-sentence summary of what was accomplished and why it matters."'},
    ],
    "media": {
        "enabled": True,
        "instructions": [
            "Take screenshots of CLI output, generated files, or workflow artifacts",
            "Save media to `{media_dir}/YYYY-MM-DD-slug/` (matching the entry filename)",
            "Reference in markdown as `![Alt text](media/YYYY-MM-DD-slug/filename.png)`",
            "If screenshots aren't feasible, add a `<!-- TODO: screenshot -->` placeholder",
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
    index_file = config.get("index_file", "_index.md")
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
    index_file = config.get("index_file", "_index.md")
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

### First-time setup (per project)

If the current project does not yet have a `{blog_dir}/` directory, scaffold it before writing the first entry:
1. Create `{blog_dir}/`, `{blog_dir}/media/`, and `.devlog/`.
2. Create `{blog_dir}/{config.get("index_file", "_index.md")}` with a heading using the project\u2019s directory name.
3. Copy `.devlog/learned.md` from the template below or create an empty one with section headings: Glossary, Entities, Recurring themes, Open threads.

If the project has a `.devlog/config.yaml`, use its settings for triggers, voice, and tags **instead of** the defaults below. If it doesn\u2019t, use the defaults."""
    else:
        opener = f"""\
## Development Blog (Automatic)

This project keeps a development blog in `{blog_dir}/`. **Before ending any response in which non-trivial progress was made**, check whether the session hit one of the triggers below. Progress includes decisions reached in discussion \u2014 not only code or files produced. If it did, write or update the blog entry as part of the same turn \u2014 don't defer it to a future session and don't wait to be asked."""

    text = f"""\
{opener}

### When to write an entry

{triggers_block}

A turn that ends on a decision \u2014 e.g., choosing one design over another, agreeing on a scope cut, naming a constraint \u2014 counts even if no code or files were touched. Write the decision now; the implementation can be a separate entry later.

If none of these triggers match the kind of work happening in this project, the defaults are wrong for this domain. Propose edits to `.devlog/config.yaml` that fit this project \u2014 at minimum the `triggers` list, and likely `voice` and `tags` too \u2014 apply them once the user approves, and ask the user to re-run `devlog install` so this convention block regenerates.

### Project context (read first, extend over time)

Before writing an entry, read `.devlog/learned.md`. It holds project-specific vocabulary, entity names, recurring themes, and open threads that previous sessions have accumulated. Use what's there to stay consistent with prior entries.

When durable project knowledge emerges during the session \u2014 a new domain term worth naming, a pattern seen across multiple sessions, a tension or decision worth remembering \u2014 append it to the appropriate section of `.devlog/learned.md`. Keep additions terse; this file is a shared notebook, not a changelog.

### How to write an entry

1. Create a file: `{blog_dir}/YYYY-MM-DD-slug.md`
2. If multiple entries share a date, append a number: `YYYY-MM-DD-slug-2.md`
3. Use this frontmatter template:

{fm_block}

4. Structure the body with these sections (skip any that don't apply):
{sections_block}

5. **Capture rich media** \u2014 screenshots and visuals are critical for portfolio impact:
{media_block}

6. Update `{blog_dir}/{config.get("index_file", "_index.md")}` \u2014 add the new entry to the list at the top.

### Voice and audience

{voice_block}

### Available tags

{tags_block}

Prefer tags from this list. If a new tag genuinely fits and recurs, use it in the entry's frontmatter \u2014 it will be folded into this list automatically on the next `devlog install`."""

    return text


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
