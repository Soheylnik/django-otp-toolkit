class OTPError(Exception):
    """Base exception for all OTP-related errors."""


class InvalidOTPError(OTPError):
    """Raised when the provided OTP code is invalid."""


class ExpiredOTPError(OTPError):
    """Raised when the OTP code has expired."""


class OTPAlreadyUsedError(OTPError):
    """Raised when an OTP code has already been used."""


class OTPMaxAttemptsExceededError(OTPError):
    """Raised when the maximum verification attempts are exceeded."""


class OTPNotFoundError(OTPError):
    """Raised when no valid OTP record is found."""


class OTPDeliveryError(OTPError):
    """Raised when sending the OTP message fails."""


class OTPRateLimitError(OTPError):
    """Raised when the OTP request rate limit is exceeded."""
