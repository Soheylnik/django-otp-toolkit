import pytest

from django_otp_toolkit.generators import generate_otp


def test_generate_otp_default_length():
    otp = generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()


@pytest.mark.parametrize("length", [4, 5, 6, 8, 10])
def test_generate_otp_custom_length(length):
    otp = generate_otp(length)

    assert len(otp) == length
    assert otp.isdigit()


@pytest.mark.parametrize("length", [3, 11, 0, -1])
def test_generate_otp_invalid_length(length):
    with pytest.raises(ValueError):
        generate_otp(length)


@pytest.mark.parametrize("length", [True, False, "6", 6.5, None])
def test_generate_otp_invalid_type(length):
    with pytest.raises(TypeError):
        generate_otp(length)


def test_generate_otp_preserves_leading_zeros():
    # The generator must return a string, not an integer.
    otp = generate_otp(6)

    assert isinstance(otp, str)
