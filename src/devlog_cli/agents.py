"""
Agent registry for devlog.

Maps AI coding agents to their context file locations.
The convention text gets injected into these files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentConfig:
    key: str
    name: str
    context_file: str  # e.g. "CLAUDE.md", "AGENTS.md"


AGENTS: dict[str, AgentConfig] = {}


def _reg(cfg: AgentConfig) -> None:
    AGENTS[cfg.key] = cfg


# ── Agents with dedicated context files ──────────────────────────────────

_reg(AgentConfig(key="claude", name="Claude Code", context_file="CLAUDE.md"))
_reg(AgentConfig(key="copilot", name="GitHub Copilot", context_file=".github/copilot-instructions.md"))
_reg(AgentConfig(key="gemini", name="Gemini CLI", context_file="GEMINI.md"))

# ── Agents using AGENTS.md ──────────────────────────────────────────────

for _key, _name in [
    ("codex", "Codex CLI"),
    ("cursor-agent", "Cursor Agent"),
    ("kimi", "Kimi K2"),
    ("qwen", "Qwen Agent"),
    ("agy", "AGY"),
    ("trae", "TRAE"),
    ("roo", "Roo Code"),
    ("bob", "Bob Agent"),
    ("auggie", "Auggie CLI"),
    ("kilocode", "Kilocode"),
    ("windsurf", "Windsurf"),
    ("codebuddy", "Codebuddy"),
    ("vibe", "Vibe"),
    ("amp", "Amp"),
    ("kiro-cli", "Kiro CLI"),
    ("tabnine", "Tabnine"),
    ("goose", "Goose"),
    ("pi", "Pi Coding Agent"),
    ("opencode", "OpenCode"),
    ("forge", "Forge"),
    ("shai", "SHAI"),
    ("iflow", "iFlow CLI"),
    ("junie", "Junie"),
    ("qodercli", "QoderCLI"),
]:
    _reg(AgentConfig(key=_key, name=_name, context_file="AGENTS.md"))


def get_agent(key: str) -> AgentConfig:
    """Look up an agent by key. Raises KeyError if not found."""
    if key not in AGENTS:
        raise KeyError(
            f"Unknown agent: {key!r}. "
            f"Available: {', '.join(sorted(AGENTS))}"
        )
    return AGENTS[key]
