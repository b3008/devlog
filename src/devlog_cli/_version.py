"""Single source of truth for the devlog version.

Lives in its own module (imported by both __init__ and convention) so the
sentinel stamp can carry the version without an import cycle. Keep in sync
with pyproject.toml.
"""

__version__ = "0.2.0"
