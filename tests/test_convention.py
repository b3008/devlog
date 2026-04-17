"""Tests for convention.py — rendering, injection, tag discovery, entry scanning."""
from __future__ import annotations

from pathlib import Path

from devlog_cli.convention import (
    _SENTINEL_START_MARKER,
    DEFAULT_CONFIG,
    SENTINEL_END,
    _extract_frontmatter,
    discover_tags,
    generate_convention,
    inject_convention,
    load_config,
    remove_convention,
    scan_entries,
)

# ── Frontmatter extraction ──────────────────────────────────────────────


class TestExtractFrontmatter:
    def test_valid(self):
        text = "---\ntitle: Hello\ntags: [a, b]\n---\nBody."
        fm = _extract_frontmatter(text)
        assert fm == {"title": "Hello", "tags": ["a", "b"]}

    def test_missing_fence(self):
        assert _extract_frontmatter("No frontmatter here.") is None

    def test_unclosed_fence(self):
        assert _extract_frontmatter("---\ntitle: Hello\nNo closing.") is None

    def test_invalid_yaml(self):
        assert _extract_frontmatter("---\n: :\n---\n") is None

    def test_non_dict(self):
        assert _extract_frontmatter("---\n- item\n---\n") is None

    def test_crlf(self):
        text = "---\r\ntitle: Hello\r\n---\r\nBody."
        fm = _extract_frontmatter(text)
        assert fm is not None
        assert fm["title"] == "Hello"


# ── Config loading ───────────────────────────────────────────────────────


class TestLoadConfig:
    def test_defaults_without_file(self, project_dir: Path):
        config = load_config(project_dir)
        assert config["blog_dir"] == "blog"
        assert len(config["tags"]) > 0
        assert len(config["triggers"]) > 0

    def test_user_override(self, project_dir: Path):
        devlog_dir = project_dir / ".devlog"
        devlog_dir.mkdir()
        (devlog_dir / "config.yaml").write_text(
            "blog_dir: docs/blog\ntags:\n  - custom\n"
        )
        config = load_config(project_dir)
        assert config["blog_dir"] == "docs/blog"
        assert config["tags"] == ["custom"]
        # Other defaults still present.
        assert "voice" in config


# ── Convention generation ────────────────────────────────────────────────


class TestGenerateConvention:
    def test_contains_key_sections(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert "## Development Blog (Automatic)" in text
        assert "### When to write an entry" in text
        assert "### How to write an entry" in text
        assert "### Voice and audience" in text
        assert "### Available tags" in text

    def test_progress_wording(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert "non-trivial progress was made" in text

    def test_decision_trigger(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert "even if no code changed yet" in text

    def test_decisions_count_note(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert "A turn that ends on a decision" in text

    def test_self_tailoring_note(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert "defaults are wrong for this domain" in text

    def test_learned_md_reference(self):
        text = generate_convention(DEFAULT_CONFIG)
        assert ".devlog/learned.md" in text

    def test_custom_tags_rendered(self):
        config = dict(DEFAULT_CONFIG)
        config["tags"] = ["alpha", "beta"]
        text = generate_convention(config)
        assert "`alpha`" in text
        assert "`beta`" in text

    def test_global_mode_opener(self):
        text = generate_convention(DEFAULT_CONFIG, global_mode=True)
        assert "Every project" in text
        assert "First-time setup" in text
        assert ".devlog/config.yaml" in text

    def test_global_mode_still_has_triggers(self):
        text = generate_convention(DEFAULT_CONFIG, global_mode=True)
        assert "### When to write an entry" in text
        assert "### Voice and audience" in text

    def test_local_mode_no_bootstrap(self):
        text = generate_convention(DEFAULT_CONFIG, global_mode=False)
        assert "First-time setup" not in text
        assert "This project keeps" in text


# ── Convention injection / removal ───────────────────────────────────────


class TestInjection:
    def test_inject_into_empty(self):
        result = inject_convention("", "convention text")
        assert _SENTINEL_START_MARKER in result
        assert SENTINEL_END in result
        assert "convention text" in result

    def test_inject_preserves_existing(self):
        existing = "# My Project\n\nSome docs.\n"
        result = inject_convention(existing, "convention text")
        assert result.startswith("# My Project\n")
        assert "convention text" in result

    def test_reinject_replaces(self):
        first = inject_convention("", "first")
        second = inject_convention(first, "second")
        assert "second" in second
        assert "first" not in second
        # Only one sentinel pair.
        assert second.count(_SENTINEL_START_MARKER) == 1

    def test_remove(self):
        injected = inject_convention("# Title\n", "convention text")
        removed = remove_convention(injected)
        assert _SENTINEL_START_MARKER not in removed
        assert "convention text" not in removed
        assert "# Title" in removed

    def test_remove_empty_file(self):
        injected = inject_convention("", "convention text")
        removed = remove_convention(injected)
        assert removed == ""


# ── Tag discovery ────────────────────────────────────────────────────────


class TestDiscoverTags:
    def test_discovers_from_entries(self, installed_project: Path, sample_entry: Path):
        config = load_config(installed_project)
        tags = discover_tags(installed_project, config)
        assert "custom-tag" in tags
        assert "feature" in tags
        assert "testing" in tags

    def test_skips_index_file(self, installed_project: Path):
        config = load_config(installed_project)
        tags = discover_tags(installed_project, config)
        # _index.md has no frontmatter; should not crash.
        assert isinstance(tags, list)

    def test_no_blog_dir(self, project_dir: Path):
        config = dict(DEFAULT_CONFIG)
        tags = discover_tags(project_dir, config)
        assert tags == []

    def test_malformed_entry_skipped(self, installed_project: Path):
        (installed_project / "blog" / "2026-01-01-bad.md").write_text("Not YAML at all.")
        config = load_config(installed_project)
        # Should not raise.
        tags = discover_tags(installed_project, config)
        assert isinstance(tags, list)


# ── Entry scanning ───────────────────────────────────────────────────────


class TestScanEntries:
    def test_counts_and_finds_latest(self, installed_project: Path, sample_entry: Path):
        (installed_project / "blog" / "2026-03-01-older.md").write_text(
            "---\ntitle: Older\ndate: 2026-03-01\n---\n"
        )
        config = load_config(installed_project)
        count, latest = scan_entries(installed_project, config)
        assert count == 2
        assert latest == "2026-04-16"

    def test_empty_blog(self, installed_project: Path):
        config = load_config(installed_project)
        count, latest = scan_entries(installed_project, config)
        assert count == 0
        assert latest is None

    def test_ignores_non_dated_files(self, installed_project: Path):
        (installed_project / "blog" / "random-notes.md").write_text("hello")
        config = load_config(installed_project)
        count, _ = scan_entries(installed_project, config)
        assert count == 0
