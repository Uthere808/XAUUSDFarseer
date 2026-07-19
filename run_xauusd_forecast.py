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
from datetime import datetime, timedelta
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


def next_trading_day_berlin(dt_berlin: datetime) -> datetime:
    """Return a datetime (same tz) representing the next trading day date.

    Trading days are defined simply as Monday–Friday.
    """
    d = dt_berlin
    while True:
        d = d.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if d.weekday() < 5:
            return d


def should_run_today(dt_berlin: datetime) -> bool:
    """Whether we should produce a forecast now.

    Rule: run on any day (including Sunday) *if tomorrow is a trading day*.
    Manual test runs can override with FORCE_SEND=true.
    """
    force = os.environ.get("FORCE_SEND", "").strip().lower() in {"1", "true", "yes", "y"}
    if force:
        return True

    # Only run at 20:00 Berlin.
    if dt_berlin.hour != 20:
        return False

    # If the next calendar day that is Mon–Fri exists (it always does), then run.
    # Specifically: we want a report for the *next trading day*.
    nt = next_trading_day_berlin(dt_berlin)
    # If next trading day is tomorrow (or later after weekend), we still want to run daily at 20:00.
    # But if today is a trading day, this just forecasts tomorrow.
    # If today is Sunday, this forecasts Monday.
    return nt.date() != dt_berlin.date()


def should_run_now(dt_berlin: datetime) -> bool:
    # We’ll schedule a UTC window and only run when it’s 20:00 in Berlin.
    # Manual test runs can override this with FORCE_SEND=true.
    force = os.environ.get("FORCE_SEND", "").strip().lower() in {"1", "true", "yes", "y"}
    return force or (dt_berlin.hour == 20)


def build_report(dt_berlin: datetime) -> tuple[str, str]:
    """Return (filename, file_content).

    The report is for the *next trading day* (Mon–Fri).
    """
    target_day = next_trading_day_berlin(dt_berlin).date()
    analysis_date = target_day.isoformat()

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

    if not should_run_today(now_berlin):
        print(
            "Skip run. "
            f"now_berlin={now_berlin.isoformat()} "
            f"force_send={os.environ.get('FORCE_SEND','').strip()}"
        )
        return

    attachment_name, attachment_text = build_report(now_berlin)

    subject = f"XAUUSD forecast — {now_berlin.date().isoformat()}"
    body = "Attached is the daily XAUUSD high/low trading day forecast (.txt)."

    send_email(cfg, subject, body, attachment_name, attachment_text)
    print("Email sent.")


if __name__ == "__main__":
    main()
