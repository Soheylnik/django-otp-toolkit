
import secrets


DEFAULT_OTP_LENGTH = 6


def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
    """
    Generate a cryptographically secure numeric OTP.

    Args:
        length: Number of digits in the OTP.

    Returns:
        A numeric OTP as a string.
    """
    if not isinstance(length, int) or isinstance(length, bool):
        raise TypeError("OTP length must be an integer.")

    if length < 4 or length > 10:
        raise ValueError("OTP length must be between 4 and 10.")

    return "".join(
        secrets.choice("0123456789")
        for _ in range(length)
    )
