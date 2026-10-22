"""Server-side SMTP delivery helpers shared by the public and admin services."""

import re
import smtplib
from email.message import EmailMessage


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class MailDeliveryError(RuntimeError):
    """Raised when a configured email provider cannot accept a message."""


def is_valid_email(address):
    """Validate a normal mailbox address and reject header-injection input."""
    return bool(address and EMAIL_PATTERN.fullmatch(address) and "\r" not in address and "\n" not in address)


def _safe_header(value, field_name):
    value = (value or "").strip()
    if not value or "\r" in value or "\n" in value:
        raise ValueError(f"Invalid {field_name}.")
    return value


def _sender(config):
    address = _safe_header(config.get("SMTP_FROM_EMAIL"), "sender address")
    if not is_valid_email(address):
        raise ValueError("Invalid sender address.")
    name = (config.get("SMTP_FROM_NAME") or "WHAT NEXT? Team").strip()
    if "\r" in name or "\n" in name:
        raise ValueError("Invalid sender name.")
    return address, name


def smtp_is_configured(config):
    """Return true only when all credentials needed for delivery are present."""
    return all(config.get(key) for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_FROM_EMAIL"))


def send_email(config, recipient, subject, body):
    """Submit a text email to SMTP without logging message content or credentials."""
    recipient = _safe_header(recipient, "recipient address")
    subject = _safe_header(subject, "email subject")
    if not is_valid_email(recipient):
        raise ValueError("Invalid recipient address.")
    if not smtp_is_configured(config):
        raise MailDeliveryError("Email delivery is not configured.")

    sender_address, sender_name = _sender(config)
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = f"{sender_name} <{sender_address}>"
    message["Subject"] = subject
    message.set_content(body)

    timeout = int(config.get("SMTP_TIMEOUT_SECONDS", 10))
    use_ssl = bool(config.get("SMTP_USE_SSL"))
    use_tls = bool(config.get("SMTP_USE_TLS", True)) and not use_ssl
    try:
        client_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with client_class(config["SMTP_HOST"], int(config["SMTP_PORT"]), timeout=timeout) as client:
            if use_tls:
                client.starttls()
            if config.get("SMTP_USER"):
                client.login(config["SMTP_USER"], config.get("SMTP_PASS") or "")
            client.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as error:
        raise MailDeliveryError("The email provider did not accept the message.") from error
