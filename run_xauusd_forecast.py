#!/usr/bin/env python3
"""XAUUSD Farseer — daily high/low volatility forecast + email delivery.

Creates a .txt report and emails it via SMTP.
- Timezone: Europe/Berlin
- Trading days: Mon–Fri
- Threshold: $70 close-to-close move

This initial version is a deterministic skeleton that can be extended
with real research/data sources.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo


BERLIN = ZoneInfo("Europe/Berlin")


@dataclass(frozen=True)
class Config:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    mail_to: str


def load_config() -> Config:
    missing = []
    def get(name: str) -> str:
        v = os.environ.get(name, "").strip()
        if not v:
            missing.append(name)
        return v

    cfg = Config(
        smtp_host=get("SMTP_HOST"),
        smtp_port=int(get("SMTP_PORT") or 0),
        smtp_user=get("SMTP_USER"),
        smtp_pass=get("SMTP_PASS"),
        mail_to=get("MAIL_TO"),
    )

    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
    if cfg.smtp_port <= 0:
        raise SystemExit("SMTP_PORT must be a positive integer")
    return cfg


def is_trading_day_berlin(dt_berlin: datetime) -> bool:
    # Simple definition requested: Monday–Friday.
    return dt_berlin.weekday() < 5


def should_run_now(dt_berlin: datetime) -> bool:
    # We’ll schedule a UTC window and only run when it’s 20:00 in Berlin.
    # Manual test runs can override this with FORCE_SEND=true.
    force = os.environ.get("FORCE_SEND", "").strip().lower() in {"1", "true", "yes", "y"}
    return force or (dt_berlin.hour == 20)


def build_report(dt_berlin: datetime) -> tuple[str, str]:
    """Return (filename, file_content)."""
    analysis_date = dt_berlin.date().isoformat()

    # Placeholder forecast logic (to be replaced with real research model).
    predicted_move_usd = 0.0
    high_trading_day = abs(predicted_move_usd) >= 70.0

    content = (
        f"date={analysis_date}\n"
        f"predicted_price_movement_usd={predicted_move_usd:.2f}\n"
        f"high_trading_day={str(high_trading_day).lower()}\n"
    )

    filename = f"XAUUSD_{analysis_date}.txt"
    return filename, content


def send_email(cfg: Config, subject: str, body: str, attachment_name: str, attachment_text: str) -> None:
    msg = EmailMessage()
    msg["From"] = cfg.smtp_user
    msg["To"] = cfg.mail_to
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        attachment_text.encode("utf-8"),
        maintype="text",
        subtype="plain",
        filename=attachment_name,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=60) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(cfg.smtp_user, cfg.smtp_pass)
        server.send_message(msg)


def main() -> None:
    cfg = load_config()

    now_berlin = datetime.now(tz=BERLIN)

    if not is_trading_day_berlin(now_berlin):
        print("Not a trading day (Mon–Fri). Exiting.")
        return

    if not should_run_now(now_berlin):
        print(f"Not 20:00 in Europe/Berlin (now {now_berlin.isoformat()}). Exiting.")
        return

    attachment_name, attachment_text = build_report(now_berlin)

    subject = f"XAUUSD forecast — {now_berlin.date().isoformat()}"
    body = "Attached is the daily XAUUSD high/low trading day forecast (.txt)."

    send_email(cfg, subject, body, attachment_name, attachment_text)
    print("Email sent.")


if __name__ == "__main__":
    main()
