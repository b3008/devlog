"""Tests for OKF migration: the migrate_entry_text helper and `devlog migrate`."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from devlog_cli import app
from devlog_cli.convention import load_config, migrate_entry_text, plan_migration

runner = CliRunner()


class TestMigrateEntryText:
    def test_adds_type_when_missing(self):
        text = '---\ntitle: "X"\ndate: 2026-01-01\ndescription: "s"\n---\nBody\n'
        out, changes = migrate_entry_text(text)
        assert "added type" in changes
        assert out.startswith('---\ntype: "Devlog Entry"\n')
        assert out.endswith("Body\n")

    def test_renames_summary_to_description(self):
        text = '---\ntitle: "X"\nsummary: "the summary"\n---\nBody\n'
        out, changes = migrate_entry_text(text)
        assert "summary→description" in changes
        assert 'description: "the summary"' in out
        assert "summary:" not in out

    def test_adds_type_and_renames_in_one_pass(self):
        text = '---\ntitle: "X"\nsummary: "s"\n---\nBody\n'
        out, changes = migrate_entry_text(text)
        assert set(changes) == {"added type", "summary→description"}

    def test_idempotent_on_conformant_entry(self):
        text = '---\ntype: "Devlog Entry"\ntitle: "X"\ndescription: "s"\n---\nBody\n'
        out, changes = migrate_entry_text(text)
        assert changes == []
        assert out == text

    def test_no_frontmatter_is_skipped(self):
        text = "Just prose, no frontmatter.\n"
        out, changes = migrate_entry_text(text)
        assert changes == []
        assert out == text

    def test_keeps_summary_when_description_already_present(self):
        text = '---\ntitle: "X"\nsummary: "s"\ndescription: "d"\n---\nBody\n'
        out, changes = migrate_entry_text(text)
        assert "summary→description" not in changes
        assert "added type" in changes
        assert "summary:" in out  # left untouched to avoid a collision

    def test_preserves_other_fields_and_body(self):
        text = '---\ntitle: "X"\ntags: [a, b]\nsummary: "s"\n---\n\n## Heading\nbody\n'
        out, _ = migrate_entry_text(text)
        assert "tags: [a, b]" in out
        assert "## Heading" in out


def _legacy_project(root: Path) -> Path:
    """Build a pre-OKF project: `_index.md` index, an entry with `summary` and
    no `type`, and a config pointing at the old index name."""
    (root / ".devlog").mkdir()
    (root / ".devlog" / "config.yaml").write_text(
        'blog_dir: blog\nmedia_dir: blog/media\nindex_file: "_index.md"\n'
        "frontmatter:\n"
        "  - field: title\n"
        "    example: '\"t\"'\n"
        "  - field: summary\n"
        "    example: '\"s\"'\n",
        encoding="utf-8",
    )
    blog = root / "blog"
    blog.mkdir()
    (blog / "_index.md").write_text(
        "# Legacy — Development Blog\n\n- old list\n", encoding="utf-8"
    )
    (blog / "2026-01-01-01-first.md").write_text(
        '---\ntitle: "First"\ndate: 2026-01-01\ntimestamp: 2026-01-01T10:00:00\n'
        'tags: [feature]\nsummary: "the first entry"\n---\nBody\n',
        encoding="utf-8",
    )
    return blog


def _legacy_project_without_config(root: Path) -> Path:
    """A pre-OKF project scaffolded by the *global* convention: `_index.md` on
    disk, a legacy entry — and no `.devlog/config.yaml` to name the index."""
    (root / ".devlog").mkdir()
    (root / ".devlog" / "learned.md").write_text("# Project knowledge\n", encoding="utf-8")
    blog = root / "blog"
    blog.mkdir()
    (blog / "_index.md").write_text(
        "# Cold — Development Blog\n\n- old list\n", encoding="utf-8"
    )
    (blog / "2026-01-01-01-first.md").write_text(
        '---\ntitle: "First"\ndate: 2026-01-01\ntimestamp: 2026-01-01T10:00:00\n'
        'tags: [feature]\nsummary: "the first entry"\n---\nBody\n',
        encoding="utf-8",
    )
    return blog


class TestMigrateCommand:
    def test_migrates_legacy_project(self, project_dir: Path):
        blog = _legacy_project(project_dir)
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0

        # Index renamed to the OKF reserved name and stamped.
        assert not (blog / "_index.md").exists()
        idx = (blog / "index.md").read_text(encoding="utf-8")
        assert 'okf_version: "0.1"' in idx
        assert "# Legacy — Development Blog" in idx  # heading preserved
        assert "[First](2026-01-01-01-first.md)" in idx  # entry indexed

        # Entry made conformant.
        entry = (blog / "2026-01-01-01-first.md").read_text(encoding="utf-8")
        assert 'type: "Devlog Entry"' in entry
        assert 'description: "the first entry"' in entry
        assert "summary:" not in entry

        # Config updated: new index name + OKF-shaped frontmatter list, so
        # future entries are born conformant too.
        cfg = (project_dir / ".devlog" / "config.yaml").read_text(encoding="utf-8")
        assert 'index_file: "index.md"' in cfg
        assert "- field: type" in cfg
        assert "- field: description" in cfg
        assert "- field: summary" not in cfg

    def test_check_is_a_dry_run(self, project_dir: Path):
        blog = _legacy_project(project_dir)
        result = runner.invoke(app, ["migrate", "--check"])
        assert result.exit_code == 0
        assert "Would migrate" in result.output
        # Nothing written.
        assert (blog / "_index.md").exists()
        assert not (blog / "index.md").exists()
        entry = (blog / "2026-01-01-01-first.md").read_text(encoding="utf-8")
        assert "type:" not in entry
        assert "summary:" in entry

    def test_idempotent_second_run(self, project_dir: Path):
        _legacy_project(project_dir)
        runner.invoke(app, ["migrate"])
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0
        assert "Nothing to migrate" in result.output

    def test_errors_without_blog_dir(self, project_dir: Path):
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 1

    def test_finds_legacy_index_without_a_config(self, project_dir: Path):
        """The config-less project is the common case in the wild: `.devlog/`
        scaffolded by the global convention, which never writes a config.yaml.
        The legacy index has to be found on disk or it gets orphaned."""
        blog = _legacy_project_without_config(project_dir)
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0

        # Renamed, not duplicated — the orphan is the whole bug.
        assert not (blog / "_index.md").exists()
        idx = (blog / "index.md").read_text(encoding="utf-8")
        assert 'okf_version: "0.1"' in idx
        assert "# Cold — Development Blog" in idx  # heading carried across
        assert "[First](2026-01-01-01-first.md)" in idx

        entry = (blog / "2026-01-01-01-first.md").read_text(encoding="utf-8")
        assert 'type: "Devlog Entry"' in entry
        assert 'description: "the first entry"' in entry

        # No config.yaml exists, so the run must not claim it rewrote one.
        assert "index_file" not in result.output
        assert not (project_dir / ".devlog" / "config.yaml").exists()

    def test_config_less_migration_is_idempotent(self, project_dir: Path):
        """The disk probe must not re-fire once `index.md` is the real index,
        or `status` would report non-conformance forever."""
        _legacy_project_without_config(project_dir)
        runner.invoke(app, ["migrate"])
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0
        assert "Nothing to migrate" in result.output

    def test_plan_sees_the_legacy_index_without_a_config(self, project_dir: Path):
        """The plan is the shared source of truth for migrate/status/install, so
        assert on it directly rather than on rendered output. Before the fix
        `current_index` stayed `index.md`, `index_rename` was False, and
        `_index.md` fell outside the skip set to be tallied as an entry."""
        _legacy_project_without_config(project_dir)
        plan = plan_migration(project_dir, load_config(project_dir))

        assert plan.current_index == "_index.md"
        assert plan.index_rename is True
        assert plan.unchanged == 0  # the index is not an entry
        assert [name for name, _ in plan.entry_changes] == ["2026-01-01-01-first.md"]
        assert plan.config_update is False  # nothing to rewrite


class TestInstallAutoMigrate:
    def test_install_heals_legacy_blog(self, project_dir: Path):
        blog = _legacy_project(project_dir)
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert "Migrated blog to OKF" in result.output
        # Index renamed and entry made conformant without a separate command.
        assert not (blog / "_index.md").exists()
        assert (blog / "index.md").exists()
        entry = (blog / "2026-01-01-01-first.md").read_text(encoding="utf-8")
        assert 'type: "Devlog Entry"' in entry
        # The injected convention reflects the new index name.
        claude_md = (project_dir / "CLAUDE.md").read_text(encoding="utf-8")
        assert "blog/index.md" in claude_md
