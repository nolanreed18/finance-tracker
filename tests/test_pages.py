"""Every page, run headless against the throwaway database: it draws empty and
with data, the sign-in keeps it private, and the look is a saved choice."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import data
import theme
import ui

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "app" / "Home.py"
PAGES = sorted((ROOT / "app" / "pages").glob("*.py"))
TODAY = date(2026, 10, 14)


PASSWORD = "correct horse"


@pytest.fixture(autouse=True)
def fixed_today(database, monkeypatch):
    monkeypatch.setattr(data, "today", lambda: TODAY)
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)


def new_app(path: Path, signed_in: bool = True) -> AppTest:
    at = AppTest.from_file(str(path), default_timeout=30)
    if signed_in:
        at.session_state[ui.SIGNED_IN] = True
    return at


def run(path: Path) -> AppTest:
    at = new_app(path).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def widget(elements, label, nth: int = 0):
    """The nth widget with this label (-1: the last, e.g. a form below the add form)."""
    matches = [w for w in elements if w.label == label]
    assert matches, f"no widget labelled {label!r}: {[w.label for w in elements]}"
    return matches[nth]


def click(at: AppTest, label: str) -> AppTest:
    widget(at.button, label).click().run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def html(at: AppTest) -> str:
    """Everything the page drew with st.html (empty states, subtitles)."""
    return "\n".join(e.proto.body for e in at.get("html"))


def opened(at: AppTest) -> bool:
    """The page got past the sign-in and drew its content."""
    return any(h.value == "Needs attention" for h in at.subheader)


def seed() -> dict[str, int]:
    """A little of everything, for the draws-with-data tests (grows with each page)."""
    checking = data.add_account("Checking", "checking", institution="First Bank",
                                opened_on=date(2020, 1, 1))
    card = data.add_account("Visa", "credit card", is_liability=True)
    old = data.add_account("Old savings", "savings")
    data.save_balance(checking, date(2026, 10, 10), Decimal("1250.00"))
    data.save_balance(card, date(2026, 8, 1), Decimal("430.25"))        # stale
    data.save_balance(checking, date(2026, 8, 20), Decimal("900.00"))
    data.close_account(old, date(2026, 9, 30))
    food = data.add_category("Food", "expense")
    pay = data.add_category("Pay", "income")
    tx = [data.add_transaction(a, on, amount, kind, TODAY, category_id=c, payee=p) for
          a, on, amount, kind, c, p in (
              (checking, date(2026, 10, 1), Decimal("2500.00"), "income", pay, "Employer"),
              (checking, date(2026, 10, 3), Decimal("-42.10"), "expense", food, "Grocer"),
              (card, date(2026, 10, 12), Decimal("-9.99"), "expense", None, "Streaming"),
              (checking, date(2026, 9, 20), Decimal("-60.00"), "expense", food, "Grocer"))]
    data.set_budget(date(2026, 10, 1), food, Decimal("100"))
    data.set_budget(date(2026, 9, 1), food, Decimal("65"))     # 92% spent: close
    rent = data.add_bill("Rent", Decimal("1200"), "monthly", date(2026, 10, 12),
                         account_id=checking)                                # overdue
    phone = data.add_bill("Phone", Decimal("45.50"), "monthly", date(2026, 10, 20), autopay=True)
    data.add_bill("Gym", Decimal("30"), "monthly", date(2026, 11, 1), active=False)
    trip = data.add_goal("Trip", Decimal("5000"), target_on=date(2027, 4, 1), account_id=checking)
    data.add_goal("Old laptop", Decimal("800"), reached_on=date(2026, 9, 1))
    return {"checking": checking, "card": card, "old": old, "food": food, "pay": pay, "tx": tx,
            "rent": rent, "phone": phone, "trip": trip}


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_draws_empty(path):
    run(path)


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_draws_with_data(path):
    seed()
    run(path)


def test_home_says_what_it_will_show_while_empty():
    at = run(HOME)
    assert at.title[0].value == "Finance Tracker"
    assert opened(at) and "Nothing to show yet" in html(at)
    assert "Wednesday, October 14" in html(at)


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_asks_for_the_password_first(path):
    at = new_app(path, signed_in=False).run()
    assert [t.label for t in at.text_input] == ["Password"]
    assert not at.metric and not at.dataframe and not opened(at)


def test_the_right_password_opens_the_app_and_a_wrong_one_does_not(monkeypatch):
    monkeypatch.setattr(ui.time, "sleep", lambda s: None)
    at = new_app(HOME, signed_in=False).run()
    widget(at.text_input, "Password").set_value("guess")
    click(at, "Sign in")
    assert at.error[0].value == "Wrong password."
    assert not opened(at)
    widget(at.text_input, "Password").set_value(PASSWORD)
    click(at, "Sign in")
    assert opened(at)


def test_dark_mode_is_a_saved_choice_and_light_is_the_default():
    at = run(HOME)
    assert theme.current() == "light" and data.get_setting("theme") is None
    widget(at.toggle, "Dark mode").set_value(True).run()
    assert not at.exception
    assert data.get_setting("theme") == "dark" and theme.current() == "dark"
    for path in PAGES:                                    # every page follows
        assert run(path).toggle[0].value is True
    widget(at.toggle, "Dark mode").set_value(False).run()
    assert data.get_setting("theme") == "light" and theme.current() == "light"


def test_the_switch_follows_a_change_made_on_another_device():
    at = run(HOME)
    assert widget(at.toggle, "Dark mode").value is False
    data.set_setting("theme", "dark")                 # flipped on the phone, say
    at.run()
    assert not at.exception
    assert widget(at.toggle, "Dark mode").value is True
    assert data.get_setting("theme") == "dark" and theme.current() == "dark"
    data.set_setting("theme", "light")
    at.run()
    assert widget(at.toggle, "Dark mode").value is False and theme.current() == "light"


def test_signing_out_locks_the_app_again():
    at = run(HOME)
    click(at, "Sign out")
    assert [t.label for t in at.text_input] == ["Password"] and not opened(at)


def test_no_way_to_sign_in_set_up_keeps_the_app_locked(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD")
    at = new_app(HOME, signed_in=False).run()
    assert "no way to sign in is set up" in at.error[0].value
    assert not at.text_input and not opened(at) and not at.button


@pytest.fixture
def google(monkeypatch):
    """Sign in with Google set up, for you; who is signed in is set per test."""
    monkeypatch.setattr(ui, "_google_ready", lambda: True)
    monkeypatch.setenv("ALLOWED_EMAILS", "Me@Example.com, other@example.com")

    def signed_in_as(email):
        monkeypatch.setattr(ui, "_google_email", lambda: email)
    return signed_in_as


def test_google_offers_both_ways_in_until_someone_signs_in(google):
    google(None)
    at = new_app(HOME, signed_in=False).run()
    assert [b.label for b in at.button] == ["Sign in with Google", "Sign in with password"]
    assert not opened(at)


def test_an_allowed_google_account_goes_straight_in(google):
    google("me@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert opened(at)
    for path in PAGES:                              # and stays in on every page
        assert not new_app(path, signed_in=False).run().exception


def test_any_other_google_account_is_turned_away(google):
    google("stranger@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert "stranger@example.com isn't allowed" in at.error[0].value
    assert [b.label for b in at.button] == ["Sign out"]
    assert not opened(at)


def test_the_sidebar_is_hidden_only_while_signed_out(google, monkeypatch):
    shown = []
    original = st.html
    monkeypatch.setattr(st, "html", lambda body, **kw: (shown.append(body), original(body, **kw)))
    google("me@example.com")
    new_app(HOME, signed_in=False).run()
    assert shown and not any(theme.LOCKED in body for body in shown)
    shown.clear()
    google(None)
    new_app(HOME, signed_in=False).run()
    assert any(theme.LOCKED in body for body in shown)


def test_google_without_allowed_emails_lets_nobody_in(google, monkeypatch):
    monkeypatch.delenv("ALLOWED_EMAILS")
    google("me@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert "isn't allowed" in at.error[0].value and not opened(at)


# ---- accounts ---------------------------------------------------------------

ACCOUNTS = ROOT / "app" / "pages" / "1_Accounts.py"


def test_accounts_show_balances_badges_and_closed_ones_apart():
    seed()
    at = run(ACCOUNTS)
    cards = [m.value for m in at.markdown if "**" in m.value]
    assert cards[0].startswith("**Checking**") and ":gray-badge[Checking]" in cards[0]
    assert "First Bank · updated 4 days ago" in cards[0]
    assert ":violet-badge[Liability]" in cards[1] and ":yellow-badge[Update balance]" in cards[1]
    assert "**Old savings**" in cards[2] and ":gray-badge[Closed]" in cards[2]
    assert [h.value for h in at.subheader] == ["Open", "Closed", "Edit"]
    amounts = [m.value for m in at.markdown if m.value.startswith("#### ")]
    assert amounts == ["#### \\$1,250.00", "#### \\$430.25"]


def test_adding_an_account_marks_cards_as_liabilities_and_refuses_a_duplicate_name():
    at = run(ACCOUNTS)
    assert not at.text_input                      # the form waits behind its button
    click(at, "Add an account")
    widget(at.text_input, "Name").set_value("Amex")
    widget(at.selectbox, "Type").set_value("credit card")
    click(at, "Add account")
    acct = data.accounts().iloc[0]
    assert (acct["name"], acct["kind"], bool(acct["is_liability"])) == ("Amex", "credit card", True)
    assert at.success[0].value == "Added Amex."
    click(at, "Add an account")
    widget(at.text_input, "Name").set_value("amex")
    click(at, "Add account")
    assert at.error[0].value == "There's already an account with that name."
    assert len(data.accounts()) == 1


def test_an_account_with_history_is_closed_not_deleted():
    ids = seed()
    at = new_app(ACCOUNTS)
    at.session_state[ui.round_key("pick_account")] = ids["checking"]
    at.run()
    assert not [b for b in at.button if b.label == "Delete account"]
    assert any("can't be deleted" in c.value for c in at.caption)
    click(at, "Close account")
    assert data.account(ids["checking"])["closed_on"] == TODAY
    assert at.success[0].value == "Closed Checking."
    click(at, "Reopen account")
    assert data.account(ids["checking"])["closed_on"] is None


def test_deleting_an_empty_account_needs_the_tick():
    wallet = data.add_account("Wallet", "cash")
    at = new_app(ACCOUNTS)
    at.session_state[ui.round_key("pick_account")] = wallet
    at.run()
    assert widget(at.button, "Delete account").disabled
    widget(at.checkbox, "I want to delete this account").check().run()
    click(at, "Delete account")
    assert data.accounts().empty
    assert at.success[0].value == "Deleted Wallet."


def test_editing_an_account_saves_and_refuses_a_taken_name():
    ids = seed()
    at = new_app(ACCOUNTS)
    at.session_state[ui.round_key("pick_account")] = ids["card"]
    at.run()
    widget(at.text_input, "Name", -1).set_value("checking")
    click(at, "Save changes")
    assert at.error[0].value == "There's already an account with that name."
    widget(at.text_input, "Name", -1).set_value("Chase Visa")
    widget(at.text_input, "Bank or institution", -1).set_value("Chase")
    click(at, "Save changes")
    acct = data.account(ids["card"])
    assert (acct["name"], acct["institution"]) == ("Chase Visa", "Chase")


# ---- transactions -----------------------------------------------------------

TRANSACTIONS = ROOT / "app" / "pages" / "2_Transactions.py"


def test_transactions_need_an_account_first():
    at = run(TRANSACTIONS)
    assert "No open accounts yet" in html(at) and not at.selectbox


def test_transactions_show_totals_for_the_filter():
    ids = seed()
    at = run(TRANSACTIONS)
    assert [m.value for m in at.metric] == ["$2,500.00", "$112.09", "$2,387.91"]
    assert len(at.dataframe[0].value) == 4
    widget(at.selectbox, "Month").set_value(date(2026, 9, 1)).run()
    assert [m.value for m in at.metric] == ["$0.00", "$60.00", "−$60.00"]
    assert len(at.dataframe[0].value) == 1
    widget(at.selectbox, "Month").set_value(None)
    widget(at.selectbox, "Category").set_value(ids["food"])
    widget(at.text_input, "Search").set_value("grocer").run()
    assert widget(at.metric, "Spending").value == "$102.10"
    widget(at.text_input, "Search").set_value("zzz").run()
    assert "Nothing matches" in html(at)


def test_adding_an_expense_stores_it_negative():
    ids = seed()
    at = run(TRANSACTIONS)
    click(at, "Add a transaction")
    widget(at.number_input, "Amount ($)").set_value(12.5)
    widget(at.selectbox, "Category").set_value(ids["food"])
    widget(at.text_input, "Payee").set_value("Cafe")
    click(at, "Add transaction")
    row = data.transactions().iloc[0]
    assert (row["amount"], row["kind"], row["payee"], row["category"], row["happened_on"]) == (
        Decimal("-12.50"), "expense", "Cafe", "Food", TODAY)
    assert at.success[0].value == "Added −$12.50 at Cafe."
    assert widget(at.selectbox, "Transaction").value == int(row["transaction_id"])


def test_an_amount_is_required():
    seed()
    at = run(TRANSACTIONS)
    click(at, "Add a transaction")
    click(at, "Add transaction")
    assert at.error[0].value == "Enter the amount."
    assert len(data.transactions()) == 4


def test_editing_a_transaction_resigns_the_amount_from_its_kind():
    ids = seed()
    at = new_app(TRANSACTIONS)
    at.session_state[ui.round_key("pick_transaction")] = ids["tx"][1]
    at.run()
    widget(at.radio, "Kind").set_value("income")
    widget(at.number_input, "Amount ($)").set_value(50)
    click(at, "Save changes")
    row = data.transaction(ids["tx"][1])
    assert (row["amount"], row["kind"]) == (Decimal("50.00"), "income")


def test_deleting_a_transaction_needs_the_tick():
    ids = seed()
    at = new_app(TRANSACTIONS)
    at.session_state[ui.round_key("pick_transaction")] = ids["tx"][2]
    at.run()
    assert widget(at.button, "Delete transaction").disabled
    widget(at.checkbox, "I want to delete this transaction").check().run()
    click(at, "Delete transaction")
    assert data.transaction(ids["tx"][2]) is None
    assert at.success[0].value == "Deleted −$9.99 at Streaming."


# ---- budgets ----------------------------------------------------------------

BUDGETS = ROOT / "app" / "pages" / "3_Budgets.py"


def test_the_budget_shows_each_category_against_its_spending():
    seed()
    data.add_category("Rent", "expense")
    at = run(BUDGETS)
    assert [m.value for m in at.metric] == ["$100.00", "$42.10", "$57.90"]   # categorised only
    bars = at.get("progress")
    assert len(bars) == 1 and bars[0].value == 42
    assert "\\$42.10 of \\$100.00 · \\$57.90 left" in bars[0].proto.text
    assert any(":green-badge[On track]" in m.value for m in at.markdown)
    assert any("no budget set" in c.value for c in at.caption)
    widget(at.selectbox, "Month").set_value(date(2026, 9, 1)).run()
    assert [m.value for m in at.metric] == ["$65.00", "$60.00", "$5.00"]
    assert any(":orange-badge[Close to budget]" in m.value for m in at.markdown)


def test_setting_budgets_saves_every_category_at_once():
    ids = seed()
    rent = data.add_category("Rent", "expense")
    at = run(BUDGETS)
    click(at, "Set budgets")
    widget(at.number_input, "Food").set_value(120.0)
    widget(at.number_input, "Rent").set_value(900.0)
    click(at, "Save budgets")
    rows = data.budgets(date(2026, 10, 1)).set_index("category_id")
    assert rows.loc[ids["food"], "budgeted"] == Decimal("120.00")
    assert rows.loc[rent, "budgeted"] == Decimal("900.00")
    assert at.success[0].value == "Budgets saved for October 2026."


def test_copy_last_month_appears_only_for_an_unbudgeted_month():
    seed()
    at = run(BUDGETS)
    assert not [b for b in at.button if b.label.startswith("Copy ")]
    widget(at.selectbox, "Month").set_value(date(2026, 11, 1)).run()
    click(at, "Copy October 2026")
    assert data.budgets(date(2026, 11, 1))["budgeted"].tolist() == [Decimal("100.00")]
    assert at.success[0].value == "Copied 1 budget from October 2026."


def test_categories_are_added_renamed_and_archived_here():
    ids = seed()
    at = run(BUDGETS)
    widget(at.radio, "Section").set_value("Categories").run()
    click(at, "Add a category")
    widget(at.text_input, "Name").set_value("food")
    click(at, "Add category")
    assert at.error[0].value == "There's already a category with that name."
    widget(at.text_input, "Name").set_value("Rent")
    click(at, "Add category")
    assert data.categories()["name"].tolist() == ["Food", "Rent", "Pay"]
    assert at.success[0].value == "Added Rent."
    at.session_state[ui.round_key("pick_category")] = ids["food"]
    at.run()
    widget(at.text_input, "Name", -1).set_value("Groceries")
    click(at, "Save changes")
    assert data.transaction(ids["tx"][1])["category"] == "Groceries"
    click(at, "Archive")
    assert data.categories()["name"].tolist() == ["Rent", "Pay"]
    assert any(":gray-badge[Archived]" in m.value for m in at.markdown)


# ---- bills ------------------------------------------------------------------

BILLS = ROOT / "app" / "pages" / "4_Bills.py"


def test_bills_show_what_is_due_and_what_is_paused():
    seed()
    at = run(BILLS)
    assert [m.value for m in at.metric] == ["$1,245.50", "1", "1"]
    cards = [m.value for m in at.markdown if m.value.startswith("**")]
    assert cards[0].startswith("**Rent** :red-badge[Overdue]") and "2 days overdue" in cards[0]
    assert ":orange-badge[Due]" in cards[1] and ":blue-badge[Autopay]" in cards[1]
    assert "due Tue Oct 20" in cards[1]
    assert cards[2].startswith("**Gym** :gray-badge[Paused]")
    assert [h.value for h in at.subheader] == ["Coming up", "Paused", "Edit"]


def test_marking_paid_moves_the_date_and_logs_the_transaction():
    ids = seed()
    at = run(BILLS)
    click(at, "Mark paid")                                  # the first card: Rent
    assert data.bill(ids["rent"])["next_due_on"] == date(2026, 11, 12)
    tx = data.transactions().iloc[0]
    assert (tx["amount"], tx["payee"], tx["account"]) == (Decimal("-1200.00"), "Rent", "Checking")
    assert at.success[0].value == "Rent paid; next due Thu Nov 12. Transaction logged."
    before = len(data.transactions())
    widget(at.checkbox, "Log a transaction when I mark a bill paid").uncheck().run()
    click(at, "Mark paid")                                  # now Phone is first
    assert data.bill(ids["phone"])["next_due_on"] == date(2026, 11, 20)
    assert len(data.transactions()) == before


def test_a_bill_without_an_account_cannot_log_a_payment():
    seed()
    at = run(BILLS)
    widget(at.button, "Mark paid", 1).click().run()          # Phone has no account
    assert "has no account" in at.error[0].value
    assert len(data.transactions()) == 4


def test_adding_a_bill():
    seed()
    at = run(BILLS)
    click(at, "Add a bill")
    widget(at.text_input, "Name").set_value("Internet")
    widget(at.number_input, "Amount ($)").set_value(60.0)
    widget(at.date_input, "Next due").set_value(date(2026, 10, 25))
    click(at, "Add bill")
    row = data.bills().set_index("name").loc["Internet"]
    assert (row["amount"], row["cadence"], row["next_due_on"]) == (
        Decimal("60.00"), "monthly", date(2026, 10, 25))
    assert at.success[0].value == "Added Internet."


def test_deleting_a_bill_needs_the_tick():
    ids = seed()
    at = new_app(BILLS)
    at.session_state[ui.round_key("pick_bill")] = ids["phone"]
    at.run()
    assert widget(at.button, "Delete bill").disabled
    widget(at.checkbox, "I want to delete this bill").check().run()
    click(at, "Delete bill")
    assert data.bill(ids["phone"]) is None


# ---- net worth --------------------------------------------------------------

NET_WORTH = ROOT / "app" / "pages" / "5_Net_worth.py"


def test_net_worth_shows_the_numbers_the_chart_and_the_table():
    seed()
    at = run(NET_WORTH)
    assert [m.value for m in at.metric] == ["$819.75", "$1,250.00", "$430.25"]
    chart = at.get("vega_lite_chart")
    assert len(chart) == 1
    assert len(at.dataframe[0].value) == 2                   # the closed account is left out
    assert any(":yellow-badge[Update balance]" in m.value and "Visa" in m.value
               for m in at.markdown)


def test_net_worth_without_balances_asks_for_them():
    data.add_account("Checking", "checking")
    at = run(NET_WORTH)
    assert [m.value for m in at.metric] == ["$0.00", "$0.00", "$0.00"]
    assert "No balances yet" in html(at) and not at.dataframe


def test_updating_balances_saves_every_open_account_at_once():
    ids = seed()
    at = run(NET_WORTH)
    click(at, "Update balances")
    inputs = {n.label: n.value for n in at.number_input}
    assert inputs == {"Checking": 1250.0, "Visa (owed)": 430.25}
    widget(at.number_input, "Visa (owed)").set_value(400.0)
    click(at, "Save balances")
    assert data.account(ids["card"])["balance"] == Decimal("400.00")
    assert data.account(ids["card"])["balance_on"] == TODAY
    assert data.account(ids["checking"])["balance_on"] == TODAY      # prefilled, saved too
    assert at.success[0].value == "Saved 2 balances as of today."
    assert [m.value for m in at.metric] == ["$850.00", "$1,250.00", "$400.00"]


# ---- goals ------------------------------------------------------------------

GOALS = ROOT / "app" / "pages" / "6_Goals.py"


def test_goals_show_progress_from_the_accounts_balance():
    seed()
    at = run(GOALS)
    cards = [m.value for m in at.markdown if m.value.startswith("**")]
    assert cards[0].startswith("**Trip** :blue-badge[Saving]")
    assert "\\$1,250.00 of \\$5,000.00 · by Apr 1, 2027 · in Checking" in cards[0]
    assert cards[1].startswith("**Old laptop** :green-badge[Reached]")
    bars = at.get("progress")
    assert bars[0].value == 25 and "\\$625.00 a month to reach it" in bars[0].proto.text
    assert bars[1].value == 0 and bars[1].proto.text == "0%"


def test_adding_a_goal_and_marking_it_reached():
    ids = seed()
    at = run(GOALS)
    click(at, "Add a goal")
    widget(at.text_input, "Name").set_value("Emergency fund")
    widget(at.number_input, "Target ($)").set_value(1000.0)
    widget(at.selectbox, "Account holding the money").set_value(ids["checking"])
    click(at, "Add goal")
    goal = data.goals().set_index("name").loc["Emergency fund"]
    assert goal["target_amount"] == Decimal("1000.00") and goal["account_id"] == ids["checking"]
    assert at.success[0].value == "Added Emergency fund."
    assert any(":green-badge[Reached]" in m.value and "Emergency fund" in m.value
               for m in at.markdown)                     # $1,250 covers it already
    click(at, "Mark reached")
    assert data.goal(int(goal["goal_id"]))["reached_on"] == TODAY


def test_deleting_a_goal_needs_the_tick():
    ids = seed()
    at = new_app(GOALS)
    at.session_state[ui.round_key("pick_goal")] = ids["trip"]
    at.run()
    assert widget(at.button, "Delete goal").disabled
    widget(at.checkbox, "I want to delete this goal").check().run()
    click(at, "Delete goal")
    assert data.goal(ids["trip"]) is None


# ---- stats ------------------------------------------------------------------

STATS = ROOT / "app" / "pages" / "7_Stats.py"


def test_stats_draw_the_month_the_year_and_the_payees():
    seed()
    at = run(STATS)
    assert [h.value for h in at.subheader] == ["Spending by category",
                                               "Income and spending, 12 months",
                                               "Savings rate", "Top payees"]
    assert len(at.get("vega_lite_chart")) == 3            # category bars, income/spending, rate
    by_month, payees = at.dataframe[0].value, at.dataframe[1].value
    assert by_month.columns.tolist() == ["category", "Aug 2026", "Sep 2026", "Oct 2026", "Total"]
    assert by_month["category"].tolist() == ["Food", "(uncategorised)"]
    assert payees["payee"].tolist() == ["Grocer", "Streaming"]
    widget(at.selectbox, "Month").set_value(date(2026, 8, 1)).run()
    assert "No spending that month" in html(at)
    assert not at.dataframe                                  # Jun to Aug: no spending, no payees
    assert any("No spending in those months" in c.value for c in at.caption)


def test_stats_without_transactions_say_so():
    at = run(STATS)
    assert "Nothing to chart yet" in html(at) and not at.get("vega_lite_chart")


# ---- import -----------------------------------------------------------------

IMPORT = ROOT / "app" / "pages" / "8_Import.py"
CSV = ("Transaction Date,Description,Amount,Category\n"
       "10/12/2026,CAFE #12,-4.50,Food\n"
       "10/01/2026,PAYROLL,2500.00,Pay\n"
       "10/13/2026,GAS,-40,Car\n")


def test_import_previews_then_adds_all_at_once_and_never_twice():
    ids = seed()
    at = run(IMPORT)
    assert not at.dataframe                                  # nothing until a file arrives
    widget(at.text_area, "…or paste the rows, header line first").set_value(CSV).run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 3
    assert at.warning[0].value == "Categories not in your list were left blank: Car."
    assert any("3 new transactions" in m.value for m in at.markdown)
    click(at, "Import 3 transactions into Checking")
    assert at.success[0].value == "Imported 3 transactions."
    added = data.transactions(account_id=ids["checking"])
    assert len(added) == 4 + 3 - 1                           # seed had 3 on Checking
    cafe = added[added["payee"] == "CAFE #12"].iloc[0]
    assert (cafe["amount"], cafe["kind"], cafe["category"]) == (Decimal("-4.50"), "expense", "Food")
    # The same file again: everything is already there.
    widget(at.text_area, "…or paste the rows, header line first").set_value(CSV).run()
    assert at.info[0].value == "Every row in this file is already in your transactions."
    assert not [b for b in at.button if b.label.startswith("Import ")]
    assert len(data.transactions(account_id=ids["checking"])) == 6


def test_import_refuses_a_file_without_the_right_headers():
    seed()
    at = run(IMPORT)
    widget(at.text_area, "…or paste the rows, header line first").set_value("a,b\n1,2\n").run()
    assert "Nothing to import" in html(at) and len(at.warning) == 3


def test_import_needs_an_account_first():
    at = run(IMPORT)
    assert "No open accounts yet" in html(at)
