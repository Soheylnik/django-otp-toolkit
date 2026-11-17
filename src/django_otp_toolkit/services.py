
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from django_otp_toolkit.backends.base import BaseSMSBackend
from django_otp_toolkit.exceptions import (
    ExpiredOTPError,
    InvalidOTPError,
    OTPAlreadyUsedError,
    OTPDeliveryError,
    OTPMaxAttemptsExceededError,
    OTPNotFoundError,
)
from django_otp_toolkit.generators import generate_otp
from django_otp_toolkit.models import OTP
from django_otp_toolkit.validators import normalize_phone_number


def _get_sms_backend():
    """
    Load and initialize the configured SMS backend.
    """

    backend_path = getattr(settings, "OTP_SMS_BACKEND", None)

    if not backend_path:
        raise OTPDeliveryError(
            "OTP SMS backend is not configured."
        )

    try:
        backend_class = import_string(backend_path)
        backend = backend_class()

    except Exception as exc:
        raise OTPDeliveryError(
            "Could not initialize the OTP SMS backend."
        ) from exc

    if not isinstance(backend, BaseSMSBackend):
        raise OTPDeliveryError(
            "Configured backend must inherit from BaseSMSBackend."
        )

    return backend


def request_otp(
    destination: str,
    purpose: str = OTP.Purpose.VERIFICATION,
    backend: BaseSMSBackend | None = None,
) -> OTP:
    """
    Generate, store, and send a new OTP.

    Previous OTPs for the same destination and purpose
    are invalidated before the new OTP is created.

    Returns:
        The created OTP database instance.

    Raises:
        OTPDeliveryError: If SMS delivery fails.
    """

    destination = normalize_phone_number(destination)

    otp_length = getattr(settings, "OTP_LENGTH", 6)
    expiry_seconds = getattr(settings, "OTP_EXPIRY_SECONDS", 300)

    if expiry_seconds <= 0:
        raise ValueError("OTP_EXPIRY_SECONDS must be greater than zero.")

    # Initialize backend before creating the OTP.
    if backend is None:
        backend = _get_sms_backend()

    # Generate a new OTP.
    code = generate_otp(length=otp_length)
    code_hash = make_password(code)

    now = timezone.now()

    # Invalidate previous OTPs and create a new one.
    with transaction.atomic():
        OTP.objects.filter(
            destination=destination,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)

        otp = OTP.objects.create(
            destination=destination,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=now + timedelta(seconds=expiry_seconds),
        )

    # The SMS backend receives the generated code.
    # Melipayamak uses this value as the {0} template argument.
    try:
        result = backend.send(
            to=destination,
            message=code,
        )

        if result is not True:
            raise OTPDeliveryError(
                "SMS backend did not confirm successful delivery."
            )

    except Exception as exc:
        # Invalidate the OTP if delivery fails.
        OTP.objects.filter(pk=otp.pk).update(is_used=True)

        if isinstance(exc, OTPDeliveryError):
            raise

        raise OTPDeliveryError(
            "Failed to deliver OTP."
        ) from exc

    return otp


def verify_otp(
    destination: str,
    code: str,
    purpose: str = OTP.Purpose.VERIFICATION,
) -> OTP:
    """
    Verify the latest OTP for a destination and purpose.

    The OTP is marked as used after successful verification.
    Failed attempts are persisted even when verification fails.
    """

    destination = normalize_phone_number(destination)

    max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 5)

    if max_attempts <= 0:
        raise ValueError("OTP_MAX_ATTEMPTS must be greater than zero.")

    error = None
    verified_otp = None

    with transaction.atomic():
        otp = (
            OTP.objects.select_for_update()
            .filter(
                destination=destination,
                purpose=purpose,
            )
            .order_by("-created_at", "-id")
            .first()
        )

        if otp is None:
            error = OTPNotFoundError("No OTP found.")

        elif otp.is_used:
            error = OTPAlreadyUsedError(
                "This OTP has already been used or invalidated."
            )

        elif otp.expires_at <= timezone.now():
            otp.is_used = True
            otp.save(update_fields=["is_used"])

            error = ExpiredOTPError("This OTP has expired.")

        elif otp.attempts >= max_attempts:
            otp.is_used = True
            otp.save(update_fields=["is_used"])

            error = OTPMaxAttemptsExceededError(
                "Maximum OTP verification attempts exceeded."
            )

        elif not isinstance(code, str) or not check_password(
            code,
            otp.code_hash,
        ):
            otp.attempts += 1

            if otp.attempts >= max_attempts:
                otp.is_used = True

            otp.save(update_fields=["attempts", "is_used"])

            if otp.is_used:
                error = OTPMaxAttemptsExceededError(
                    "Maximum OTP verification attempts exceeded."
                )
            else:
                error = InvalidOTPError("Invalid OTP code.")

        else:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            verified_otp = otp

    # Raise errors after the transaction commits.
    if error is not None:
        raise error

    return verified_otp
