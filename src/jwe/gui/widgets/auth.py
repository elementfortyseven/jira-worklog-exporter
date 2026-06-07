"""Authentication section widget."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import jwe.service as _default_svc
from jwe.api.auth import AuthHeaderStyle, AuthMode
from jwe.config import ExportConfig
from jwe.gui.workers.cloud_id_discover import CloudIdDiscoverWorker
from jwe.gui.workers.connection_test import ConnectionTestWorker
from jwe.i18n import DEFAULT_LANG, diag, t

logger = logging.getLogger(__name__)

_S = "auth"  # QSettings key prefix


class ServiceAccountPanel(QWidget):
    """Fields for Service Account authentication."""

    discover_requested = Signal(str)  # emits discovery_url on Discover click

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Site URL row: field + Discover button
        url_row = QWidget()
        url_layout = QHBoxLayout(url_row)
        url_layout.setContentsMargins(0, 0, 0, 0)
        self.discovery_url_field = QLineEdit()
        self.discover_btn = QPushButton()
        self.discover_btn.setFixedWidth(80)
        url_layout.addWidget(self.discovery_url_field, 1)
        url_layout.addWidget(self.discover_btn)
        self._lbl_site_url = QLabel()
        layout.addRow(self._lbl_site_url, url_row)

        self.cloud_id_field = QLineEdit()
        self._lbl_cloud_id = QLabel()
        layout.addRow(self._lbl_cloud_id, self.cloud_id_field)

        self.email_field = QLineEdit()
        self._lbl_email = QLabel()
        layout.addRow(self._lbl_email, self.email_field)

        self.token_field = QLineEdit()
        self.token_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_token = QLabel()
        layout.addRow(self._lbl_token, self.token_field)

        self.auth_header_combo = QComboBox()
        self.auth_header_combo.addItem("Basic", AuthHeaderStyle.BASIC.value)
        self.auth_header_combo.addItem("Bearer", AuthHeaderStyle.BEARER.value)
        self._lbl_auth_header = QLabel()
        layout.addRow(self._lbl_auth_header, self.auth_header_combo)

        self.discover_btn.clicked.connect(
            lambda: self.discover_requested.emit(self.discovery_url_field.text().strip())
        )

        self.retranslate_ui(DEFAULT_LANG)

    def retranslate_ui(self, lang: str) -> None:
        """Update translatable strings for *lang*."""
        self._lbl_site_url.setText(t("auth.sa.label.site_url", lang))
        self._lbl_cloud_id.setText(t("auth.sa.label.cloud_id", lang))
        self._lbl_email.setText(t("auth.sa.label.email", lang))
        self._lbl_token.setText(t("auth.sa.label.token", lang))
        self._lbl_auth_header.setText(t("auth.sa.label.auth_header", lang))
        self.discovery_url_field.setPlaceholderText(t("auth.sa.discovery_url.placeholder", lang))
        self.cloud_id_field.setPlaceholderText(t("auth.sa.cloud_id.placeholder", lang))
        self.email_field.setPlaceholderText(t("auth.sa.email.placeholder", lang))
        self.token_field.setPlaceholderText(t("auth.sa.token.placeholder", lang))
        self.discover_btn.setText(t("auth.btn.discover_cloud_id", lang))


class UserTokenPanel(QWidget):
    """Fields for personal API token authentication."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.site_url_field = QLineEdit()
        self._lbl_site_url = QLabel()
        layout.addRow(self._lbl_site_url, self.site_url_field)

        self.email_field = QLineEdit()
        self._lbl_email = QLabel()
        layout.addRow(self._lbl_email, self.email_field)

        self.token_field = QLineEdit()
        self.token_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_token = QLabel()
        layout.addRow(self._lbl_token, self.token_field)

        self.retranslate_ui(DEFAULT_LANG)

    def retranslate_ui(self, lang: str) -> None:
        """Update translatable strings for *lang*."""
        self._lbl_site_url.setText(t("auth.user.label.site_url", lang))
        self._lbl_email.setText(t("auth.user.label.email", lang))
        self._lbl_token.setText(t("auth.user.label.token", lang))
        self.site_url_field.setPlaceholderText(t("auth.user.site_url.placeholder", lang))
        self.email_field.setPlaceholderText(t("auth.user.email.placeholder", lang))
        self.token_field.setPlaceholderText(t("auth.user.token.placeholder", lang))


class AuthWidget(QGroupBox):
    """Collects auth-mode, credentials, and triggers connection test."""

    validation_changed    = Signal()
    connection_verified   = Signal(object)  # payload: ExportConfig
    connection_invalidated = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        service: Any = None,
    ) -> None:
        super().__init__(t("section.auth.title", DEFAULT_LANG), parent)
        self._lang: str = DEFAULT_LANG
        self._svc: Any = service if service is not None else _default_svc
        self._conn_thread: QThread | None = None
        self._conn_worker: ConnectionTestWorker | None = None
        self._disc_thread: QThread | None = None
        self._disc_worker: CloudIdDiscoverWorker | None = None
        self._verified: bool = False
        self._last_test_config: ExportConfig | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 16, 8, 8)
        outer.setSpacing(6)

        # Mode radio buttons
        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        self.sa_radio = QRadioButton()
        self.user_radio = QRadioButton()
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.sa_radio, 0)
        self._mode_group.addButton(self.user_radio, 1)
        self.sa_radio.setChecked(True)
        mode_layout.addWidget(self.sa_radio)
        mode_layout.addWidget(self.user_radio)
        mode_layout.addStretch()
        outer.addWidget(mode_row)

        # Stacked panels (index 0 = SA, index 1 = User)
        self.stack = QStackedWidget()
        self.sa_panel = ServiceAccountPanel()
        self.user_panel = UserTokenPanel()
        self.stack.addWidget(self.sa_panel)
        self.stack.addWidget(self.user_panel)
        outer.addWidget(self.stack)

        # Keyring row
        keyring_row = QWidget()
        keyring_layout = QHBoxLayout(keyring_row)
        keyring_layout.setContentsMargins(0, 0, 0, 0)
        self.save_token_cb = QCheckBox()
        self.keyring_info_label = QLabel("")
        self.keyring_info_label.setVisible(False)
        keyring_layout.addWidget(self.save_token_cb)
        keyring_layout.addWidget(self.keyring_info_label)
        keyring_layout.addStretch()
        outer.addWidget(keyring_row)

        # Test Connection row
        test_row = QWidget()
        test_layout = QHBoxLayout(test_row)
        test_layout.setContentsMargins(0, 0, 0, 0)
        self.test_btn = QPushButton()
        self.status_label = QLabel("")
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(self.status_label, 1)
        outer.addWidget(test_row)

        self._mode_group.idClicked.connect(self._on_mode_changed)
        self.sa_panel.discover_requested.connect(self._on_discover_requested)
        self.test_btn.clicked.connect(self._on_test_connection_clicked)
        self.save_token_cb.toggled.connect(self._on_save_token_toggled)

        # Validation wiring -- route through _on_field_changed so that
        # connection_invalidated is emitted when fields change after a successful verify.
        self.sa_panel.cloud_id_field.textChanged.connect(lambda _: self._on_field_changed())
        self.sa_panel.email_field.textChanged.connect(lambda _: self._on_field_changed())
        self.sa_panel.token_field.textChanged.connect(lambda _: self._on_field_changed())
        self.user_panel.site_url_field.textChanged.connect(lambda _: self._on_field_changed())
        self.user_panel.email_field.textChanged.connect(lambda _: self._on_field_changed())
        self.user_panel.token_field.textChanged.connect(lambda _: self._on_field_changed())
        self._mode_group.idClicked.connect(lambda _: self._on_field_changed())

        self.retranslate_ui(DEFAULT_LANG)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_mode(self) -> AuthMode:
        return AuthMode.SERVICE_ACCOUNT if self.sa_radio.isChecked() else AuthMode.USER_TOKEN

    def _current_identifier(self) -> str:
        if self._current_mode() == AuthMode.SERVICE_ACCOUNT:
            return self.sa_panel.cloud_id_field.text().strip()
        return self.user_panel.site_url_field.text().strip()

    def _current_token_field(self) -> QLineEdit:
        if self._current_mode() == AuthMode.SERVICE_ACCOUNT:
            return self.sa_panel.token_field
        return self.user_panel.token_field

    def get_export_config_partial(self) -> ExportConfig:
        """Build an ExportConfig with only the auth fields filled in.

        MainWindow._build_config() calls this and fills in the remaining fields
        (user_account_ids, dates, output settings).
        """
        mode = self._current_mode()
        if mode == AuthMode.SERVICE_ACCOUNT:
            header_val = self.sa_panel.auth_header_combo.currentData()
            return ExportConfig(
                auth_mode=mode,
                cloud_id=self.sa_panel.cloud_id_field.text().strip(),
                service_account_email=self.sa_panel.email_field.text().strip(),
                api_token=self.sa_panel.token_field.text(),
                auth_header=AuthHeaderStyle(header_val),
            )
        return ExportConfig(
            auth_mode=mode,
            site_url=self.user_panel.site_url_field.text().strip().rstrip("/"),
            email=self.user_panel.email_field.text().strip(),
            api_token=self.user_panel.token_field.text(),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        """Return True when all required credentials fields for the current mode are non-empty."""
        if self._current_mode() == AuthMode.SERVICE_ACCOUNT:
            return bool(
                self.sa_panel.cloud_id_field.text().strip()
                and self.sa_panel.email_field.text().strip()
                and self.sa_panel.token_field.text()
            )
        return bool(
            self.user_panel.site_url_field.text().strip()
            and self.user_panel.email_field.text().strip()
            and self.user_panel.token_field.text()
        )

    # ------------------------------------------------------------------
    # Keyring
    # ------------------------------------------------------------------

    def _init_keyring(self) -> None:
        """Pre-fill token from keyring; disable checkbox if keyring unavailable.

        Called at the end of load_settings so cloud_id/site_url are populated.
        """
        try:
            mode = self._current_mode()
            identifier = self._current_identifier()
            # Probe with "__probe__" when identifier is empty so we still detect
            # RuntimeError from a missing keyring package upfront.
            token: str | None = self._svc.load_token(
                mode, identifier if identifier else "__probe__"
            )
            if token and identifier:
                self._current_token_field().setText(token)
                self.save_token_cb.setChecked(True)
        except RuntimeError:
            self.save_token_cb.setEnabled(False)
            self.keyring_info_label.setText(diag("auth.keyring.unavailable"))
            self.keyring_info_label.setVisible(True)

    # ------------------------------------------------------------------
    # Field-change dispatcher
    # ------------------------------------------------------------------

    def _on_field_changed(self) -> None:
        """Emit connection_invalidated (once) when fields change after a successful verify."""
        if self._verified:
            self._verified = False
            self.connection_invalidated.emit()
        self.validation_changed.emit()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self, button_id: int) -> None:
        self.stack.setCurrentIndex(button_id)
        if self.save_token_cb.isEnabled():
            identifier = self._current_identifier()
            if identifier:
                try:
                    token = self._svc.load_token(self._current_mode(), identifier)
                    if token:
                        self._current_token_field().setText(token)
                        self.save_token_cb.setChecked(True)
                except RuntimeError:
                    pass

    def _on_test_connection_clicked(self) -> None:
        self.test_btn.setEnabled(False)
        self.status_label.setText(t("auth.status.testing", self._lang))
        config = self.get_export_config_partial()
        self._last_test_config = config  # stored so _on_conn_finished can emit it
        worker = ConnectionTestWorker(config, self._svc.test_connection)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._on_conn_finished)
        worker.failed.connect(self._on_conn_failed)
        worker.finished.connect(self._on_conn_worker_done)
        worker.failed.connect(self._on_conn_worker_done)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_conn_refs)
        thread.started.connect(worker.run)
        self._conn_thread = thread
        self._conn_worker = worker
        thread.start()

    def _on_conn_finished(self, display_name: str, email: str) -> None:
        self.status_label.setText(
            t("auth.status.connected", self._lang, display_name=display_name, email=email)
        )
        if self.save_token_cb.isChecked():
            identifier = self._current_identifier()
            token = self._current_token_field().text()
            if identifier and token:
                with contextlib.suppress(RuntimeError):
                    self._svc.save_token(self._current_mode(), identifier, token)
        self._verified = True
        if self._last_test_config is not None:
            self.connection_verified.emit(self._last_test_config)

    def _on_conn_failed(self, message: str) -> None:
        self.status_label.setText(message)
        self._verified = False

    def _on_conn_worker_done(self) -> None:
        self.test_btn.setEnabled(True)
        if self._conn_thread is not None:
            self._conn_thread.quit()

    def _clear_conn_refs(self) -> None:
        self._conn_thread = None
        self._conn_worker = None

    def _on_discover_requested(self, site_url: str) -> None:
        if not site_url:
            return
        self.sa_panel.discover_btn.setEnabled(False)
        worker = CloudIdDiscoverWorker(site_url, self._svc.discover_cloud_id)
        thread = QThread()
        worker.moveToThread(thread)
        worker.discovered.connect(self._on_discovered)
        worker.failed.connect(self._on_discover_failed)
        worker.discovered.connect(self._on_disc_worker_done)
        worker.failed.connect(self._on_disc_worker_done)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_disc_refs)
        thread.started.connect(worker.run)
        self._disc_thread = thread
        self._disc_worker = worker
        thread.start()

    def _on_discovered(self, cloud_id: str) -> None:
        self.sa_panel.cloud_id_field.setText(cloud_id)
        self.status_label.setText(
            t("auth.status.cloud_id_found", self._lang, cloud_id=cloud_id)
        )

    def _on_discover_failed(self, message: str) -> None:
        self.status_label.setText(diag("auth.status.discovery_failed", message=message))

    def _on_disc_worker_done(self) -> None:
        self.sa_panel.discover_btn.setEnabled(True)
        if self._disc_thread is not None:
            self._disc_thread.quit()

    def _clear_disc_refs(self) -> None:
        self._disc_thread = None
        self._disc_worker = None

    def _on_save_token_toggled(self, checked: bool) -> None:
        if not checked:
            identifier = self._current_identifier()
            if identifier:
                with contextlib.suppress(RuntimeError):
                    self._svc.delete_token(self._current_mode(), identifier)

    # ------------------------------------------------------------------
    # Thread lifecycle (called from MainWindow.closeEvent)
    # ------------------------------------------------------------------

    def stop_running_threads(self) -> None:
        # TODO etappe 5b: graceful cancel for export worker
        threads = [th for th in (self._conn_thread, self._disc_thread) if th is not None and th.isRunning()]
        for thread in threads:
            thread.quit()
        for thread in threads:
            if not thread.wait(2000):
                logger.warning("Thread did not stop within timeout: %r", thread)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def save_settings(self, settings: QSettings) -> None:
        """Persist all auth field values (not the API token)."""
        settings.setValue(
            f"{_S}/mode",
            0 if self._current_mode() == AuthMode.SERVICE_ACCOUNT else 1,
        )
        settings.setValue(f"{_S}/cloud_id", self.sa_panel.cloud_id_field.text())
        settings.setValue(f"{_S}/sa_email", self.sa_panel.email_field.text())
        settings.setValue(f"{_S}/sa_discovery_url", self.sa_panel.discovery_url_field.text())
        settings.setValue(f"{_S}/auth_header", self.sa_panel.auth_header_combo.currentIndex())
        settings.setValue(f"{_S}/site_url", self.user_panel.site_url_field.text())
        settings.setValue(f"{_S}/email", self.user_panel.email_field.text())

    def load_settings(self, settings: QSettings) -> None:
        """Restore all persisted auth field values, then probe keyring."""

        def _str(key: str, default: str = "") -> str:
            return str(settings.value(key, default))

        # QSettings.value() returns object (str or int depending on backend); int(str(...)) handles both.
        mode_idx = int(str(settings.value(f"{_S}/mode", 0)))
        if mode_idx == 1:
            self.user_radio.setChecked(True)
            self.stack.setCurrentIndex(1)
        else:
            self.sa_radio.setChecked(True)
            self.stack.setCurrentIndex(0)

        self.sa_panel.cloud_id_field.setText(_str(f"{_S}/cloud_id"))
        self.sa_panel.email_field.setText(_str(f"{_S}/sa_email"))
        self.sa_panel.discovery_url_field.setText(_str(f"{_S}/sa_discovery_url"))
        # QSettings.value() returns object (str or int depending on backend); int(str(...)) handles both.
        header_idx = int(str(settings.value(f"{_S}/auth_header", 0)))
        self.sa_panel.auth_header_combo.setCurrentIndex(header_idx)
        self.user_panel.site_url_field.setText(_str(f"{_S}/site_url"))
        self.user_panel.email_field.setText(_str(f"{_S}/email"))

        self._init_keyring()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update translatable strings for *lang*."""
        self._lang = lang
        self.setTitle(t("section.auth.title", lang))
        self.sa_radio.setText(t("auth.radio.service_account", lang))
        self.user_radio.setText(t("auth.radio.user_token", lang))
        self.save_token_cb.setText(t("auth.checkbox.save_token", lang))
        self.test_btn.setText(t("auth.btn.test_connection", lang))
        self.sa_panel.retranslate_ui(lang)
        self.user_panel.retranslate_ui(lang)
