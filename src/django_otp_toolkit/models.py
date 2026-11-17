from django.db import models


class OTP(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        REGISTRATION = "registration", "Registration"
        PASSWORD_RESET = "password_reset", "Password Reset"
        VERIFICATION = "verification", "Verification"

    destination = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Phone number receiving the OTP.",
    )

    purpose = models.CharField(
        max_length=30,
        choices=Purpose.choices,
        default=Purpose.VERIFICATION,
        db_index=True,
    )

    code_hash = models.CharField(max_length=128)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(db_index=True)

    is_used = models.BooleanField(default=False, db_index=True)

    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["destination", "purpose", "is_used"],
                name="otp_dest_purpose_used_idx",
            ),
        ]

    def __str__(self):
        return f"OTP for {self.destination} ({self.purpose})"
