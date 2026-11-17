from abc import ABC, abstractmethod

from django_otp_toolkit.exceptions import OTPDeliveryError


class BaseSMSBackend(ABC):
    """
    Base class for all SMS delivery backends.
    """

    @abstractmethod
    def send(self, to: str, message: str) -> bool:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number.
            message: Message content.

        Returns:
            True if the message was sent successfully.

        Raises:
            OTPDeliveryError: If message delivery fails.
        """
        raise NotImplementedError
