from __future__ import annotations

from app.core.email_provider import EmailMessage, EmailProviderUnavailable, EmailTransport

VERIFY_SUBJECT = "Verify your SENTINEL email"
RESET_SUBJECT = "Reset your SENTINEL password"


def send_verification_email(transport: EmailTransport, email: str, token: str) -> bool:
    message = EmailMessage(
        to_address=email,
        subject=VERIFY_SUBJECT,
        text=(
            "SENTINEL email verification\n\n"
            f"Verification code: {token}\n\n"
            "This one-time code expires in 24 hours. "
            "If you did not request this account, ignore this message."
        ),
    )
    try:
        transport.send(message)
        return True
    except EmailProviderUnavailable:
        return False


def send_password_reset_email(transport: EmailTransport, email: str, token: str) -> bool:
    message = EmailMessage(
        to_address=email,
        subject=RESET_SUBJECT,
        text=(
            "SENTINEL password reset\n\n"
            f"Reset code: {token}\n\n"
            "This one-time code expires in 30 minutes. "
            "Using it revokes existing account sessions. "
            "If you did not request a reset, ignore this message."
        ),
    )
    try:
        transport.send(message)
        return True
    except EmailProviderUnavailable:
        return False
