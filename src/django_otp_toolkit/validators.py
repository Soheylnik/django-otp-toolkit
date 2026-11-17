import re


IRAN_PHONE_PATTERN = re.compile(r"^09\d{9}$")


def normalize_phone_number(phone: str) -> str:
    """
    Normalize an Iranian mobile number.

    Supported examples:
        09123456789
        +989123456789
        989123456789
    """
    if not isinstance(phone, str):
        raise TypeError("Phone number must be a string.")

    phone = re.sub(r"[\s\-()]", "", phone)

    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98"):
        phone = "0" + phone[2:]

    if not IRAN_PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Invalid Iranian mobile number.")

    return phone
