
from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.utils import timezone

from django_otp_toolkit.exceptions import (
    ExpiredOTPError,
    InvalidOTPError,
    OTPAlreadyUsedError,
    OTPDeliveryError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from django_otp_toolkit.models import OTP
from django_otp_toolkit.services import request_otp, verify_otp


pytestmark = pytest.mark.django_db


class DummySMSBackend:
    def __init__(self, result=True, exception=None):
        self.result = result
        self.exception = exception
        self.last_message = None
        self.last_destination = None

    def send(self, to, message):
        self.last_destination = to
        self.last_message = message

        if self.exception:
            raise self.exception

        return self.result


def test_request_otp_creates_record():
    backend = DummySMSBackend()

    otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    assert OTP.objects.count() == 1
    assert otp.destination == "09123456789"
    assert otp.is_used is False
    assert backend.last_destination == "09123456789"
    assert len(backend.last_message) == 6
    assert backend.last_message.isdigit()


def test_otp_code_is_not_stored_as_plain_text():
    backend = DummySMSBackend()

    otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    assert otp.code_hash != backend.last_message
    assert otp.code_hash.startswith("pbkdf2_sha256$")


def test_new_otp_invalidates_previous_otp():
    backend = DummySMSBackend()

    first_otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    second_otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    first_otp.refresh_from_db()

    assert first_otp.is_used is True
    assert second_otp.is_used is False


def test_different_purposes_do_not_invalidate_each_other():
    backend = DummySMSBackend()

    login_otp = request_otp(
        destination="09123456789",
        purpose=OTP.Purpose.LOGIN,
        backend=backend,
    )

    registration_otp = request_otp(
        destination="09123456789",
        purpose=OTP.Purpose.REGISTRATION,
        backend=backend,
    )

    login_otp.refresh_from_db()

    assert login_otp.is_used is False
    assert registration_otp.is_used is False


def test_delivery_failure_invalidates_otp():
    backend = DummySMSBackend(
        exception=OTPDeliveryError("SMS failed")
    )

    with pytest.raises(OTPDeliveryError):
        request_otp(
            destination="09123456789",
            backend=backend,
        )

    otp = OTP.objects.get()

    assert otp.is_used is True


def test_false_delivery_result_invalidates_otp():
    backend = DummySMSBackend(result=False)

    with pytest.raises(OTPDeliveryError):
        request_otp(
            destination="09123456789",
            backend=backend,
        )

    otp = OTP.objects.get()

    assert otp.is_used is True


def test_verify_otp_success():
    backend = DummySMSBackend()

    request_otp(
        destination="09123456789",
        backend=backend,
    )

    otp = verify_otp(
        destination="09123456789",
        code=backend.last_message,
    )

    assert otp.is_used is True


def test_verify_otp_rejects_invalid_code():
    backend = DummySMSBackend()

    request_otp(
        destination="09123456789",
        backend=backend,
    )

    with pytest.raises(InvalidOTPError):
        verify_otp(
            destination="09123456789",
            code="000000",
        )

    otp = OTP.objects.get()

    assert otp.attempts == 1
    assert otp.is_used is False


def test_verify_otp_persists_max_attempts():
    backend = DummySMSBackend()

    request_otp(
        destination="09123456789",
        backend=backend,
    )

    for _ in range(4):
        with pytest.raises(InvalidOTPError):
            verify_otp(
                destination="09123456789",
                code="000000",
            )

    with pytest.raises(OTPMaxAttemptsExceededError):
        verify_otp(
            destination="09123456789",
            code="000000",
        )

    otp = OTP.objects.get()

    assert otp.attempts == 5
    assert otp.is_used is True


def test_verify_otp_rejects_reused_code():
    backend = DummySMSBackend()

    request_otp(
        destination="09123456789",
        backend=backend,
    )

    verify_otp(
        destination="09123456789",
        code=backend.last_message,
    )

    with pytest.raises(OTPAlreadyUsedError):
        verify_otp(
            destination="09123456789",
            code=backend.last_message,
        )


def test_verify_otp_rejects_expired_code():
    backend = DummySMSBackend()

    otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    otp.expires_at = timezone.now() - timedelta(seconds=1)
    otp.save(update_fields=["expires_at"])

    with pytest.raises(ExpiredOTPError):
        verify_otp(
            destination="09123456789",
            code=backend.last_message,
        )

    otp.refresh_from_db()

    assert otp.is_used is True


def test_verify_otp_when_no_record_exists():
    with pytest.raises(OTPNotFoundError):
        verify_otp(
            destination="09123456789",
            code="123456",
        )



def test_old_code_cannot_be_used_after_new_request():
    backend = DummySMSBackend()

    first_otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    first_code = backend.last_message

    second_otp = request_otp(
        destination="09123456789",
        backend=backend,
    )

    with pytest.raises(InvalidOTPError):
        verify_otp(
            destination="09123456789",
            code=first_code,
        )

    first_otp.refresh_from_db()
    second_otp.refresh_from_db()

    assert first_otp.is_used is True
    assert second_otp.is_used is False
    assert second_otp.attempts == 1
