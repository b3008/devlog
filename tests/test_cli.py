"""Tests for CLI commands via typer's CliRunner."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devlog_cli import app
from devlog_cli.convention import _SENTINEL_START_MARKER, SENTINEL_END

runner = CliRunner()


class TestInit:
    def test_creates_scaffold(self, project_dir: Path):
        result = runner.invoke(app, ["init", "--name", "My Project"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "config.yaml").exists()
        assert (project_dir / ".devlog" / "learned.md").exists()
        assert (project_dir / "blog" / "_index.md").exists()
        assert (project_dir / "blog" / "media").is_dir()

    def test_index_has_project_name(self, project_dir: Path):
        runner.invoke(app, ["init", "--name", "My Project"])
        content = (project_dir / "blog" / "_index.md").read_text()
        assert "My Project" in content

    def test_idempotent(self, project_dir: Path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["init"])
        assert (project_dir / ".devlog" / "config.yaml").exists()

    def test_defaults_name_to_dirname(self, project_dir: Path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0


class TestInstall:
    def test_creates_claude_md(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        claude_md = (initialized_project / "CLAUDE.md").read_text()
        assert _SENTINEL_START_MARKER in claude_md
        assert SENTINEL_END in claude_md

    def test_preserves_existing_content(self, initialized_project: Path):
        claude_md = initialized_project / "CLAUDE.md"
        claude_md.write_text("# My Rules\n\nDon't touch this.\n")
        runner.invoke(app, ["install", "--ai", "claude"])
        content = claude_md.read_text()
        assert "# My Rules" in content
        assert _SENTINEL_START_MARKER in content

    def test_reinstall_replaces(self, installed_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        content = (installed_project / "CLAUDE.md").read_text()
        assert content.count(_SENTINEL_START_MARKER) == 1

    def test_auto_init(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "config.yaml").exists()

    def test_unknown_agent(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "nonexistent"])
        assert result.exit_code == 1

    def test_tag_discovery(self, installed_project: Path, sample_entry: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert "custom-tag" in result.output

    def test_manifest_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["agent"] == "claude"
        assert "CLAUDE.md" in data["files"]


class TestInstallWithHook:
    def test_creates_hook_files(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert result.exit_code == 0
        assert (initialized_project / ".devlog" / "hooks" / "stop.py").exists()
        assert (initialized_project / ".devlog" / "hooks" / "session_end.py").exists()
        assert (initialized_project / ".claude" / "settings.json").exists()

    def test_settings_json_structure(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text()
        )
        stop_entries = settings["hooks"]["Stop"]
        assert len(stop_entries) == 1
        commands = [h["command"] for h in stop_entries[0]["hooks"]]
        assert any(".devlog/hooks/stop.py" in c for c in commands)

    def test_preserves_existing_settings(self, initialized_project: Path):
        settings_dir = initialized_project / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps({"theme": "dark", "permissions": {"allow": ["Bash"]}})
        )
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads((settings_dir / "settings.json").read_text())
        assert settings["theme"] == "dark"
        assert settings["permissions"] == {"allow": ["Bash"]}
        assert "hooks" in settings

    def test_idempotent(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text()
        )
        assert len(settings["hooks"]["Stop"]) == 1

    def test_manifest_records_hook_bundle(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text()
        )
        assert {h["event"] for h in data["hooks"]} == {"Stop", "SessionEnd"}

    def test_settings_records_session_end(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text()
        )
        commands = [h["command"] for h in settings["hooks"]["SessionEnd"][0]["hooks"]]
        assert any("session_end.py" in c for c in commands)

    def test_manifest_records_hook_sha256(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text(encoding="utf-8")
        )
        assert len(data["hooks"][0]["sha256"]) == 64

    def test_reinstall_without_flag_carries_hook_forward(self, initialized_project: Path):
        """A reinstall without --with-hook must not orphan an installed hook:
        settings.json keeps firing it, so the manifest must keep tracking it."""
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text(encoding="utf-8")
        )
        assert {h["event"] for h in data["hooks"]} == {"Stop", "SessionEnd"}
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        assert len(settings["hooks"]["Stop"]) == 1
        assert "Refreshed existing Stop hook" in result.output

    def test_reinstall_refreshes_stale_hook_script(self, initialized_project: Path):
        """An unmodified script from an older version (disk hash == recorded
        hash != new template hash) gets resynced from the template."""
        import hashlib

        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        script = initialized_project / ".devlog" / "hooks" / "stop.py"
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        old = "# old template version\n"
        script.write_text(old, encoding="utf-8")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["hooks"][0]["sha256"] = hashlib.sha256(old.encode("utf-8")).hexdigest()
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert script.read_text(encoding="utf-8") != old

    def test_reinstall_preserves_customized_hook_script(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        script = initialized_project / ".devlog" / "hooks" / "stop.py"
        script.write_text("# my custom hook\n", encoding="utf-8")
        result = runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert result.exit_code == 0
        assert script.read_text(encoding="utf-8") == "# my custom hook\n"
        assert "Preserved" in result.output

    def test_rejected_for_non_claude(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "copilot", "--with-hook"])
        assert result.exit_code == 1
        assert "only supported for" in result.output

    def test_hook_tip_shown_without_flag(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert "--with-hook" in result.output


class TestSlashCommands:
    def test_command_file_created(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        assert "blog/_index.md" in body
        assert "learned.md" in body

    def test_write_command_file_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-write.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        assert "$ARGUMENTS" in body

    def test_manicure_command_file_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-manicure.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        # Phase markers and key concepts present.
        assert "Phase 1" in body
        assert "Phase 4" in body
        assert "annotate" in body
        assert "wipe" in body
        # Optional topic argument is wired in.
        assert "$ARGUMENTS" in body

    def test_manifest_records_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text()
        )
        names = {c["name"] for c in data["commands"]}
        assert "devlog-catchup" in names
        assert "devlog-write" in names
        assert "devlog-manicure" in names

    def test_install_message_lists_command(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert "/devlog-catchup" in result.output
        assert "/devlog-write" in result.output
        assert "/devlog-manicure" in result.output

    def test_idempotent_on_reinstall(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_files = list((initialized_project / ".claude" / "commands").glob("*.md"))
        assert len(cmd_files) == 3  # catchup + write + manicure

    def test_not_installed_for_non_claude(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "copilot"])
        assert not (initialized_project / ".claude" / "commands").exists()

    def test_uninstall_removes_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not cmd_file.exists()
        # Empty .claude/commands and .claude get cleaned up.
        assert not (initialized_project / ".claude" / "commands").exists()

    def test_global_install_creates_command(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        cmd_file = project_dir / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()

    def test_global_uninstall_removes_command(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert not (project_dir / ".claude" / "commands" / "devlog-catchup.md").exists()

    def test_manifest_records_command_hashes(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text(encoding="utf-8")
        )
        for cmd in data["commands"]:
            assert "sha256" in cmd
            assert len(cmd["sha256"]) == 64

    def test_reinstall_preserves_user_customization(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        cmd_file.write_text("# my custom version\n", encoding="utf-8")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert cmd_file.read_text(encoding="utf-8") == "# my custom version\n"
        assert "Preserved" in result.output

    def test_uninstall_preserves_user_customization(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        cmd_file.write_text("# my custom version\n", encoding="utf-8")
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert cmd_file.exists()
        assert cmd_file.read_text(encoding="utf-8") == "# my custom version\n"

    def test_reinstall_removes_orphaned_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        # Simulate a previous version that shipped an extra slash command:
        # add an orphan file plus a manifest entry pointing at it.
        orphan = initialized_project / ".claude" / "commands" / "devlog-zombie.md"
        orphan.write_text("ghost from a prior release\n", encoding="utf-8")
        import hashlib

        orphan_hash = hashlib.sha256(
            orphan.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["commands"].append({
            "name": "devlog-zombie",
            "path": ".claude/commands/devlog-zombie.md",
            "sha256": orphan_hash,
        })
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert not orphan.exists()
        # And the manifest stops tracking it.
        new_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "devlog-zombie" not in {c["name"] for c in new_data["commands"]}

    def test_install_passthrough_when_templates_missing(self, initialized_project: Path, monkeypatch):
        """If templates/commands/ is missing (packaging error / incomplete checkout),
        reinstall must NOT delete previously-tracked commands as orphans."""
        from devlog_cli import _install_claude_commands

        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))["commands"]

        # Point _templates_dir() at a directory without commands/ to simulate the failure.
        broken_root = initialized_project / "broken_templates"
        broken_root.mkdir()
        monkeypatch.setattr("devlog_cli._templates_dir", lambda: broken_root)

        records, preserved, orphans = _install_claude_commands(initialized_project, previous)
        assert records == previous  # passthrough preserves the prior manifest exactly
        assert preserved == []
        assert orphans == []
        assert cmd_file.exists()  # critically, no files deleted

    def test_reinstall_overwrites_unreadable_file(self, initialized_project: Path):
        """If dst exists but is unreadable, install must not abort — it should
        fall back to overwriting from the template."""
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        # Write invalid UTF-8 to trigger UnicodeDecodeError on read.
        cmd_file.write_bytes(b"\xff\xfe not valid utf-8 \x80")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        # File got overwritten from the template — content should now be valid UTF-8
        # matching the bundled template (starts with frontmatter).
        body = cmd_file.read_text(encoding="utf-8")
        assert body.startswith("---")

    def test_reinstall_preserves_modified_orphan(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        orphan = initialized_project / ".claude" / "commands" / "devlog-zombie.md"
        orphan.write_text("original ghost\n", encoding="utf-8")
        import hashlib

        original_hash = hashlib.sha256("original ghost\n".encode("utf-8")).hexdigest()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["commands"].append({
            "name": "devlog-zombie",
            "path": ".claude/commands/devlog-zombie.md",
            "sha256": original_hash,
        })
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # User customized it after install; reinstall must not delete their edits.
        orphan.write_text("user-edited ghost\n", encoding="utf-8")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert orphan.exists()
        assert orphan.read_text(encoding="utf-8") == "user-edited ghost\n"


class TestThinLocalBlock:
    """With a global install present, local installs drop a thin pointer
    block instead of duplicating the full convention in every session."""

    def test_thin_block_when_global_installed(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        content = (initialized_project / "CLAUDE.md").read_text(encoding="utf-8")
        assert _SENTINEL_START_MARKER in content
        assert "full convention" in content
        assert "### How to write an entry" not in content
        assert "thin project block" in result.output

    def test_full_flag_overrides_detection(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        result = runner.invoke(app, ["install", "--ai", "claude", "--full"])
        assert result.exit_code == 0
        content = (initialized_project / "CLAUDE.md").read_text(encoding="utf-8")
        assert "### How to write an entry" in content

    def test_full_block_without_global_install(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        content = (initialized_project / "CLAUDE.md").read_text(encoding="utf-8")
        assert "### How to write an entry" in content

    def test_manifest_without_convention_not_enough(
        self, initialized_project: Path, isolated_home: Path
    ):
        # A stale global manifest with no actual convention block must not
        # trigger the thin path — the agent would be left with no rules at all.
        manifests = isolated_home / ".devlog" / "manifests"
        manifests.mkdir(parents=True)
        (manifests / "claude.manifest.json").write_text("{}", encoding="utf-8")
        runner.invoke(app, ["install", "--ai", "claude"])
        content = (initialized_project / "CLAUDE.md").read_text(encoding="utf-8")
        assert "### How to write an entry" in content


class TestUninstall:
    def test_removes_convention(self, installed_project: Path):
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert not (installed_project / "CLAUDE.md").exists()  # was empty besides convention

    def test_preserves_non_devlog_content(self, initialized_project: Path):
        claude_md = initialized_project / "CLAUDE.md"
        claude_md.write_text("# My Rules\n")
        runner.invoke(app, ["install", "--ai", "claude"])
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        content = claude_md.read_text()
        assert "# My Rules" in content
        assert _SENTINEL_START_MARKER not in content

    def test_removes_hook(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert (initialized_project / ".devlog" / "hooks" / "stop.py").exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not (initialized_project / ".devlog" / "hooks" / "stop.py").exists()

    def test_uninstall_preserves_customized_hook_script(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        script = initialized_project / ".devlog" / "hooks" / "stop.py"
        script.write_text("# my custom hook\n", encoding="utf-8")
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert script.exists()
        assert script.read_text(encoding="utf-8") == "# my custom hook\n"

    def test_uninstall_preserves_unverifiable_script_from_old_manifest(
        self, initialized_project: Path
    ):
        """Pre-sha256 manifests can't prove a modified script is devlog's;
        uninstall must keep it rather than risk deleting user edits."""
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for h in data["hooks"]:
            h.pop("sha256", None)
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        script = initialized_project / ".devlog" / "hooks" / "stop.py"
        script.write_text("# customized before hashes existed\n", encoding="utf-8")

        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert script.exists()
        assert script.read_text(encoding="utf-8") == "# customized before hashes existed\n"

    def test_uninstall_removes_pristine_script_from_old_manifest(
        self, initialized_project: Path
    ):
        """A hash-less record whose script still matches the shipped template
        is positively devlog's — uninstall removes it."""
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for h in data["hooks"]:
            h.pop("sha256", None)
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert not (initialized_project / ".devlog" / "hooks" / "stop.py").exists()

    def test_hook_removal_preserves_settings(self, initialized_project: Path):
        settings_dir = initialized_project / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(json.dumps({"theme": "dark"}))
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        settings = json.loads((settings_dir / "settings.json").read_text())
        assert settings == {"theme": "dark"}

    def test_not_installed(self, project_dir: Path):
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 1

    def test_removes_manifest(self, installed_project: Path):
        manifest = installed_project / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not manifest.exists()


class TestStatus:
    def test_no_agents(self, project_dir: Path):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "No agents installed" in result.output

    def test_shows_active(self, installed_project: Path):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "active" in result.output
        assert "Claude Code" in result.output

    def test_shows_entry_count(self, installed_project: Path, sample_entry: Path):
        result = runner.invoke(app, ["status"])
        assert "1 entry" in result.output
        assert "2026-04-16" in result.output

    def test_no_entries_shown(self, installed_project: Path):
        result = runner.invoke(app, ["status"])
        assert "no entries yet" in result.output

    def test_session_coverage_line(self, installed_project: Path, sample_entry: Path):
        (installed_project / ".devlog" / "sessions.jsonl").write_text(
            '{"ts": "2026-04-17T10:00:00+00:00", "session_id": "a", "reason": "exit"}\n'
            '{"ts": "2026-04-18T10:00:00+00:00", "session_id": "b", "reason": "exit"}\n',
            encoding="utf-8",
        )
        result = runner.invoke(app, ["status"])
        assert "2 recorded" in result.output
        assert "2 since the last entry" in result.output

    def test_no_session_line_without_log(self, installed_project: Path):
        result = runner.invoke(app, ["status"])
        assert "recorded" not in result.output


class TestGlobalInstall:
    def test_creates_global_claude_md(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["install", "--ai", "claude", "--global"])
        assert result.exit_code == 0
        claude_md = project_dir / ".claude" / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert _SENTINEL_START_MARKER in content
        assert "Every project" in content  # global opener wording

    def test_includes_bootstrap_section(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        content = (project_dir / ".claude" / "CLAUDE.md").read_text()
        assert "First-time setup" in content
        assert ".devlog/config.yaml" in content

    def test_migrates_legacy_home_root_location(self, project_dir: Path, monkeypatch):
        """Old versions injected into ~/CLAUDE.md; reinstall must move the
        convention to ~/.claude/CLAUDE.md and clean the legacy copy."""
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        legacy = project_dir / "CLAUDE.md"
        legacy.write_text(
            "<!-- DEVLOG:START - old install -->\nold convention\n<!-- DEVLOG:END -->\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["install", "--ai", "claude", "--global"])
        assert result.exit_code == 0
        assert (project_dir / ".claude" / "CLAUDE.md").exists()
        # Legacy file was devlog-only, so it should be gone entirely.
        assert not legacy.exists()

    def test_migration_preserves_legacy_non_devlog_content(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        legacy = project_dir / "CLAUDE.md"
        legacy.write_text(
            "# My global rules\n\n<!-- DEVLOG:START - old -->\nold\n<!-- DEVLOG:END -->\n",
            encoding="utf-8",
        )
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        content = legacy.read_text(encoding="utf-8")
        assert "# My global rules" in content
        assert _SENTINEL_START_MARKER not in content

    def test_with_hook_global(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["install", "--ai", "claude", "--global", "--with-hook"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "hooks" / "stop.py").exists()
        settings = json.loads((project_dir / ".claude" / "settings.json").read_text())
        command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert "$HOME/" in command  # global hook uses $HOME, not $CLAUDE_PROJECT_DIR

    def test_manifest_in_home(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        manifest = project_dir / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()

    def test_rejected_for_non_claude(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "copilot", "--global"])
        assert result.exit_code == 1

    def test_preserves_existing_global_content(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        claude_md = project_dir / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True)
        claude_md.write_text("# My global rules\n")
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        content = claude_md.read_text()
        assert "# My global rules" in content
        assert _SENTINEL_START_MARKER in content


class TestGlobalUninstall:
    def test_removes_global_convention(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        result = runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert result.exit_code == 0
        # ~/.claude/CLAUDE.md was devlog-only, so file should be removed
        assert not (project_dir / ".claude" / "CLAUDE.md").exists()

    def test_uninstall_sweeps_legacy_location(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        # Simulate a stale legacy copy left behind by an old version.
        legacy = project_dir / "CLAUDE.md"
        legacy.write_text(
            "<!-- DEVLOG:START - old -->\nold\n<!-- DEVLOG:END -->\n", encoding="utf-8"
        )
        runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert not legacy.exists()

    def test_removes_global_hook(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global", "--with-hook"])
        runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert not (project_dir / ".devlog" / "hooks" / "stop.py").exists()

    def test_global_uninstall_not_installed(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert result.exit_code == 1


class TestIndexCommand:
    def test_generates_from_frontmatter_newest_first(
        self, installed_project: Path, sample_entry: Path
    ):
        (installed_project / "blog" / "2026-05-01-01-newer.md").write_text(
            '---\ntitle: "Newer entry"\ndate: 2026-05-01\ntimestamp: 2026-05-01T10:00:00\n---\nBody.\n',
            encoding="utf-8",
        )
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0
        assert "2 entries" in result.output
        content = (installed_project / "blog" / "_index.md").read_text(encoding="utf-8")
        assert "[Newer entry](2026-05-01-01-newer.md)" in content
        assert content.index("2026-05-01-01-newer.md") < content.index("2026-04-16-test-entry.md")
        assert "Generated by `devlog index`" in content

    def test_same_day_entries_ordered_by_timestamp(self, installed_project: Path):
        blog = installed_project / "blog"
        (blog / "2026-05-01-01-morning.md").write_text(
            '---\ntitle: "Morning"\ndate: 2026-05-01\ntimestamp: 2026-05-01T09:00:00\n---\n',
            encoding="utf-8",
        )
        (blog / "2026-05-01-02-evening.md").write_text(
            '---\ntitle: "Evening"\ndate: 2026-05-01\ntimestamp: 2026-05-01T21:00:00\n---\n',
            encoding="utf-8",
        )
        runner.invoke(app, ["index"])
        content = (blog / "_index.md").read_text(encoding="utf-8")
        assert content.index("[Evening]") < content.index("[Morning]")

    def test_preserves_existing_heading(self, installed_project: Path, sample_entry: Path):
        runner.invoke(app, ["index"])
        content = (installed_project / "blog" / "_index.md").read_text(encoding="utf-8")
        # Heading scaffolded by init (project name) survives regeneration.
        assert content.splitlines()[0] == "# Test Project — Development Blog"

    def test_entry_without_frontmatter_falls_back_to_filename(
        self, installed_project: Path
    ):
        (installed_project / "blog" / "2026-03-03-bare.md").write_text(
            "No frontmatter here.\n", encoding="utf-8"
        )
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0
        content = (installed_project / "blog" / "_index.md").read_text(encoding="utf-8")
        assert "[2026-03-03-bare](2026-03-03-bare.md)" in content
        assert "- 2026-03-03 —" in content

    def test_errors_without_blog_dir(self, project_dir: Path):
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 1


class TestListAgents:
    def test_lists_agents(self, project_dir: Path):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "GitHub Copilot" in result.output
        assert "Gemini CLI" in result.output


class TestVersion:
    def test_shows_version(self, project_dir: Path):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
