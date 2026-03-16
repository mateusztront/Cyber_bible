"""
Tests for login.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from instagrapi.exceptions import (
    LoginRequired,
    TwoFactorRequired,
    BadPassword,
    PleaseWaitFewMinutes,
)

from login import (
    login_user,
    logout,
    _configure_client,
    _login_via_session,
    _login_via_credentials,
)


class TestConfigureClient:
    """Tests for _configure_client function."""

    def test_sets_delay_range(self):
        client = MagicMock()
        _configure_client(client)

        client.set_locale.assert_called_once()
        client.set_country_code.assert_called_once()
        client.set_timezone_offset.assert_called_once()
        client.set_device.assert_called_once()
        client.set_user_agent.assert_called_once()

    def test_sets_device_info(self):
        client = MagicMock()
        _configure_client(client)

        device_call = client.set_device.call_args[0][0]
        assert "samsung" in device_call["manufacturer"]
        assert "SM-S926B" in device_call["model"]


class TestLoginViaSession:
    """Tests for _login_via_session function."""

    @patch("login.SESSION_FILE")
    def test_returns_false_when_no_session_file(self, mock_session_file):
        mock_session_file.exists.return_value = False
        client = MagicMock()

        result = _login_via_session(client, "user", "pass")

        assert result is False

    @patch("login.SESSION_FILE")
    def test_returns_true_on_successful_session_login(self, mock_session_file):
        mock_session_file.exists.return_value = True
        client = MagicMock()
        client.get_timeline_feed.return_value = {}

        result = _login_via_session(client, "user", "pass")

        assert result is True
        client.load_settings.assert_called_once()
        client.login.assert_called_once()

    @patch("login.SESSION_FILE")
    def test_returns_false_on_login_required(self, mock_session_file):
        mock_session_file.exists.return_value = True
        client = MagicMock()
        client.get_timeline_feed.side_effect = LoginRequired("Session expired")

        result = _login_via_session(client, "user", "pass")

        assert result is False


class TestLoginViaCredentials:
    """Tests for _login_via_credentials function."""

    @patch("login.SESSION_FILE")
    def test_returns_true_on_success(self, mock_session_file):
        client = MagicMock()

        result = _login_via_credentials(client, "user", "pass")

        assert result is True
        client.login.assert_called_once_with("user", "pass")
        client.dump_settings.assert_called_once()

    @patch("login.SESSION_FILE")
    def test_returns_false_on_bad_password(self, mock_session_file):
        client = MagicMock()
        client.login.side_effect = BadPassword("Wrong password")

        result = _login_via_credentials(client, "user", "wrongpass")

        assert result is False

    @patch("login.SESSION_FILE")
    def test_returns_false_on_rate_limit(self, mock_session_file):
        client = MagicMock()
        client.login.side_effect = PleaseWaitFewMinutes("Too many requests")

        result = _login_via_credentials(client, "user", "pass")

        assert result is False

    @patch("login.SESSION_FILE")
    @patch("builtins.input", return_value="123456")
    def test_handles_two_factor_auth(self, mock_input, mock_session_file):
        client = MagicMock()
        client.login.side_effect = [
            TwoFactorRequired("2FA needed"),
            None,  # Success on second call
        ]

        result = _login_via_credentials(client, "user", "pass")

        assert result is True
        assert client.login.call_count == 2


class TestLoginUser:
    """Tests for login_user function."""

    def test_raises_error_without_credentials(self):
        with patch("login.INSTAGRAM_USERNAME", ""):
            with patch("login.INSTAGRAM_PASSWORD", ""):
                with pytest.raises(ValueError, match="credentials not provided"):
                    login_user()

    @patch("login._login_via_session")
    @patch("login._configure_client")
    @patch("login.Client")
    def test_uses_session_login_first(self, mock_client_class, mock_configure, mock_session):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_session.return_value = True

        result = login_user("user", "pass")

        mock_session.assert_called_once()
        assert result == mock_client

    @patch("login._login_via_credentials")
    @patch("login._login_via_session")
    @patch("login._configure_client")
    @patch("login.Client")
    def test_falls_back_to_credentials(
        self, mock_client_class, mock_configure, mock_session, mock_credentials
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_session.return_value = False
        mock_credentials.return_value = True

        result = login_user("user", "pass")

        mock_session.assert_called_once()
        mock_credentials.assert_called_once()
        assert result == mock_client

    @patch("login._login_via_credentials")
    @patch("login._login_via_session")
    @patch("login._configure_client")
    @patch("login.Client")
    def test_raises_on_all_failures(
        self, mock_client_class, mock_configure, mock_session, mock_credentials
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_session.return_value = False
        mock_credentials.return_value = False

        with pytest.raises(Exception, match="Failed to login"):
            login_user("user", "pass")


class TestLogout:
    """Tests for logout function."""

    @patch("login.SESSION_FILE")
    def test_calls_client_logout(self, mock_session_file):
        mock_session_file.exists.return_value = False
        client = MagicMock()

        logout(client)

        client.logout.assert_called_once()

    @patch("login.SESSION_FILE")
    def test_removes_session_file(self, mock_session_file):
        mock_session_file.exists.return_value = True
        client = MagicMock()

        logout(client)

        mock_session_file.unlink.assert_called_once()

    @patch("login.SESSION_FILE")
    def test_handles_logout_error(self, mock_session_file):
        mock_session_file.exists.return_value = False
        client = MagicMock()
        client.logout.side_effect = Exception("Logout failed")

        # Should not raise
        logout(client)
