"""Status bar widget anchored at the bottom of MainWindow (Etappe 5a fill)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from jwe.i18n import DEFAULT_LANG, t


class StatusWidget(QWidget):
    """Export button, cancel button, status label, progress bar, counters, log panel, and result buttons."""

    _MAX_LOG_LINES = 50

    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lang: str = DEFAULT_LANG
        self._issues_seen: int = 0
        self._worklogs_written: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(4)

        # Row 1: export button + cancel button + status label
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.export_btn = QPushButton()
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_requested)
        btn_layout.addWidget(self.cancel_btn)
        self.status_label = QLabel(t("status.label.not_ready", DEFAULT_LANG))
        btn_layout.addWidget(self.status_label, 1)
        outer.addWidget(btn_row)

        # Row 2: issue / worklog counters (hidden until export starts)
        self._counter_row = QWidget()
        counter_layout = QHBoxLayout(self._counter_row)
        counter_layout.setContentsMargins(0, 0, 0, 0)
        self.issue_label = QLabel()
        self.worklog_label = QLabel()
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
        self.log_panel.setFixedHeight(80)
        self.log_panel.setVisible(False)
        outer.addWidget(self.log_panel)

        # Row 5: result buttons (hidden until export finishes)
        self._result_row = QWidget()
        result_layout = QHBoxLayout(self._result_row)
        result_layout.setContentsMargins(0, 0, 0, 0)
        self.open_csv_btn = QPushButton()
        self.open_folder_btn = QPushButton()
        result_layout.addWidget(self.open_csv_btn)
        result_layout.addWidget(self.open_folder_btn)
        result_layout.addStretch()
        self._result_row.setVisible(False)
        outer.addWidget(self._result_row)

        self.retranslate_ui(DEFAULT_LANG)

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
        self._issues_seen = 0
        self._worklogs_written = 0
        self.issue_label.setText(t("status.counter.issues_n", self._lang, n=0))
        self.worklog_label.setText(t("status.counter.worklogs_n", self._lang, n=0))
        self.log_panel.clear()
        self.progress_bar.setRange(0, 0)           # (re-)start marquee animation
        self._counter_row.setVisible(True)
        self.progress_bar.setVisible(True)
        self.log_panel.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)
        self._result_row.setVisible(False)

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
        self._issues_seen = 0
        self._worklogs_written = 0
        self.issue_label.setText(t("status.counter.issues_n", self._lang, n=0))
        self.worklog_label.setText(t("status.counter.worklogs_n", self._lang, n=0))
        self.log_panel.clear()
        self.cancel_btn.setVisible(False)
        self._result_row.setVisible(False)

    def on_progress_done(self) -> None:
        """Stop the marquee animation; keep counter and log visible for the user to read."""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)

    def disable_cancel_btn(self) -> None:
        """Disable the cancel button (keep visible) to signal cancellation is pending."""
        self.cancel_btn.setEnabled(False)

    def hide_cancel_btn(self) -> None:
        """Hide the cancel button."""
        self.cancel_btn.setVisible(False)

    def show_result_buttons(self, csv_path: str) -> None:
        """Make the result row visible after a successful export."""
        _ = csv_path  # path stored in MainWindow; buttons call back via slots
        self._result_row.setVisible(True)

    # ------------------------------------------------------------------
    # Slots wired to ExportWorker signals
    # ------------------------------------------------------------------

    def on_progress_updated(self, issues_seen: int, worklogs_written: int) -> None:
        self._issues_seen = issues_seen
        self._worklogs_written = worklogs_written
        self.issue_label.setText(t("status.counter.issues_n", self._lang, n=issues_seen))
        self.worklog_label.setText(t("status.counter.worklogs_n", self._lang, n=worklogs_written))

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
        self._lang = lang
        self.export_btn.setText(t("status.btn.export", lang))
        self.cancel_btn.setText(t("status.btn.cancel", lang))
        self.open_csv_btn.setText(t("status.btn.open_csv", lang))
        self.open_folder_btn.setText(t("status.btn.open_folder", lang))
        self.issue_label.setText(t("status.counter.issues_n", lang, n=self._issues_seen))
        self.worklog_label.setText(t("status.counter.worklogs_n", lang, n=self._worklogs_written))
        # status_label is managed by MainWindow via set_status_text; not retranslated here
