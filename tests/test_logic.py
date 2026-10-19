"""The pure calculations: months, money, formatting, import headers."""

from datetime import date, time
from decimal import Decimal

import pandas as pd
import pytest

import logic

TODAY = date(2026, 10, 14)            # a Wednesday


def test_blank_and_value():
    for empty in (None, "", "  ", float("nan"), pd.NaT):
        assert logic.blank(empty) and logic.value(empty) is None
    for kept in (0, Decimal("0"), "x", False):
        assert not logic.blank(kept) and logic.value(kept) == kept


# ---- months -----------------------------------------------------------------

def test_a_month_is_named_by_its_first_day():
    assert logic.month_start(TODAY) == date(2026, 10, 1)


def test_adding_months_keeps_the_day_or_takes_the_months_last():
    assert logic.add_months(TODAY, 1) == date(2026, 11, 14)
    assert logic.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert logic.add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)    # leap year
    assert logic.add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert logic.add_months(date(2026, 1, 15), -1) == date(2025, 12, 15)
    assert logic.add_months(date(2026, 3, 31), -13) == date(2025, 2, 28)


# ---- money ------------------------------------------------------------------

@pytest.mark.parametrize("given, expected", [
    ("1,234.56", Decimal("1234.56")), ("$12", Decimal("12.00")), ("-4.5", Decimal("-4.50")),
    ("($12.50)", Decimal("-12.50")), (" $ 3.005 ", Decimal("3.01")), (0.1, Decimal("0.10")),
    (7, Decimal("7.00")), (Decimal("2.345"), Decimal("2.35")),
])
def test_amounts_become_decimal_to_the_cent(given, expected):
    assert logic.to_money(given) == expected
    assert isinstance(logic.to_money(given), Decimal)


def test_blank_is_no_amount_and_nonsense_is_refused():
    assert logic.to_money("") is None and logic.to_money(None) is None
    for nonsense in ("abc", "1.2.3", "NaN", "inf"):
        with pytest.raises(ValueError):
            logic.to_money(nonsense)


def test_money_text():
    assert logic.money(Decimal("1234.5")) == "$1,234.50"
    assert logic.money(Decimal("-12")) == "−$12.00"
    assert logic.money(0) == "$0.00"
    assert logic.money(None) == "—"


def test_percent_text():
    assert logic.percent(Decimal("0.425")) == "42%"
    assert logic.percent(None) == "—"


# ---- formatting -------------------------------------------------------------

def test_tables_show_blanks_dates_and_amounts():
    frame = pd.DataFrame({"payee": ["Shop", None], "on": [TODAY, None],
                          "amount": [Decimal("-1.50"), None]})
    shown = logic.for_display(frame, dates=("on",), amounts=("amount",))
    assert shown["payee"].tolist() == ["Shop", ""]
    assert shown["on"].iloc[0] == pd.Timestamp(TODAY) and pd.isna(shown["on"].iloc[1])
    assert shown["amount"].iloc[0] == -1.5 and pd.isna(shown["amount"].iloc[1])
    assert frame["on"].iloc[0] == TODAY                         # the original is untouched


def test_plural_when_and_clock():
    assert (logic.plural(1, "bill"), logic.plural(3, "bill")) == ("1 bill", "3 bills")
    assert logic.when(TODAY, TODAY) == "today"
    assert logic.when(date(2026, 10, 15), TODAY) == "tomorrow"
    assert logic.when(date(2026, 10, 13), TODAY) == "yesterday"
    assert logic.when(date(2026, 10, 20), TODAY) == "Tue Oct 20"
    assert logic.clock(time(0, 5)) == "12:05 am" and logic.clock(time(13, 30)) == "1:30 pm"


# ---- import headers ---------------------------------------------------------

def test_bank_headers_are_matched_loosely():
    found = logic.match_columns(["Posted_Date", "Description", "Debit", "Credit", "Balance"])
    assert found == {"date": "Posted_Date", "description": "Description",
                     "debit": "Debit", "credit": "Credit"}
    assert logic.match_columns(["Transaction Date", "Payee", "Amount", "Category"]) == {
        "date": "Transaction Date", "description": "Payee", "amount": "Amount",
        "category": "Category"}


# ---- accounts ---------------------------------------------------------------

def test_a_balance_is_stale_after_thirty_days_or_when_there_is_none():
    assert logic.stale_balance(None, TODAY)
    assert logic.stale_balance(date(2026, 9, 14), TODAY)              # exactly 30 days
    assert not logic.stale_balance(date(2026, 9, 15), TODAY)
    assert logic.stale_balance(date(2026, 10, 1), TODAY, days=10)


def test_balance_age_text():
    assert logic.balance_age(TODAY, TODAY) == "updated today"
    assert logic.balance_age(date(2026, 10, 13), TODAY) == "updated 1 day ago"
    assert logic.balance_age(date(2026, 10, 1), TODAY) == "updated 13 days ago"
    assert logic.balance_age(date(2026, 9, 2), TODAY) == "updated Sep 2"
    assert logic.balance_age(date(2025, 12, 2), TODAY) == "updated Dec 2, 2025"
    assert logic.balance_age(None, TODAY) == "no balance yet"
