import hashlib

from django.conf import settings
from django.core.cache import caches

from django_otp_toolkit.exceptions import OTPRateLimitError


def _make_cache_key(destination: str, purpose: str, suffix: str) -> str:
    """
    Create a cache key without exposing the phone number.
    """

    value = f"{destination}:{purpose}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()

    return f"django_otp_toolkit:{suffix}:{digest}"


def _increment_counter(cache, key: str, timeout: int) -> int:
    """
    Atomically increment a cache counter when supported by the backend.
    """

    if cache.add(key, 1, timeout=timeout):
        return 1

    try:
        return cache.incr(key)

    except ValueError:
        # The key may have expired between the add and increment calls.
        if cache.add(key, 1, timeout=timeout):
            return 1

        return cache.incr(key)


def enforce_otp_rate_limit(
    destination: str,
    purpose: str,
) -> None:
    """
    Enforce cooldown, hourly, and daily OTP request limits.

    Limits are applied separately to each destination and purpose.
    """

    if not getattr(settings, "OTP_RATE_LIMIT_ENABLED", True):
        return

    cooldown = getattr(settings, "OTP_RATE_LIMIT_COOLDOWN", 60)
    hourly_limit = getattr(settings, "OTP_RATE_LIMIT_HOURLY", 5)
    daily_limit = getattr(settings, "OTP_RATE_LIMIT_DAILY", 10)

    if cooldown < 0:
        raise ValueError("OTP_RATE_LIMIT_COOLDOWN cannot be negative.")

    if hourly_limit is not None and hourly_limit <= 0:
        raise ValueError("OTP_RATE_LIMIT_HOURLY must be positive or None.")

    if daily_limit is not None and daily_limit <= 0:
        raise ValueError("OTP_RATE_LIMIT_DAILY must be positive or None.")

    cache_alias = getattr(
        settings,
        "OTP_RATE_LIMIT_CACHE_ALIAS",
        "default",
    )

    cache = caches[cache_alias]

    cooldown_key = _make_cache_key(
        destination,
        purpose,
        "cooldown",
    )

    hourly_key = _make_cache_key(
        destination,
        purpose,
        "hourly",
    )

    daily_key = _make_cache_key(
        destination,
        purpose,
        "daily",
    )

    cooldown_created = False

    try:
        # Prevent repeated requests during the cooldown period.
        if cooldown > 0:
            cooldown_created = cache.add(
                cooldown_key,
                1,
                timeout=cooldown,
            )

            if not cooldown_created:
                raise OTPRateLimitError(
                    f"Please wait {cooldown} seconds before requesting another OTP."
                )

        # Check hourly request limit.
        if hourly_limit is not None:
            hourly_count = _increment_counter(
                cache,
                hourly_key,
                timeout=3600,
            )

            if hourly_count > hourly_limit:
                raise OTPRateLimitError(
                    "Hourly OTP request limit exceeded."
                )

        # Check daily request limit.
        if daily_limit is not None:
            daily_count = _increment_counter(
                cache,
                daily_key,
                timeout=86400,
            )

            if daily_count > daily_limit:
                raise OTPRateLimitError(
                    "Daily OTP request limit exceeded."
                )

    except OTPRateLimitError:
        if cooldown_created:
            cache.delete(cooldown_key)

        raise

    except Exception as exc:
        if cooldown_created:
            try:
                cache.delete(cooldown_key)
            except Exception:
                pass

        raise OTPRateLimitError(
            "Could not check OTP request limits."
        ) from exc
