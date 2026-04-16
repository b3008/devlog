"""
File manifest tracker for devlog installations.

Records SHA-256 hashes of installed files and injected sections
so uninstallation can safely revert changes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class Manifest:
    """Track installed files and injected content for safe uninstallation."""

    def __init__(self, agent_key: str, project_root: Path, version: str = "0.1.0"):
        self.agent_key = agent_key
        self.project_root = project_root
        self.version = version
        self.installed_at = datetime.now(timezone.utc).isoformat()
        self.files: dict[str, str] = {}  # relative path -> sha256
        # Hooks installed into agent settings files (e.g. .claude/settings.json).
        # Each entry: {"event": "Stop", "settings_path": ".claude/settings.json",
        #              "script_path": ".devlog/hooks/stop.py", "command": "python3 ..."}
        self.hooks: list[dict[str, Any]] = []

    @property
    def manifest_path(self) -> Path:
        return self.project_root / ".devlog" / "manifests" / f"{self.agent_key}.manifest.json"

    def save(self) -> Path:
        """Write manifest JSON and return its path."""
        data = {
            "agent": self.agent_key,
            "version": self.version,
            "installed_at": self.installed_at,
            "files": self.files,
            "hooks": self.hooks,
        }
        path = self.manifest_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, path: Path, project_root: Path) -> Optional["Manifest"]:
        """Load a manifest from path. Returns None if invalid."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        m = cls(
            agent_key=data["agent"],
            project_root=project_root,
            version=data.get("version", "unknown"),
        )
        m.installed_at = data.get("installed_at", "")
        m.files = data.get("files", {})
        m.hooks = data.get("hooks", [])
        return m

    @staticmethod
    def _sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
