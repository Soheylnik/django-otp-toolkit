import pytest

from django_otp_toolkit.validators import normalize_phone_number


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("09123456789", "09123456789"),
        ("+989123456789", "09123456789"),
        ("989123456789", "09123456789"),
        ("0912 345 6789", "09123456789"),
        ("0912-345-6789", "09123456789"),
        ("(0912)3456789", "09123456789"),
    ],
)
def test_normalize_valid_iranian_phone(phone, expected):
    assert normalize_phone_number(phone) == expected


@pytest.mark.parametrize(
    "phone",
    [
        "123456",
        "08123456789",
        "0912345678",
        "091234567890",
        "+123456789012",
        "",
    ],
)
def test_normalize_invalid_iranian_phone(phone):
    with pytest.raises(ValueError):
        normalize_phone_number(phone)


@pytest.mark.parametrize("phone", [123456789, None, True])
def test_normalize_phone_invalid_type(phone):
    with pytest.raises(TypeError):
        normalize_phone_number(phone)
