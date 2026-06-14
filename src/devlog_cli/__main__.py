"""Allow `python -m devlog_cli` to invoke the CLI.

A fallback entry point for `devlog upgrade`, which re-invokes the freshly
installed binary and prefers the `devlog` shim but falls back to this.
"""

from devlog_cli import main

if __name__ == "__main__":
    main()
