"""Tests for AuthWidget, ServiceAccountPanel, UserTokenPanel -- Etappe 2."""

from __future__ import annotations

import threading
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSettings, Qt

from jwe.api.auth import AuthMode
from jwe.api.client import AuthenticationError, JiraPermissionError
from jwe.api.tenant_info import TenantInfo
from jwe.api.user import User
from jwe.config import ExportConfig
from jwe.gui.widgets.auth import AuthWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FAKE_USER = User(account_id="acc-1", display_name="Bot User", email="bot@sa.atlassian.com", active=True)
_FAKE_CLOUD_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


@pytest.fixture
def mock_svc() -> MagicMock:
    svc = MagicMock()
    svc.load_token.return_value = None  # no stored token by default
    return svc


@pytest.fixture
def auth_widget(qtbot, mock_svc: MagicMock) -> Generator[AuthWidget, None, None]:
    w = AuthWidget(service=mock_svc)
    qtbot.addWidget(w)
    yield w
    w.stop_running_threads()


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def _fill_sa_fields(widget: AuthWidget, cloud_id: str = "cloud-id-123") -> None:
    widget.sa_panel.cloud_id_field.setText(cloud_id)
    widget.sa_panel.email_field.setText("bot@sa.atlassian.com")
    widget.sa_panel.token_field.setText("secret-token")


# ---------------------------------------------------------------------------
# Mode switch
# ---------------------------------------------------------------------------


class TestModeSwitch:
    def test_sa_radio_checked_by_default(self, auth_widget: AuthWidget) -> None:
        assert auth_widget.sa_radio.isChecked()
        assert not auth_widget.user_radio.isChecked()

    def test_stack_index_0_by_default(self, auth_widget: AuthWidget) -> None:
        assert auth_widget.stack.currentIndex() == 0

    def test_switch_to_user_token_changes_stack(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        qtbot.mouseClick(auth_widget.user_radio, Qt.MouseButton.LeftButton)
        assert auth_widget.stack.currentIndex() == 1

    def test_switch_back_to_sa_changes_stack(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        qtbot.mouseClick(auth_widget.user_radio, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(auth_widget.sa_radio, Qt.MouseButton.LeftButton)
        assert auth_widget.stack.currentIndex() == 0


# ---------------------------------------------------------------------------
# SA panel fields
# ---------------------------------------------------------------------------


class TestSAPanelFields:
    def test_has_discovery_url_field(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.sa_panel, "discovery_url_field")

    def test_has_cloud_id_field(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.sa_panel, "cloud_id_field")

    def test_has_email_field(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.sa_panel, "email_field")

    def test_has_token_field_password_mode(self, auth_widget: AuthWidget) -> None:
        from PySide6.QtWidgets import QLineEdit
        assert auth_widget.sa_panel.token_field.echoMode() == QLineEdit.EchoMode.Password

    def test_has_auth_header_combo_with_basic_and_bearer(
        self, auth_widget: AuthWidget
    ) -> None:
        combo = auth_widget.sa_panel.auth_header_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        assert "Basic" in items
        assert "Bearer" in items

    def test_has_discover_btn(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.sa_panel, "discover_btn")


# ---------------------------------------------------------------------------
# User panel fields
# ---------------------------------------------------------------------------


class TestUserPanelFields:
    def test_has_site_url_field(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.user_panel, "site_url_field")

    def test_has_email_field(self, auth_widget: AuthWidget) -> None:
        assert hasattr(auth_widget.user_panel, "email_field")

    def test_has_token_field_password_mode(self, auth_widget: AuthWidget) -> None:
        from PySide6.QtWidgets import QLineEdit
        assert auth_widget.user_panel.token_field.echoMode() == QLineEdit.EchoMode.Password


# ---------------------------------------------------------------------------
# Connection test worker
# ---------------------------------------------------------------------------


class TestConnectionTest:
    def test_connect_btn_starts_worker_and_service_is_called(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.return_value = _FAKE_USER
        _fill_sa_fields(auth_widget)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        mock_svc.test_connection.assert_called_once()

    def test_connect_btn_disabled_while_worker_running(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        barrier = threading.Event()

        def slow_test(config):  # type: ignore[no-untyped-def]
            barrier.wait(timeout=5.0)
            return _FAKE_USER

        mock_svc.test_connection.side_effect = slow_test
        _fill_sa_fields(auth_widget)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        assert not auth_widget.test_btn.isEnabled()

        barrier.set()
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

    def test_connect_success_updates_status_label(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.return_value = _FAKE_USER
        _fill_sa_fields(auth_widget)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        assert "Bot User" in auth_widget.status_label.text()

    def test_connect_auth_error_shows_specific_message(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.side_effect = AuthenticationError("bad token")
        _fill_sa_fields(auth_widget)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        text = auth_widget.status_label.text()
        assert "Authentication failed" in text
        assert "scopes" in text

    def test_connect_permission_error_shows_specific_message(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.side_effect = JiraPermissionError("no permission")
        _fill_sa_fields(auth_widget)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        text = auth_widget.status_label.text()
        assert "Permission denied" in text
        assert "scopes" in text

    def test_connect_saves_token_when_checkbox_checked(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.return_value = _FAKE_USER
        _fill_sa_fields(auth_widget, cloud_id="cloud-id-123")
        auth_widget.save_token_cb.setChecked(True)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        mock_svc.save_token.assert_called_once_with(
            AuthMode.SERVICE_ACCOUNT, "cloud-id-123", "secret-token"
        )

    def test_connect_does_not_save_token_when_checkbox_unchecked(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.test_connection.return_value = _FAKE_USER
        _fill_sa_fields(auth_widget)
        auth_widget.save_token_cb.setChecked(False)

        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)

        mock_svc.save_token.assert_not_called()


# ---------------------------------------------------------------------------
# Cloud ID discovery
# ---------------------------------------------------------------------------


class TestCloudIdDiscovery:
    def test_discover_btn_fills_cloud_id_field(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.discover_cloud_id.return_value = TenantInfo(cloud_id=_FAKE_CLOUD_ID)
        auth_widget.sa_panel.discovery_url_field.setText("https://company.atlassian.net")

        qtbot.mouseClick(auth_widget.sa_panel.discover_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: auth_widget.sa_panel.discover_btn.isEnabled(), timeout=3000
        )

        assert auth_widget.sa_panel.cloud_id_field.text() == _FAKE_CLOUD_ID

    def test_discover_btn_disabled_while_worker_running(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        barrier = threading.Event()

        def slow_discover(url):  # type: ignore[no-untyped-def]
            barrier.wait(timeout=5.0)
            return TenantInfo(cloud_id=_FAKE_CLOUD_ID)

        mock_svc.discover_cloud_id.side_effect = slow_discover
        auth_widget.sa_panel.discovery_url_field.setText("https://company.atlassian.net")

        qtbot.mouseClick(auth_widget.sa_panel.discover_btn, Qt.MouseButton.LeftButton)
        assert not auth_widget.sa_panel.discover_btn.isEnabled()

        barrier.set()
        qtbot.waitUntil(
            lambda: auth_widget.sa_panel.discover_btn.isEnabled(), timeout=3000
        )

    def test_discover_failure_shown_in_status_label(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        mock_svc.discover_cloud_id.side_effect = Exception("unreachable")
        auth_widget.sa_panel.discovery_url_field.setText("https://bad.example.com")

        qtbot.mouseClick(auth_widget.sa_panel.discover_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: auth_widget.sa_panel.discover_btn.isEnabled(), timeout=3000
        )

        assert "Discovery failed" in auth_widget.status_label.text()

    def test_discover_btn_does_nothing_on_empty_url(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        auth_widget.sa_panel.discovery_url_field.setText("")
        qtbot.mouseClick(auth_widget.sa_panel.discover_btn, Qt.MouseButton.LeftButton)
        mock_svc.discover_cloud_id.assert_not_called()


# ---------------------------------------------------------------------------
# Keyring
# ---------------------------------------------------------------------------


class TestKeyring:
    def test_keyring_load_prefills_token_after_load_settings(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        svc = MagicMock()
        svc.load_token.return_value = "my-secret-token"

        w = AuthWidget(service=svc)
        qtbot.addWidget(w)
        isolated_settings.setValue("auth/cloud_id", "cloud-id-abc")
        w.load_settings(isolated_settings)

        assert w.sa_panel.token_field.text() == "my-secret-token"
        assert w.save_token_cb.isChecked()

    def test_keyring_runtime_error_disables_checkbox(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        svc = MagicMock()
        svc.load_token.side_effect = RuntimeError("keyring not installed")

        w = AuthWidget(service=svc)
        qtbot.addWidget(w)
        isolated_settings.setValue("auth/cloud_id", "cloud-id-abc")
        w.load_settings(isolated_settings)

        assert not w.save_token_cb.isEnabled()
        assert not w.keyring_info_label.isHidden()  # isVisible() is False when parent not shown

    def test_keyring_uncheck_calls_delete_token(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        auth_widget.sa_panel.cloud_id_field.setText("cloud-id-123")
        auth_widget.save_token_cb.setChecked(True)
        auth_widget.save_token_cb.setChecked(False)

        mock_svc.delete_token.assert_called_once_with(
            AuthMode.SERVICE_ACCOUNT, "cloud-id-123"
        )

    def test_keyring_no_delete_when_identifier_empty(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        auth_widget.sa_panel.cloud_id_field.setText("")
        auth_widget.save_token_cb.setChecked(True)
        auth_widget.save_token_cb.setChecked(False)
        mock_svc.delete_token.assert_not_called()


# ---------------------------------------------------------------------------
# QSettings round-trip
# ---------------------------------------------------------------------------


class TestQSettingsRoundTrip:
    def test_auth_settings_round_trip(
        self, qtbot, isolated_settings: QSettings, mock_svc: MagicMock
    ) -> None:
        w1 = AuthWidget(service=mock_svc)
        qtbot.addWidget(w1)
        w1.user_radio.setChecked(True)
        w1.sa_panel.cloud_id_field.setText("cloud-id-xyz")
        w1.sa_panel.email_field.setText("bot@sa.atlassian.com")
        w1.sa_panel.discovery_url_field.setText("https://co.atlassian.net")
        w1.sa_panel.auth_header_combo.setCurrentIndex(1)  # Bearer
        w1.user_panel.site_url_field.setText("https://site.atlassian.net")
        w1.user_panel.email_field.setText("me@example.com")
        w1.save_settings(isolated_settings)

        w2 = AuthWidget(service=mock_svc)
        qtbot.addWidget(w2)
        w2.load_settings(isolated_settings)

        assert w2.user_radio.isChecked()
        assert w2.stack.currentIndex() == 1
        assert w2.sa_panel.cloud_id_field.text() == "cloud-id-xyz"
        assert w2.sa_panel.email_field.text() == "bot@sa.atlassian.com"
        assert w2.sa_panel.discovery_url_field.text() == "https://co.atlassian.net"
        assert w2.sa_panel.auth_header_combo.currentIndex() == 1
        assert w2.user_panel.site_url_field.text() == "https://site.atlassian.net"
        assert w2.user_panel.email_field.text() == "me@example.com"


# ---------------------------------------------------------------------------
# is_valid -- Etappe 4 retrofit
# ---------------------------------------------------------------------------


class TestIsValidServiceAccount:
    def test_valid_sa_when_all_fields_filled(
        self, auth_widget: AuthWidget
    ) -> None:
        _fill_sa_fields(auth_widget)
        assert auth_widget.is_valid() is True

    def test_invalid_sa_when_cloud_id_empty(self, auth_widget: AuthWidget) -> None:
        _fill_sa_fields(auth_widget)
        auth_widget.sa_panel.cloud_id_field.setText("")
        assert auth_widget.is_valid() is False

    def test_invalid_sa_when_email_empty(self, auth_widget: AuthWidget) -> None:
        _fill_sa_fields(auth_widget)
        auth_widget.sa_panel.email_field.setText("")
        assert auth_widget.is_valid() is False

    def test_invalid_sa_when_token_empty(self, auth_widget: AuthWidget) -> None:
        _fill_sa_fields(auth_widget)
        auth_widget.sa_panel.token_field.setText("")
        assert auth_widget.is_valid() is False


class TestIsValidUserToken:
    def _fill_user_fields(self, w: AuthWidget) -> None:
        w.user_radio.setChecked(True)
        w.stack.setCurrentIndex(1)
        w.user_panel.site_url_field.setText("https://company.atlassian.net")
        w.user_panel.email_field.setText("me@example.com")
        w.user_panel.token_field.setText("my-token")

    def test_valid_user_when_all_fields_filled(
        self, auth_widget: AuthWidget
    ) -> None:
        self._fill_user_fields(auth_widget)
        assert auth_widget.is_valid() is True

    def test_invalid_user_when_site_url_empty(
        self, auth_widget: AuthWidget
    ) -> None:
        self._fill_user_fields(auth_widget)
        auth_widget.user_panel.site_url_field.setText("")
        assert auth_widget.is_valid() is False

    def test_invalid_user_when_email_empty(
        self, auth_widget: AuthWidget
    ) -> None:
        self._fill_user_fields(auth_widget)
        auth_widget.user_panel.email_field.setText("")
        assert auth_widget.is_valid() is False

    def test_invalid_user_when_token_empty(
        self, auth_widget: AuthWidget
    ) -> None:
        self._fill_user_fields(auth_widget)
        auth_widget.user_panel.token_field.setText("")
        assert auth_widget.is_valid() is False


# ---------------------------------------------------------------------------
# validation_changed -- Etappe 4 retrofit
# ---------------------------------------------------------------------------


class TestValidationChangedSignal:
    def test_emitted_on_sa_cloud_id_change(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        with qtbot.waitSignal(auth_widget.validation_changed, timeout=500):
            auth_widget.sa_panel.cloud_id_field.setText("new-id")

    def test_emitted_on_sa_email_change(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        with qtbot.waitSignal(auth_widget.validation_changed, timeout=500):
            auth_widget.sa_panel.email_field.setText("bot@sa.atlassian.com")

    def test_emitted_on_sa_token_change(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        with qtbot.waitSignal(auth_widget.validation_changed, timeout=500):
            auth_widget.sa_panel.token_field.setText("secret")

    def test_emitted_on_user_site_url_change(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        with qtbot.waitSignal(auth_widget.validation_changed, timeout=500):
            auth_widget.user_panel.site_url_field.setText("https://co.atlassian.net")

    def test_emitted_on_mode_switch(self, qtbot, auth_widget: AuthWidget) -> None:
        with qtbot.waitSignal(auth_widget.validation_changed, timeout=500):
            qtbot.mouseClick(auth_widget.user_radio, Qt.MouseButton.LeftButton)


# ---------------------------------------------------------------------------
# connection_verified / connection_invalidated signals
# ---------------------------------------------------------------------------


def _do_successful_test(qtbot, auth_widget: AuthWidget, mock_svc: MagicMock) -> None:
    """Helper: fill SA fields, click test, wait for completion."""
    mock_svc.test_connection.return_value = _FAKE_USER
    _fill_sa_fields(auth_widget)
    qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)


class TestConnectionVerifiedSignal:
    # AV-1: emitted after successful test
    def test_emitted_after_successful_test(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        received: list[object] = []
        auth_widget.connection_verified.connect(received.append)
        _do_successful_test(qtbot, auth_widget, mock_svc)
        assert len(received) == 1

    # AV-2: payload is ExportConfig
    def test_payload_is_export_config(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        received: list[object] = []
        auth_widget.connection_verified.connect(received.append)
        _do_successful_test(qtbot, auth_widget, mock_svc)
        assert isinstance(received[0], ExportConfig)

    # AV-3: NOT emitted after failed test
    def test_not_emitted_after_failed_test(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        received: list[object] = []
        auth_widget.connection_verified.connect(received.append)
        mock_svc.test_connection.side_effect = AuthenticationError("bad token")
        _fill_sa_fields(auth_widget)
        qtbot.mouseClick(auth_widget.test_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: auth_widget.test_btn.isEnabled(), timeout=3000)
        assert received == []

    # AV-4: connection_invalidated emitted when field changes after verify
    def test_invalidated_emitted_on_field_change_after_verify(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        invalidated: list[None] = []
        auth_widget.connection_invalidated.connect(lambda: invalidated.append(None))
        _do_successful_test(qtbot, auth_widget, mock_svc)
        auth_widget.sa_panel.cloud_id_field.setText("different-cloud-id")
        assert len(invalidated) == 1

    # AV-5: connection_invalidated NOT emitted when field changes before verify
    def test_invalidated_not_emitted_before_verify(
        self, qtbot, auth_widget: AuthWidget
    ) -> None:
        invalidated: list[None] = []
        auth_widget.connection_invalidated.connect(lambda: invalidated.append(None))
        auth_widget.sa_panel.cloud_id_field.setText("some-cloud-id")
        assert invalidated == []

    # AV-6: connection_invalidated emitted exactly once for two changes after verify
    def test_invalidated_emitted_only_once_for_multiple_changes(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        invalidated: list[None] = []
        auth_widget.connection_invalidated.connect(lambda: invalidated.append(None))
        _do_successful_test(qtbot, auth_widget, mock_svc)
        auth_widget.sa_panel.cloud_id_field.setText("change-1")
        auth_widget.sa_panel.cloud_id_field.setText("change-2")
        assert len(invalidated) == 1

    # AV-7: mode change after verify emits connection_invalidated
    def test_invalidated_emitted_on_mode_change_after_verify(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        invalidated: list[None] = []
        auth_widget.connection_invalidated.connect(lambda: invalidated.append(None))
        _do_successful_test(qtbot, auth_widget, mock_svc)
        qtbot.mouseClick(auth_widget.user_radio, Qt.MouseButton.LeftButton)
        assert len(invalidated) == 1

    # AV-8: _verified is False after connection_invalidated
    def test_verified_flag_reset_after_invalidation(
        self, qtbot, auth_widget: AuthWidget, mock_svc: MagicMock
    ) -> None:
        _do_successful_test(qtbot, auth_widget, mock_svc)
        assert auth_widget._verified is True
        auth_widget.sa_panel.cloud_id_field.setText("something-different")
        assert auth_widget._verified is False
