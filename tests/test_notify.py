"""The morning ping and the Monday email: what they say (digest, pure) and
how notify.py sends them, with ntfy and Gmail faked."""

import smtplib
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

import config
import data
import digest
import notify

TODAY = date(2026, 10, 14)            # a Wednesday
MONDAY = date(2026, 10, 12)


def bills(*rows) -> pd.DataFrame:
    base = {"amount": Decimal("10"), "active": True, "autopay": False}
    return pd.DataFrame([{**base, **r} for r in rows],
                        columns=["name", "amount", "next_due_on", "active", "autopay"])


def connections(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=["institution_name", "last_error", "last_synced_on"])


# ---- the ping ---------------------------------------------------------------

def test_the_ping_lists_bills_due_soon_and_overdue_soonest_first():
    ping = digest.daily_ping(bills(
        {"name": "Phone", "amount": Decimal("45.50"), "next_due_on": date(2026, 10, 16),
         "autopay": True},
        {"name": "Rent", "amount": Decimal("1200"), "next_due_on": date(2026, 10, 12)},
        {"name": "Gym", "next_due_on": date(2026, 10, 15), "active": False},
        {"name": "Insurance", "next_due_on": date(2026, 10, 20)},             # beyond 3 days
    ), connections(), TODAY)
    assert ping.title == "2 bills to pay" and ping.urgent
    assert ping.lines == ["Rent $1,200.00 · 2 days overdue",
                          "Phone $45.50 · due Fri Oct 16 (autopay)"]
    assert ping.url.endswith("/Bills") and ping.body == "\n".join(ping.lines)


def test_the_ping_mentions_a_bank_to_sign_in_to_and_is_quiet_otherwise():
    ping = digest.daily_ping(bills(), connections(("Chase", "ITEM_LOGIN_REQUIRED: x", None)), TODAY)
    assert ping.title == "Finance Tracker" and ping.urgent
    assert ping.lines == ["Chase: sign in again to keep syncing"] and ping.url.endswith("/Accounts")
    assert digest.daily_ping(bills({"name": "Rent", "next_due_on": date(2026, 10, 20)}),
                             connections(("Amex", None, TODAY)), TODAY) is None
    calm = digest.daily_ping(bills({"name": "Rent", "next_due_on": TODAY}), connections(), TODAY)
    assert calm.title == "1 bill to pay" and not calm.urgent


# ---- the email --------------------------------------------------------------

def transactions(*rows) -> pd.DataFrame:
    base = {"kind": "expense", "category": "Food", "category_id": 1, "payee": "Grocer"}
    return pd.DataFrame([{**base, **r} for r in rows],
                        columns=["happened_on", "amount", "kind", "category", "category_id",
                                 "payee"])


FACTS_INPUT = dict(
    transactions=transactions(
        {"happened_on": date(2026, 10, 1), "amount": Decimal("2500"), "kind": "income",
         "category": "Pay", "category_id": 2},
        {"happened_on": date(2026, 10, 3), "amount": Decimal("-42.10")},
        {"happened_on": date(2026, 10, 12), "amount": Decimal("-9.99"), "category": None,
         "category_id": None, "payee": "Streaming"},
        {"happened_on": date(2026, 10, 13), "amount": Decimal("-60"), "category": "Fun",
         "category_id": 3},
    ),
    budgets=pd.DataFrame([{"name": "Food", "budgeted": Decimal("100"), "spent": Decimal("42.10")},
                          {"name": "Fun", "budgeted": Decimal("50"), "spent": Decimal("60")}]),
    bills=bills({"name": "Rent", "amount": Decimal("1200"), "next_due_on": date(2026, 10, 18)},
                {"name": "Insurance", "next_due_on": date(2026, 11, 20)}),
    accounts=pd.DataFrame([{"account_id": 1, "name": "Checking", "closed_on": None,
                            "is_liability": False, "balance": Decimal("1250"),
                            "balance_on": TODAY}]),
    balances=pd.DataFrame([{"account_id": 1, "as_of": date(2026, 9, 1), "amount": Decimal("1000"),
                            "is_liability": False, "closed_on": None},
                           {"account_id": 1, "as_of": TODAY, "amount": Decimal("1250"),
                            "is_liability": False, "closed_on": None}]),
    connections=connections(),
)


def test_week_facts_from_the_frames():
    facts = digest.week_facts(today=TODAY, **FACTS_INPUT)
    assert facts.net_worth == Decimal("1250.00") and facts.net_worth_change == Decimal("250.00")
    assert facts.spent_month == Decimal("112.09") and facts.budgeted_month == Decimal("150.00")
    assert facts.savings_rate == Decimal("0.9552")
    assert facts.spent_week == Decimal("69.99")
    assert facts.week_by_category.values.tolist() == [["Fun", Decimal("60.00")],
                                                      ["(uncategorised)", Decimal("9.99")]]
    assert [(a.kind, a.headline) for a in facts.attention] == [("due", "Rent"), ("over", "Fun")]
    assert facts.upcoming_bills["name"].tolist() == ["Rent"]
    assert facts.uncategorised == 1


def test_the_email_is_small_self_contained_and_says_the_numbers():
    facts = digest.week_facts(today=TODAY, **FACTS_INPUT)
    subject, html, text = digest.weekly_email(facts, url="https://app.example")
    assert subject == "Money this week · Oct 14"
    assert html.startswith("<!doctype html>") and "<script" not in html and "fonts.googleapis" not in html
    assert len(html.encode()) < 100_000
    for needle in ("$1,250.00", "+$250.00 in 30 days", "$112.09", "of $150.00 budgeted", "96%",
                   "Over budget", "Fun", "Rent", "due Sun Oct 18", "1 transaction has",
                   'href="https://app.example/Transactions"', 'href="https://app.example"'):
        assert needle in html, needle
    assert "Insurance" not in html                                 # too far off
    assert "Net worth $1,250.00 (+$250.00 in 30 days)" in text
    assert "- Rent $1,200.00, due Sun Oct 18" in text and text.endswith("https://app.example")


def test_the_email_escapes_what_you_typed():
    bad = {**FACTS_INPUT, "bills": bills({"name": "<b>Rent</b> & co", "amount": Decimal("1"),
                                          "next_due_on": TODAY})}
    _, html, _ = digest.weekly_email(digest.week_facts(today=TODAY, **bad))
    assert "&lt;b&gt;Rent&lt;/b&gt; &amp; co" in html and "<b>Rent</b>" not in html


def test_an_empty_app_still_makes_an_email():
    empty = {k: v.iloc[0:0] for k, v in FACTS_INPUT.items()}
    facts = digest.week_facts(today=TODAY, **empty)
    subject, html, text = digest.weekly_email(facts)
    assert facts.net_worth == Decimal("0.00") and facts.savings_rate is None
    assert "Savings rate so far" in html and "—" in text and "Needs attention" not in html


# ---- notify.py, with ntfy and Gmail faked ------------------------------------

@pytest.fixture
def outbox(database, monkeypatch):
    monkeypatch.setattr(data, "today", lambda: TODAY)
    monkeypatch.setenv("NTFY_TOPIC", "secret-topic")
    monkeypatch.setenv("GMAIL_ADDRESS", "me@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-pass")
    monkeypatch.delenv("NOTIFY_TO", raising=False)
    sent = {"pings": [], "emails": [], "logins": []}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"{}"

    def urlopen(request, timeout):
        sent["pings"].append({"url": request.full_url, "body": request.data.decode(),
                              "headers": {k.lower(): v for k, v in request.header_items()}})
        return Response()

    class SMTP:
        def __init__(self, host, port, timeout):
            assert (host, port) == ("smtp.gmail.com", 465)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, user, password):
            sent["logins"].append((user, password))

        def send_message(self, message):
            sent["emails"].append(message)

    monkeypatch.setattr(notify.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", SMTP)
    return sent


def seed_bills():
    data.add_bill("Rent", "1200", "monthly", date(2026, 10, 12))
    data.add_bill("Insurance", "90", "monthly", date(2026, 11, 20))


def test_the_ping_goes_to_ntfy_once_a_day(outbox, capsys):
    seed_bills()
    assert notify.main(["ping"]) == 0
    assert "pinged: 1 bill to pay" in capsys.readouterr().out
    ping = outbox["pings"][0]
    assert ping["url"] == "https://ntfy.sh/secret-topic"
    assert ping["body"] == "Rent $1,200.00 · 2 days overdue"
    assert ping["headers"]["title"] == "1 bill to pay" and ping["headers"]["priority"] == "high"
    assert ping["headers"]["click"] == f"{config.APP_URL}/Bills"
    assert notify.main(["ping"]) == 0
    assert "already sent today" in capsys.readouterr().out and len(outbox["pings"]) == 1
    assert data.get_setting(notify.PING_SENT) == "2026-10-14"


def test_nothing_to_say_sends_nothing(outbox, capsys):
    assert notify.main(["ping"]) == 0
    assert "nothing to ping about" in capsys.readouterr().out and not outbox["pings"]


def test_the_email_goes_through_gmail_with_html_and_text(outbox, capsys):
    seed_bills()
    assert notify.main(["email"]) == 0
    assert "emailed: Money this week · Oct 14" in capsys.readouterr().out
    assert outbox["logins"] == [("me@example.com", "app-pass")]
    message = outbox["emails"][0]
    assert message["To"] == "me@example.com" and message["From"] == "Finance Tracker <me@example.com>"
    assert message.get_content_type() == "multipart/alternative"
    html = message.get_body(("html",)).get_content()
    assert "Rent" in html and "Needs attention" in html
    assert notify.main(["email"]) == 0 and len(outbox["emails"]) == 1


def test_auto_pings_daily_and_emails_on_the_summary_weekday(outbox, monkeypatch):
    seed_bills()
    assert notify.main([]) == 0
    assert len(outbox["pings"]) == 1 and len(outbox["emails"]) == 0      # a Wednesday
    monkeypatch.setattr(data, "today", lambda: MONDAY)
    assert notify.main([]) == 0
    assert len(outbox["pings"]) == 2 and len(outbox["emails"]) == 1


def test_a_different_recipient_and_the_preview(outbox, monkeypatch, capsys):
    monkeypatch.setenv("NOTIFY_TO", "partner@example.com")
    assert notify.main(["email"]) == 0
    assert outbox["emails"][0]["To"] == "partner@example.com"
    seed_bills()
    assert notify.main(["preview"]) == 0
    out = capsys.readouterr().out
    assert "PING: 1 bill to pay" in out and "EMAIL: Money this week" in out
    assert len(outbox["pings"]) == 0 and len(outbox["emails"]) == 1    # preview sent nothing


def test_missing_secrets_make_the_run_red_without_printing_them(outbox, monkeypatch, capsys):
    seed_bills()
    monkeypatch.delenv("NTFY_TOPIC")
    assert notify.main(["ping"]) == 1
    assert "NTFY_TOPIC is not set" in capsys.readouterr().err
    monkeypatch.delenv("GMAIL_APP_PASSWORD")
    assert notify.main(["email"]) == 1
    err = capsys.readouterr().err
    assert "not both set" in err and "app-pass" not in err


def test_an_smtp_failure_is_reported_not_raised(outbox, monkeypatch):
    def boom(*args, **kwargs):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", boom)
    assert notify.main(["email"]) == 1
    assert data.get_setting(notify.EMAIL_SENT) is None                  # so tomorrow retries
