#!/usr/bin/env python3
"""XAUUSD Farseer — email sender.

Reads the latest forecast .txt file from the forecasts/ directory
and emails it as an attachment.

This script is triggered by GitHub Actions when a new forecast file
is pushed to the repo (by the Langdock scheduled task via GitHub integration).
"""

from __future__ import annotations

import glob
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage


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


def find_latest_forecast() -> tuple[str, str]:
    """Find the most recent XAUUSD_*.txt file in forecasts/ directory.

    Returns (filename, file_content).
    """
    pattern = os.path.join("forecasts", "XAUUSD_*.txt")
    files = sorted(glob.glob(pattern))

    if not files:
        raise SystemExit("No forecast files found in forecasts/ directory.")

    latest = files[-1]
    filename = os.path.basename(latest)

    with open(latest, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Found forecast file: {latest}")
    return filename, content


def extract_date_from_filename(filename: str) -> str:
    """Extract date from XAUUSD_YYYY-MM-DD.txt format."""
    # Remove prefix and suffix
    name = filename.replace("XAUUSD_", "").replace(".txt", "")
    return name


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

    filename, content = find_latest_forecast()
    forecast_date = extract_date_from_filename(filename)

    subject = f"XAUUSD forecast — {forecast_date}"
    body = (
        f"Attached is the XAUUSD high/low trading day forecast for {forecast_date}.\n\n"
        f"--- Preview ---\n{content}"
    )

    send_email(cfg, subject, body, filename, content)
    print(f"Email sent to {cfg.mail_to} for forecast date {forecast_date}.")


if __name__ == "__main__":
    main()
