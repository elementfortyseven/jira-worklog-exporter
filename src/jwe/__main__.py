"""Entry point for ``python -m jwe``.

Dispatches to either the CLI or the GUI based on the first argument.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Dispatch to CLI or GUI subcommand."""
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        from jwe.gui import main as gui_main

        return gui_main()

    from jwe.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
