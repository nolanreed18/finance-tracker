"""The morning ping and the Monday email, built by code from the frames
data.py returns. Pure, like logic.py: no database, no Streamlit, no network,
so every line of what gets sent is tested.

The ping (daily_ping) is a few plain lines for a phone notification. The
email (weekly_email) is one self-contained HTML page in the app's colours,
email-safe: tables, inline styles, no scripts or web fonts; well under
Gmail's 100 KB clipping limit.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from html import escape

import pandas as pd

import config
import logic

# The light palette, inline (emails can't load a stylesheet).
INK, INK2, MUTED = "#0f172a", "#475569", "#64748b"
CARD, PAGE, BORDER, BLUE = "#ffffff", "#f8fafc", "#e2e8f0", "#2563eb"
RED, ORANGE, GREEN, YELLOW = "#f43f5e", "#f59e0b", "#10b981", "#ca8a04"
BADGE_COLORS = {"overdue": RED, "due": ORANGE, "over": RED, "close": ORANGE, "stale": YELLOW,
                "relink": RED}
BADGE_TEXT = {"overdue": "Overdue", "due": "Due", "over": "Over budget", "close": "Close",
              "stale": "Update balance", "relink": "Sign in again"}


@dataclass(frozen=True)
class Ping:
    title: str
    lines: list[str]
    urgent: bool                  # anything overdue or a bank to sign in to again
    url: str

    @property
    def body(self) -> str:
        return "\n".join(self.lines)


# ---- the morning ping -------------------------------------------------------

def daily_ping(bills: pd.DataFrame, connections: pd.DataFrame, today: date,
               reminder_days: int = config.REMINDER_DAYS, url: str = config.APP_URL
               ) -> Ping | None:
    """Bills overdue or due within reminder_days, and banks that need a new
    sign-in; None when there's nothing to say (no ping is sent)."""
    lines, urgent = [], False
    for row in connections.itertuples(index=False):
        if not logic.blank(row.last_error):
            lines.append(f"{logic.value(row.institution_name) or 'A bank'}: sign in again "
                         "to keep syncing")
            urgent = True
    due: list[tuple[date, str]] = []
    for row in bills.itertuples(index=False):
        if not row.active:
            continue
        state = logic.bill_state(row.next_due_on, today, lookahead=reminder_days)
        if state is None:
            continue
        urgent = urgent or state == "overdue"
        text = f"{row.name} {logic.money(row.amount)} · {logic.due_text(row.next_due_on, today)}"
        if row.autopay:
            text += " (autopay)"
        due.append((row.next_due_on, text))
    lines += [text for _, text in sorted(due)]
    if not lines:
        return None
    count = sum(1 for _ in due)
    title = (f"{logic.plural(count, 'bill')} to pay" if count else "Finance Tracker")
    return Ping(title, lines, urgent, f"{url}/Bills" if count else f"{url}/Accounts")


# ---- the Monday email -------------------------------------------------------

@dataclass(frozen=True)
class WeekFacts:
    """Everything the weekly email says, as plain values (built by
    week_facts, rendered by weekly_email, so each half is tested alone)."""
    today: date
    net_worth: Decimal
    net_worth_change: Decimal          # vs 30 days ago
    spent_month: Decimal
    budgeted_month: Decimal
    savings_rate: Decimal | None
    spent_week: Decimal
    week_by_category: pd.DataFrame     # category, spent
    attention: list[logic.Attention]
    upcoming_bills: pd.DataFrame       # name, amount, next_due_on, autopay
    uncategorised: int


def week_facts(transactions: pd.DataFrame, budgets: pd.DataFrame, bills: pd.DataFrame,
               accounts: pd.DataFrame, balances: pd.DataFrame, connections: pd.DataFrame,
               today: date) -> WeekFacts:
    """The numbers from the frames: `transactions` must reach back at least
    to the start of this month and 7 days."""
    month = logic.month_start(today)
    this_month = logic.in_month(transactions, month)
    sums = logic.totals(this_month)
    week_start = today - timedelta(days=7)
    week = (transactions[transactions["happened_on"] > week_start]
            if not transactions.empty else transactions)
    budget = logic.budget_summary(budgets)
    upcoming = bills[bills["active"].astype(bool)] if not bills.empty else bills
    if not upcoming.empty:
        horizon = today + timedelta(days=config.BILL_LOOKAHEAD_DAYS)
        upcoming = upcoming[upcoming["next_due_on"] <= horizon].sort_values("next_due_on")
    now = logic.net_worth_now(accounts)["net"]
    return WeekFacts(
        today=today, net_worth=now,
        net_worth_change=now - logic.net_worth_on(balances, today - timedelta(days=30)),
        spent_month=sums["spending"], budgeted_month=budget["budgeted"],
        savings_rate=logic.savings_rate(sums["income"], sums["spending"]),
        spent_week=logic.totals(week)["spending"],
        week_by_category=logic.spending_by_category(week),
        attention=logic.needs_attention(bills, budgets, accounts, today, connections),
        upcoming_bills=upcoming, uncategorised=logic.uncategorised(this_month),
    )


def _row(label: str, value: str, muted: str = "") -> str:
    return (f'<tr><td style="padding:6px 0;color:{INK2}">{escape(label)}</td>'
            f'<td style="padding:6px 0;text-align:right;font-family:ui-monospace,Menlo,monospace;'
            f'color:{INK}">{escape(value)}'
            + (f' <span style="color:{MUTED};font-size:12px">{escape(muted)}</span>' if muted
               else "") + "</td></tr>")


def _badge(kind: str) -> str:
    color = BADGE_COLORS.get(kind, MUTED)
    return (f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
            f'font-size:12px;font-family:ui-monospace,Menlo,monospace;color:{color};'
            f'border:1px solid {color}">{escape(BADGE_TEXT.get(kind, kind))}</span>')


def _card(title: str, inner: str) -> str:
    return (f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:12px;'
            f'padding:14px 16px;margin:0 0 12px">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:'
            f'uppercase;color:{INK2};margin-bottom:6px">{escape(title)}</div>{inner}</div>')


def _signed(amount: Decimal) -> str:
    return ("+" if amount >= 0 else "") + logic.money(amount)


def weekly_email(facts: WeekFacts, url: str = config.APP_URL) -> tuple[str, str, str]:
    """(subject, html, text) for the Monday email."""
    t = facts.today
    subject = f"Money this week · {t:%b} {t.day}"
    parts = []
    headline = (
        _row("Net worth", logic.money(facts.net_worth),
             f"{_signed(facts.net_worth_change)} in 30 days")
        + _row("Spent this month", logic.money(facts.spent_month),
               f"of {logic.money(facts.budgeted_month)} budgeted" if facts.budgeted_month
               else "no budget set")
        + _row("Savings rate so far", logic.percent(facts.savings_rate))
        + _row("Spent in the last 7 days", logic.money(facts.spent_week)))
    parts.append(_card("Where things stand", f'<table style="width:100%;border-collapse:collapse">'
                       f'{headline}</table>'))
    if facts.attention:
        items = "".join(
            f'<tr><td style="padding:6px 0">{_badge(a.kind)} <b>{escape(a.headline)}</b>'
            f'<div style="color:{INK2};font-size:13px">{escape(a.detail)}</div></td></tr>'
            for a in facts.attention)
        parts.append(_card("Needs attention", f'<table style="border-collapse:collapse">{items}'
                           "</table>"))
    if not facts.upcoming_bills.empty:
        rows = "".join(_row(f"{b.name}" + (" (autopay)" if b.autopay else ""),
                            logic.money(b.amount), logic.due_text(b.next_due_on, t))
                       for b in facts.upcoming_bills.itertuples(index=False))
        parts.append(_card(f"Bills in the next {config.BILL_LOOKAHEAD_DAYS} days",
                           f'<table style="width:100%;border-collapse:collapse">{rows}</table>'))
    if not facts.week_by_category.empty:
        rows = "".join(_row(c.category, logic.money(c.spent))
                       for c in facts.week_by_category.head(8).itertuples(index=False))
        parts.append(_card("Last 7 days by category",
                           f'<table style="width:100%;border-collapse:collapse">{rows}</table>'))
    if facts.uncategorised:
        parts.append(_card("To tidy", f'<div style="color:{INK2}">{facts.uncategorised} '
                           f"{'transaction has' if facts.uncategorised == 1 else 'transactions have'}"
                           f' no category yet. <a href="{url}/Transactions" style="color:{BLUE}">'
                           "Sort them</a> so the budgets add up.</div>"))
    html = (
        f'<!doctype html><html><body style="margin:0;background:{PAGE};padding:20px;'
        f'font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{INK};font-size:15px">'
        f'<div style="max-width:560px;margin:0 auto">'
        f'<div style="font-weight:700;font-size:20px;margin-bottom:2px">Finance Tracker</div>'
        f'<div style="color:{MUTED};font-family:ui-monospace,Menlo,monospace;font-size:12px;'
        f'margin-bottom:16px">{escape(f"{t:%A, %B} {t.day}")}</div>'
        + "".join(parts)
        + f'<p style="margin:16px 0 0"><a href="{url}" style="display:inline-block;background:'
        f'{BLUE};color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;'
        f'font-weight:600">Open Finance Tracker</a></p>'
        f'<p style="color:{MUTED};font-size:12px;margin-top:20px">Sent every '
        f'{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][config.SUMMARY_WEEKDAY]} '
        f"morning by your Finance Tracker (notify.py).</p></div></body></html>")
    text_lines = [
        f"Finance Tracker, {t:%A, %B} {t.day}", "",
        f"Net worth {logic.money(facts.net_worth)} ({_signed(facts.net_worth_change)} in 30 days)",
        f"Spent this month {logic.money(facts.spent_month)}"
        + (f" of {logic.money(facts.budgeted_month)} budgeted" if facts.budgeted_month else ""),
        f"Savings rate so far {logic.percent(facts.savings_rate)}",
        f"Spent in the last 7 days {logic.money(facts.spent_week)}",
    ]
    if facts.attention:
        text_lines += ["", "Needs attention:"] + [f"- {a.headline}: {a.detail}"
                                                  for a in facts.attention]
    if not facts.upcoming_bills.empty:
        text_lines += ["", f"Bills in the next {config.BILL_LOOKAHEAD_DAYS} days:"] + [
            f"- {b.name} {logic.money(b.amount)}, {logic.due_text(b.next_due_on, t)}"
            for b in facts.upcoming_bills.itertuples(index=False)]
    if facts.uncategorised:
        text_lines += ["", f"{facts.uncategorised} transactions have no category yet."]
    text_lines += ["", url]
    return subject, html, "\n".join(text_lines)
