"""Tkinter GUI for the worklog exporter.

Layout is described in PRD §10. The GUI is the last thing to implement —
by then all building blocks (config, exporter, csv_writer) exist and the GUI
becomes a thin shell that produces an :class:`jwe.config.ExportConfig` and
runs :func:`jwe.exporter.run_export` in a worker thread.

TODO (claude code):
1. Build the layout per PRD §10. Use ``ttk`` widgets throughout.
2. Auth-mode radio buttons toggle between Service-Account and User-Token
   field groups (use :meth:`grid_remove`/``grid``).
3. Connection test button: POST to a worker thread, await result, paint
   green/red status. **Never call Tk widgets from a worker thread** — use
   ``root.after(100, poll_queue)`` and a :class:`queue.Queue` for events.
4. User search: live results list updated as the user types (debounce
   ~300ms). Selected users go to a second listbox.
5. Date pickers: simple ``ttk.Entry`` with ``YYYY-MM-DD`` validation is
   enough for v1.
6. Export button starts the run; progress bar is driven by ExportProgress
   events from the queue. Cancel button signals a ``threading.Event``.
7. Optional: ``keyring`` integration for token persistence (FR-02 in PRD).
"""

from __future__ import annotations

import sys


def main() -> int:
    """GUI entry point. Returns 0 on clean exit."""
    # TODO: import tkinter only inside main(), so headless CLI users
    # (especially in CI) don't pay the import cost or risk a Tk init failure.
    print("jwe-gui is a skeleton. UI is not implemented yet — see CLAUDE.md.")
    return 5


if __name__ == "__main__":
    sys.exit(main())
