
import pytest
from unittest.mock import Mock, patch

from django.test import override_settings

from django_otp_toolkit.backends.base import BaseSMSBackend
from django_otp_toolkit.backends.melipayamak import MelipayamakBackend
from django_otp_toolkit.exceptions import OTPDeliveryError


def test_base_backend_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseSMSBackend()


def test_custom_backend_can_be_instantiated():
    class DummySMSBackend(BaseSMSBackend):
        def send(self, to: str, message: str) -> bool:
            return True

    backend = DummySMSBackend()

    assert backend.send("09123456789", "123456") is True


def test_backend_failure_raises_otp_delivery_error():
    class FailedSMSBackend(BaseSMSBackend):
        def send(self, to: str, message: str) -> bool:
            raise OTPDeliveryError("SMS delivery failed.")

    backend = FailedSMSBackend()

    with pytest.raises(OTPDeliveryError):
        backend.send("09123456789", "123456")


@override_settings(
    MELIPAYAMAK_API_KEY="test-api-key",
    MELIPAYAMAK_BODY_ID=582256,
    MELIPAYAMAK_TIMEOUT=10,
)
@patch("django_otp_toolkit.backends.melipayamak.requests.post")
def test_melipayamak_send_success(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "recId": "123456789",
        "status": "",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    backend = MelipayamakBackend()

    result = backend.send(
        "09123456789",
        "123456",
    )

    assert result is True

    mock_post.assert_called_once_with(
        "https://console.melipayamak.com/api/send/shared/test-api-key",
        json={
            "to": "09123456789",
            "bodyId": 582256,
            "args": ["123456"],
        },
        timeout=10,
    )


@override_settings(
    MELIPAYAMAK_API_KEY="test-api-key",
    MELIPAYAMAK_BODY_ID=582256,
)
@patch("django_otp_toolkit.backends.melipayamak.requests.post")
def test_melipayamak_api_error(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "Invalid body ID",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    backend = MelipayamakBackend()

    with pytest.raises(OTPDeliveryError, match="Invalid body ID"):
        backend.send("09123456789", "123456")


@override_settings(
    MELIPAYAMAK_API_KEY="test-api-key",
    MELIPAYAMAK_BODY_ID=582256,
)
@patch("django_otp_toolkit.backends.melipayamak.requests.post")
def test_melipayamak_network_error(mock_post):
    import requests

    mock_post.side_effect = requests.Timeout("Connection timed out")

    backend = MelipayamakBackend()

    with pytest.raises(
        OTPDeliveryError,
        match="Failed to communicate",
    ):
        backend.send("09123456789", "123456")


@override_settings(
    MELIPAYAMAK_API_KEY="test-api-key",
    MELIPAYAMAK_BODY_ID=582256,
)
@patch("django_otp_toolkit.backends.melipayamak.requests.post")
def test_melipayamak_invalid_json(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_post.return_value = mock_response

    backend = MelipayamakBackend()

    with pytest.raises(
        OTPDeliveryError,
        match="invalid response",
    ):
        backend.send("09123456789", "123456")


@override_settings(
    MELIPAYAMAK_API_KEY="test-api-key",
    MELIPAYAMAK_BODY_ID=582256,
)
@patch("django_otp_toolkit.backends.melipayamak.requests.post")
def test_melipayamak_missing_rec_id(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    backend = MelipayamakBackend()

    with pytest.raises(
        OTPDeliveryError,
        match="did not return a message ID",
    ):
        backend.send("09123456789", "123456")


def test_melipayamak_missing_api_key():
    with override_settings(
        MELIPAYAMAK_API_KEY="",
        MELIPAYAMAK_BODY_ID=582256,
    ):
        with pytest.raises(
            OTPDeliveryError,
            match="API key is not configured",
        ):
            MelipayamakBackend()


def test_melipayamak_missing_body_id():
    with override_settings(
        MELIPAYAMAK_API_KEY="test-api-key",
        MELIPAYAMAK_BODY_ID=None,
    ):
        with pytest.raises(
            OTPDeliveryError,
            match="body ID is not configured",
        ):
            MelipayamakBackend()
