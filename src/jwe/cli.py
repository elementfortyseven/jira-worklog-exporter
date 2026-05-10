"""Command-line interface for the worklog exporter.

The CLI is the headless / scripted counterpart to the GUI; both consume the
same :class:`jwe.config.ExportConfig` and call :func:`jwe.exporter.run_export`.

TODO (claude code):
1. Build the argparse tree per PRD §11. Use subcommands ``export`` (default)
   and ``discover-cloud-id`` (helper).
2. Implement env-var fallbacks for ``--token``, ``--email``, etc., per
   PRD FR-08.
3. Map exceptions to the exit-code table in PRD §11.
4. Use ``tqdm`` for the progress bar (already a dep). Drive it from the
   :class:`ExportProgress` events yielded by :func:`run_export`.
5. Wire ``logging`` to stderr; set level via ``--verbose``.
6. Ctrl-C handling: catch :class:`KeyboardInterrupt`, set the cancel event,
   let the export close out cleanly, exit code 4.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    TODO: implement subcommands per PRD §11.
    """
    parser = argparse.ArgumentParser(
        prog="jwe-cli",
        description="Export Jira Cloud worklogs of selected users to CSV.",
    )
    parser.add_argument("--version", action="version", version="0.1.0")
    # TODO: add subparsers for "export" and "discover-cloud-id"
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns an exit code per PRD §11."""
    parser = build_parser()
    parser.parse_args(argv if argv is not None else sys.argv[1:])

    # TODO: dispatch on subcommand.
    print("jwe-cli is a skeleton. Run is not implemented yet — see CLAUDE.md.")
    return 5  # placeholder until implemented


if __name__ == "__main__":
    raise SystemExit(main())
