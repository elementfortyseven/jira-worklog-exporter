"""Status bar widget anchored at the bottom of MainWindow (Etappe 5a fill)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class StatusWidget(QWidget):
    """Export button, status label, progress bar, counters, and log panel."""

    _MAX_LOG_LINES = 50

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(140)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(4)

        # Row 1: export button + status label
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.export_btn = QPushButton("Start Export")  # i18n: status.btn.export
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        self.status_label = QLabel("Fill in required fields")  # i18n: status.label.not_ready
        btn_layout.addWidget(self.status_label, 1)
        outer.addWidget(btn_row)

        # Row 2: issue / worklog counters (hidden until export starts)
        self._counter_row = QWidget()
        counter_layout = QHBoxLayout(self._counter_row)
        counter_layout.setContentsMargins(0, 0, 0, 0)
        self.issue_label = QLabel("Issues: 0")      # i18n: status.counter.issues_n
        self.worklog_label = QLabel("Worklogs: 0")  # i18n: status.counter.worklogs_n
        counter_layout.addWidget(self.issue_label)
        counter_layout.addWidget(self.worklog_label)
        counter_layout.addStretch()
        self._counter_row.setVisible(False)
        outer.addWidget(self._counter_row)

        # Row 3: indeterminate progress bar (hidden until export starts)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate marquee by default
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setVisible(False)
        outer.addWidget(self.progress_bar)

        # Row 4: scrollable read-only log panel (hidden until export starts)
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setVisible(False)
        outer.addWidget(self.log_panel)

    # ------------------------------------------------------------------
    # Public API (called by MainWindow._update_export_btn)
    # ------------------------------------------------------------------

    def set_export_enabled(self, enabled: bool) -> None:
        self.export_btn.setEnabled(enabled)

    def set_status_text(self, text: str) -> None:
        self.status_label.setText(text)

    # ------------------------------------------------------------------
    # Progress display lifecycle
    # ------------------------------------------------------------------

    def start_progress_display(self) -> None:
        """Show progress widgets, reset values, and start the progress bar marquee."""
        self.issue_label.setText("Issues: 0")      # i18n: status.counter.issues_n
        self.worklog_label.setText("Worklogs: 0")  # i18n: status.counter.worklogs_n
        self.log_panel.clear()
        self.progress_bar.setRange(0, 0)           # (re-)start marquee animation
        self._counter_row.setVisible(True)
        self.progress_bar.setVisible(True)
        self.log_panel.setVisible(True)

    def stop_progress_display(self) -> None:
        """Hide all progress widgets and reset content.

        Call this as the first step of _on_export_clicked to reset from any
        previous run before calling start_progress_display().
        """
        self._counter_row.setVisible(False)
        self.progress_bar.setVisible(False)
        self.log_panel.setVisible(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.issue_label.setText("Issues: 0")      # i18n: status.counter.issues_n
        self.worklog_label.setText("Worklogs: 0")  # i18n: status.counter.worklogs_n
        self.log_panel.clear()

    def on_progress_done(self) -> None:
        """Stop the marquee animation; keep counter and log visible for the user to read."""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)

    # ------------------------------------------------------------------
    # Slots wired to ExportWorker signals
    # ------------------------------------------------------------------

    def on_progress_updated(self, issues_seen: int, worklogs_written: int) -> None:
        self.issue_label.setText(f"Issues: {issues_seen}")         # i18n: status.counter.issues_n
        self.worklog_label.setText(f"Worklogs: {worklogs_written}")  # i18n: status.counter.worklogs_n

    def append_log_line(self, text: str) -> None:
        """Append *text* to the log panel; keep at most _MAX_LOG_LINES lines."""
        current = self.log_panel.toPlainText()
        lines = current.splitlines() if current else []
        lines.append(text)
        if len(lines) > self._MAX_LOG_LINES:
            lines = lines[-self._MAX_LOG_LINES:]
        self.log_panel.setPlainText("\n".join(lines))
        sb = self.log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
