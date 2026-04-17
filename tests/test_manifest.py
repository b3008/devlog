"""Tests for manifest.py — save/load round-trip, hooks, backward compat."""
from __future__ import annotations

import json
from pathlib import Path

from devlog_cli.manifest import Manifest


class TestManifest:
    def test_round_trip(self, project_dir: Path):
        m = Manifest(agent_key="claude", project_root=project_dir)
        m.files["CLAUDE.md"] = m._sha256("content")
        saved_path = m.save()
        assert saved_path.exists()

        loaded = Manifest.load(saved_path, project_dir)
        assert loaded is not None
        assert loaded.agent_key == "claude"
        assert loaded.files == m.files
        assert loaded.installed_at == m.installed_at

    def test_hooks_persisted(self, project_dir: Path):
        m = Manifest(agent_key="claude", project_root=project_dir)
        m.hooks.append({
            "event": "Stop",
            "script_path": ".devlog/hooks/stop.py",
            "settings_path": ".claude/settings.json",
            "command": "python3 stop.py",
        })
        m.save()

        loaded = Manifest.load(m.manifest_path, project_dir)
        assert loaded is not None
        assert len(loaded.hooks) == 1
        assert loaded.hooks[0]["event"] == "Stop"

    def test_backward_compat_no_hooks(self, project_dir: Path):
        """Old manifests without a 'hooks' key should load with hooks=[]."""
        manifest_dir = project_dir / ".devlog" / "manifests"
        manifest_dir.mkdir(parents=True)
        manifest_path = manifest_dir / "claude.manifest.json"
        manifest_path.write_text(json.dumps({
            "agent": "claude",
            "version": "0.1.0",
            "installed_at": "2026-04-16T00:00:00+00:00",
            "files": {"CLAUDE.md": "abc123"},
        }))

        loaded = Manifest.load(manifest_path, project_dir)
        assert loaded is not None
        assert loaded.hooks == []

    def test_load_invalid_json(self, project_dir: Path):
        bad_path = project_dir / "bad.json"
        bad_path.write_text("not json")
        assert Manifest.load(bad_path, project_dir) is None

    def test_load_missing_file(self, project_dir: Path):
        assert Manifest.load(project_dir / "nope.json", project_dir) is None

    def test_sha256_deterministic(self):
        h1 = Manifest._sha256("hello")
        h2 = Manifest._sha256("hello")
        assert h1 == h2
        assert len(h1) == 64
