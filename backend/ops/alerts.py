from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from backend.core.config import settings
from backend.core.retry import retry_sync


def _send_telegram(message: str) -> bool:
    if not settings.alerts_telegram_bot_token or not settings.alerts_telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.alerts_telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.alerts_telegram_chat_id, "text": message}
    response = retry_sync(lambda: httpx.post(url, json=payload, timeout=10.0))
    response.raise_for_status()
    return True


def _send_discord(message: str) -> bool:
    if not settings.alerts_discord_webhook_url:
        return False
    response = retry_sync(
        lambda: httpx.post(
            settings.alerts_discord_webhook_url,
            json={"content": message},
            timeout=10.0,
        )
    )
    response.raise_for_status()
    return True


def _send_email(subject: str, body: str) -> bool:
    if not (settings.alerts_email_smtp_host and settings.alerts_email_to and settings.alerts_email_from):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.alerts_email_from
    msg["To"] = settings.alerts_email_to
    msg.set_content(body)
    with smtplib.SMTP(settings.alerts_email_smtp_host, settings.alerts_email_smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.alerts_email_username:
            smtp.login(settings.alerts_email_username, settings.alerts_email_password)
        smtp.send_message(msg)
    return True


def notify_event(event_type: str, title: str, details: dict) -> dict:
    message = f"[{event_type}] {title}\n{details}"
    sent = {"telegram": False, "discord": False, "email": False}
    try:
        sent["telegram"] = _send_telegram(message)
    except Exception:
        sent["telegram"] = False
    try:
        sent["discord"] = _send_discord(message)
    except Exception:
        sent["discord"] = False
    try:
        sent["email"] = _send_email(f"CryptoSwarms {event_type}", message)
    except Exception:
        sent["email"] = False
    return sent
