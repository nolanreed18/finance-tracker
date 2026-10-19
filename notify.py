"""Send the morning ping and, on Mondays, the weekly email.

    python notify.py            # what today calls for: the ping, plus the email on Mondays
    python notify.py ping       # just the ping
    python notify.py email      # just the email, whatever the day
    python notify.py preview    # print both to the terminal, send nothing

Runs daily in GitHub Actions (.github/workflows/notify.yml) after the bank
sync. The ping goes to your phone through ntfy.sh (the NTFY_TOPIC secret is
the channel: anyone who knows it can read it, so it's long and random). The
email goes through Gmail's SMTP server with an app password (GMAIL_ADDRESS,
GMAIL_APP_PASSWORD), to the same address unless NOTIFY_TO says otherwise.
Each is sent at most once a day: the settings table remembers the date.
Both messages are built by code (app/digest.py); nothing here prints a
secret.
"""

import os
import smtplib
import sys
import urllib.request
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))

import config  # noqa: E402
import data  # noqa: E402
import digest  # noqa: E402
import logic  # noqa: E402

NTFY_URL = "https://ntfy.sh"
PING_SENT, EMAIL_SENT = "ping_sent_on", "email_sent_on"


def app_url() -> str:
    return os.environ.get("APP_URL") or config.APP_URL


# ---- building --------------------------------------------------------------

def build_ping(today) -> digest.Ping | None:
    return digest.daily_ping(data.bills(active_only=True), data.connections(), today,
                             url=app_url())


def build_email(today) -> tuple[str, str, str]:
    since = min(logic.month_start(today), today - timedelta(days=7))
    facts = digest.week_facts(data.transactions(since=since), data.budgets(logic.month_start(today)),
                              data.bills(active_only=True), data.accounts(), data.balances(),
                              data.connections(), today)
    return digest.weekly_email(facts, url=app_url())


# ---- sending ---------------------------------------------------------------

def send_ping(ping: digest.Ping) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        raise RuntimeError("NTFY_TOPIC is not set")
    request = urllib.request.Request(
        f"{NTFY_URL}/{topic}", data=ping.body.encode("utf-8"), method="POST",
        headers={"Title": ping.title, "Click": ping.url, "Tags": "moneybag",
                 "Priority": "high" if ping.urgent else "default"})
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def send_email(subject: str, html: str, text: str) -> None:
    sender = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not sender or not password:
        raise RuntimeError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD are not both set")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"Finance Tracker <{sender}>"
    message["To"] = os.environ.get("NOTIFY_TO") or sender
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
        server.login(sender, password)
        server.send_message(message)


# ---- the run ---------------------------------------------------------------

def run_ping(today) -> str:
    if data.get_setting(PING_SENT) == today.isoformat():
        return "ping already sent today"
    ping = build_ping(today)
    if ping is None:
        return "nothing to ping about"
    send_ping(ping)
    data.set_setting(PING_SENT, today.isoformat())
    return f"pinged: {ping.title} ({len(ping.lines)} lines)"


def run_email(today) -> str:
    if data.get_setting(EMAIL_SENT) == today.isoformat():
        return "email already sent today"
    subject, html, text = build_email(today)
    send_email(subject, html, text)
    data.set_setting(EMAIL_SENT, today.isoformat())
    return f"emailed: {subject}"


def main(argv: list[str] | None = None) -> int:
    mode = (argv if argv is not None else sys.argv[1:])[:1] or ["auto"]
    today = data.today()
    try:
        if mode[0] == "preview":
            ping = build_ping(today)
            print("PING:", "nothing to say" if ping is None else f"{ping.title}\n{ping.body}")
            subject, _, text = build_email(today)
            print(f"\nEMAIL: {subject}\n{text}")
            return 0
        if mode[0] in ("auto", "ping"):
            print(run_ping(today))
        if mode[0] == "email" or (mode[0] == "auto" and today.weekday() == config.SUMMARY_WEEKDAY):
            print(run_email(today))
    except (RuntimeError, OSError, smtplib.SMTPException) as exc:
        print(f"notify failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
