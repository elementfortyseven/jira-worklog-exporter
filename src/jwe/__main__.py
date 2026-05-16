"""Entry point for ``python -m jwe``.

Dispatches to the CLI (which includes the ``gui`` subcommand) via argparse.
"""

from __future__ import annotations

import sys

from jwe.cli import main

if __name__ == "__main__":
    sys.exit(main())
