"""data.py against a real (throwaway) Postgres with the real schema."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest

import apply_schema
import config
import data
import logic


@pytest.fixture(autouse=True)
def _db(database):
    return database


def test_a_setting_is_saved_over_and_unset_means_the_default():
    assert data.get_setting("theme") is None
    assert data.get_setting("theme", "light") == "light"
    data.set_setting("theme", "dark")
    data.set_setting("theme", "light")
    assert data.get_setting("theme") == "light"


def test_the_schema_can_be_run_again_and_keeps_what_is_there(database):
    data.set_setting("theme", "dark")
    with psycopg.connect(database, autocommit=True) as conn:
        apply_schema.apply(conn)
    assert data.get_setting("theme") == "dark"


def test_a_new_database_gets_its_tables_on_first_connection(database, monkeypatch):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("drop table settings")
    monkeypatch.setattr(data, "_schema_ready", False)
    data.reset_connection()
    assert data.get_setting("theme") is None          # recreated, not an error


def test_a_closed_connection_is_reopened():
    data.get_setting("theme")
    data._conn.close()
    assert data.get_setting("theme") is None


def test_a_connection_the_server_dropped_while_idle_is_replaced(monkeypatch, database):
    """As when Neon suspends: the next use after a quiet spell pings, finds the
    connection dead, and reconnects instead of failing the page."""
    data.get_setting("theme")
    with psycopg.connect(database, autocommit=True) as other:
        other.execute("select pg_terminate_backend(%s)", (data._conn.info.backend_pid,))
    monkeypatch.setattr(data, "_last_used", 0.0)
    assert data.get_setting("theme") is None


def test_migrations_are_safe_to_run_again():
    data.migrate()
    data.migrate()


# ---- the schema's lists match config.py -------------------------------------

def allowed(database, statement: str, values: list) -> list:
    """The values the schema accepts in `statement` (one %s), each tried in a
    rolled-back transaction."""
    accepted = []
    with psycopg.connect(database) as conn:
        for v in values:
            try:
                with conn.transaction():
                    conn.execute(statement, (v,))
                    accepted.append(v)
                    raise psycopg.Rollback()
            except psycopg.errors.CheckViolation:
                pass
    return accepted


def test_every_account_type_is_allowed_by_the_schema_and_nothing_else(database):
    statement = "insert into accounts (name, kind) values ('A', %s)"
    assert allowed(database, statement, [*config.ACCOUNT_TYPES, "piggy bank"]) \
        == config.ACCOUNT_TYPES
    assert set(config.LIABILITY_TYPES) <= set(config.ACCOUNT_TYPES)


def test_every_category_kind_is_allowed_by_the_schema_and_nothing_else(database):
    statement = "insert into categories (name, kind) values ('A', %s)"
    assert allowed(database, statement, [*config.CATEGORY_KINDS, "transfer"]) \
        == config.CATEGORY_KINDS


def test_every_transaction_kind_is_allowed_by_the_schema_and_nothing_else(database):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("insert into accounts (name, kind) values ('Checking', 'checking')")
    statement = """insert into transactions (account_id, happened_on, amount, kind, created_on)
                   values (1, '2026-10-14', -1.00, %s, '2026-10-14')"""
    assert allowed(database, statement, [*config.TRANSACTION_KINDS, "refund"]) \
        == config.TRANSACTION_KINDS


def test_every_cadence_is_allowed_by_the_schema_and_nothing_else(database):
    statement = """insert into bills (name, amount, cadence, next_due_on)
                   values ('Rent', 1000, %s, '2026-11-01')"""
    assert allowed(database, statement, [*config.CADENCES, "daily"]) == config.CADENCES


def test_money_columns_are_numeric_to_the_cent(database):
    with psycopg.connect(database, autocommit=True) as conn:
        columns = conn.execute("""
            select table_name || '.' || column_name, numeric_precision, numeric_scale
            from information_schema.columns
            where table_schema = 'public' and data_type = 'numeric'
            order by 1
        """).fetchall()
    assert columns == [("accounts.apr", 5, 2)] + [(name, 12, 2) for name in (
        "balances.amount", "bills.amount", "budgets.amount", "goals.target_amount",
        "transactions.amount")]


def test_a_budget_month_is_the_first_of_the_month(database):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("insert into categories (name, kind) values ('Food', 'expense')")
        conn.execute("insert into budgets (month, category_id, amount) "
                     "values ('2026-10-01', 1, 100)")
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("insert into budgets (month, category_id, amount) "
                         "values ('2026-10-14', 1, 100)")


def test_names_are_unique_whatever_the_capitalisation(database):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("insert into categories (name, kind) values ('Food', 'expense')")
        conn.execute("insert into accounts (name, kind) values ('Checking', 'checking')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("insert into categories (name, kind) values ('FOOD', 'expense')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("insert into accounts (name, kind) values ('checking', 'savings')")


# ---- accounts ---------------------------------------------------------------

TODAY = date(2026, 10, 14)


def test_an_account_is_added_edited_and_listed_with_its_latest_balance():
    checking = data.add_account(" Checking ", "checking", institution="", opened_on=TODAY)
    card = data.add_account("Card", "credit card", is_liability=True)
    data.save_balance(checking, date(2026, 10, 1), Decimal("100.00"))
    data.save_balance(checking, date(2026, 10, 10), Decimal("250.50"))
    data.save_balance(checking, date(2026, 10, 10), Decimal("260.50"))   # same day: replaced
    rows = data.accounts().set_index("account_id")
    assert rows.loc[checking, "name"] == "Checking" and rows.loc[checking, "institution"] is None
    assert rows.loc[checking, "balance"] == Decimal("260.50")
    assert rows.loc[checking, "balance_on"] == date(2026, 10, 10)
    assert rows.loc[checking, "balances"] == 2 and rows.loc[checking, "transactions"] == 0
    assert rows.loc[card, "balance"] is None and bool(rows.loc[card, "is_liability"])
    data.update_account(card, name="Visa", institution="Chase")
    assert data.account(card)["name"] == "Visa"
    with pytest.raises(ValueError):
        data.update_account(card, balance=1)
    with pytest.raises(ValueError):
        data.add_account("X", "cash", colour="blue")


def test_account_names_are_unique_whatever_the_capitalisation():
    data.add_account("Checking", "checking")
    with pytest.raises(psycopg.errors.UniqueViolation):
        data.add_account("checking", "savings")


def test_closing_keeps_history_and_leaves_the_open_list():
    checking = data.add_account("Checking", "checking")
    data.save_balance(checking, TODAY, Decimal("10"))
    data.close_account(checking, TODAY)
    assert data.open_accounts().empty
    assert data.account(checking)["closed_on"] == TODAY
    assert data.account(checking)["balance"] == Decimal("10.00")
    data.reopen_account(checking)
    assert data.open_accounts()["account_id"].tolist() == [checking]


def test_only_an_empty_account_can_be_deleted():
    checking = data.add_account("Checking", "checking")
    data.save_balance(checking, TODAY, Decimal("10"))
    with pytest.raises(data.InUse):
        data.delete_account(checking)
    empty = data.add_account("Wallet", "cash")
    data.delete_account(empty)
    assert data.accounts()["account_id"].tolist() == [checking]


def test_accounts_list_open_ones_first_then_by_name():
    zed = data.add_account("Zed", "savings")
    amy = data.add_account("Amy", "checking")
    old = data.add_account("Old", "checking")
    data.close_account(old, TODAY)
    assert data.accounts()["account_id"].tolist() == [amy, zed, old]


# ---- categories and transactions --------------------------------------------

def test_categories_list_expense_first_and_archived_ones_only_on_request():
    rent = data.add_category("Rent", "expense", sort_order=1)
    food = data.add_category("Food", "expense", sort_order=0)
    pay = data.add_category("Pay", "income")
    assert data.categories()["category_id"].tolist() == [food, rent, pay]
    data.archive_category(rent)
    assert data.categories()["category_id"].tolist() == [food, pay]
    assert data.categories(include_archived=True)["category_id"].tolist() == [food, rent, pay]
    data.archive_category(rent, archived=False)
    data.update_category(rent, name="Housing")
    assert data.categories()["name"].tolist() == ["Food", "Housing", "Pay"]
    with pytest.raises(psycopg.errors.UniqueViolation):
        data.add_category("food", "expense")
    with pytest.raises(ValueError):
        data.add_category("X", "expense", colour="red")


def seed_transactions() -> dict:
    checking = data.add_account("Checking", "checking")
    card = data.add_account("Visa", "credit card", is_liability=True)
    food = data.add_category("Food", "expense")
    pay = data.add_category("Pay", "income")
    rows = [
        (checking, date(2026, 10, 1), Decimal("2500.00"), "income", pay, "Employer"),
        (checking, date(2026, 10, 3), Decimal("-42.10"), "expense", food, "Grocer"),
        (card, date(2026, 10, 12), Decimal("-9.99"), "expense", None, "Streaming"),
        (checking, date(2026, 10, 12), Decimal("-200.00"), "transfer", None, None),
        (checking, date(2026, 9, 20), Decimal("-60.00"), "expense", food, "Grocer"),
    ]
    ids = [data.add_transaction(a, on, amount, kind, TODAY, category_id=c, payee=p)
           for a, on, amount, kind, c, p in rows]
    return {"checking": checking, "card": card, "food": food, "pay": pay, "ids": ids}


def test_transactions_are_newest_first_with_names_and_decimal_amounts():
    s = seed_transactions()
    rows = data.transactions()
    assert rows["transaction_id"].tolist() == [s["ids"][3], s["ids"][2], s["ids"][1],
                                               s["ids"][0], s["ids"][4]]
    first = rows.iloc[1]
    assert (first["account"], first["payee"]) == ("Visa", "Streaming") and logic.blank(first["category"])
    assert first["amount"] == Decimal("-9.99") and isinstance(first["amount"], Decimal)
    assert data.transaction_months() == [date(2026, 10, 1), date(2026, 9, 1)]


def test_transactions_are_filtered_by_month_account_category_and_text():
    s = seed_transactions()
    assert len(data.transactions(month=date(2026, 10, 1))) == 4
    assert len(data.transactions(month=date(2026, 9, 1))) == 1
    assert len(data.transactions(account_id=s["card"])) == 1
    assert len(data.transactions(category_id=s["food"])) == 2
    assert data.transactions(search=" grocer").shape[0] == 2
    assert data.transactions(month=date(2026, 10, 1), category_id=s["food"],
                             search="GROCER")["transaction_id"].tolist() == [s["ids"][1]]
    assert data.transactions(search="nothing").empty


def test_a_transaction_is_edited_and_deleted_and_keeps_its_account_from_deletion():
    s = seed_transactions()
    tx = s["ids"][1]
    data.update_transaction(tx, amount=Decimal("-45.00"), payee=" Market ", category_id=None)
    row = data.transaction(tx)
    assert (row["amount"], row["payee"], row["category"]) == (Decimal("-45.00"), "Market", None)
    with pytest.raises(ValueError):
        data.update_transaction(tx, created_on=TODAY)
    with pytest.raises(data.InUse):
        data.delete_account(s["card"])
    for tx_id in s["ids"]:
        data.delete_transaction(tx_id)
    assert data.transactions().empty and data.transaction_months() == []
    data.delete_account(s["card"])


def test_archiving_a_category_keeps_its_transactions():
    s = seed_transactions()
    data.archive_category(s["food"])
    assert data.transaction(s["ids"][1])["category"] == "Food"


# ---- budgets ----------------------------------------------------------------

OCT, SEP, NOV = date(2026, 10, 1), date(2026, 9, 1), date(2026, 11, 1)


def test_budgets_show_every_expense_category_with_spending_for_the_month():
    s = seed_transactions()
    rent = data.add_category("Rent", "expense")
    data.set_budget(OCT, s["food"], "100")
    rows = data.budgets(OCT).set_index("category_id")
    assert rows.index.tolist() == [s["food"], rent]             # income categories stay out
    assert rows.loc[s["food"], "budgeted"] == Decimal("100.00")
    assert rows.loc[s["food"], "spent"] == Decimal("42.10")      # October only, as a positive
    assert logic.blank(rows.loc[rent, "budgeted"]) and rows.loc[rent, "spent"] == 0
    assert data.budgets(SEP).loc[lambda f: f["category_id"] == s["food"], "spent"].iloc[0] \
        == Decimal("60.00")


def test_a_budget_is_saved_over_and_cleared_by_zero_or_blank():
    food = data.add_category("Food", "expense")
    data.set_budget(OCT, food, Decimal("100"))
    data.set_budget(OCT, food, 150.0)
    assert data.budgets(OCT)["budgeted"].tolist() == [Decimal("150.00")]
    data.set_budget(OCT, food, 0)
    assert data.budgets(OCT)["budget_id"].isna().all()
    data.set_budget(OCT, food, "80")
    data.set_budget(OCT, food, None)
    assert data.budget_months() == []


def test_copy_last_month_fills_only_what_is_missing():
    food = data.add_category("Food", "expense")
    rent = data.add_category("Rent", "expense")
    data.set_budget(SEP, food, "100")
    data.set_budget(SEP, rent, "900")
    data.set_budget(OCT, rent, "950")
    assert data.copy_budgets(SEP, OCT) == 1
    rows = data.budgets(OCT).set_index("category_id")
    assert rows.loc[food, "budgeted"] == Decimal("100.00")
    assert rows.loc[rent, "budgeted"] == Decimal("950.00")      # kept
    assert data.copy_budgets(SEP, NOV) == 2
    assert data.budget_months() == [NOV, OCT, SEP]


def test_an_archived_category_keeps_its_budget_but_a_deleted_month_row_goes_with_it():
    food = data.add_category("Food", "expense")
    data.set_budget(OCT, food, "100")
    data.archive_category(food)
    rows = data.budgets(OCT)
    assert bool(rows.iloc[0]["archived"]) and rows.iloc[0]["budgeted"] == Decimal("100.00")


# ---- bills ------------------------------------------------------------------

def test_bills_are_listed_soonest_first_with_paused_ones_last():
    checking = data.add_account("Checking", "checking")
    rent = data.add_bill("Rent", "1200", "monthly", date(2026, 11, 1), account_id=checking)
    phone = data.add_bill(" Phone ", Decimal("45.50"), "monthly", date(2026, 10, 20), autopay=True)
    gym = data.add_bill("Gym", "30", "monthly", date(2026, 10, 15), active=False)
    rows = data.bills()
    assert rows["bill_id"].tolist() == [phone, rent, gym]
    assert rows.iloc[0]["name"] == "Phone" and rows.iloc[0]["amount"] == Decimal("45.50")
    assert rows.iloc[1]["account"] == "Checking" and bool(rows.iloc[0]["autopay"])
    assert data.bills(active_only=True)["bill_id"].tolist() == [phone, rent]
    data.update_bill(gym, active=True, amount="35")
    assert data.bill(gym)["amount"] == Decimal("35.00")
    with pytest.raises(ValueError):
        data.add_bill("X", "1", "monthly", TODAY, colour="red")
    data.delete_bill(gym)
    assert len(data.bills()) == 2


def test_marking_paid_moves_the_date_and_logs_the_payment_together():
    checking = data.add_account("Checking", "checking")
    rent_cat = data.add_category("Housing", "expense")
    rent = data.add_bill("Rent", "1200", "monthly", date(2026, 10, 1), account_id=checking,
                         category_id=rent_cat)
    tx_id = data.mark_bill_paid(rent, TODAY, True, TODAY)
    assert data.bill(rent)["next_due_on"] == date(2026, 11, 1)
    tx = data.transaction(tx_id)
    assert (tx["amount"], tx["kind"], tx["payee"], tx["category"], tx["happened_on"]) == (
        Decimal("-1200.00"), "expense", "Rent", "Housing", TODAY)
    assert data.mark_bill_paid(rent, TODAY, False, TODAY) is None
    assert data.bill(rent)["next_due_on"] == date(2026, 12, 1)
    assert len(data.transactions()) == 1


def test_marking_paid_without_an_account_cannot_log_and_changes_nothing():
    phone = data.add_bill("Phone", "45", "monthly", date(2026, 10, 20))
    with pytest.raises(ValueError):
        data.mark_bill_paid(phone, TODAY, True, TODAY)
    assert data.bill(phone)["next_due_on"] == date(2026, 10, 20)      # rolled back
    assert data.transactions().empty
    data.mark_bill_paid(phone, TODAY, False, TODAY)
    assert data.bill(phone)["next_due_on"] == date(2026, 11, 20)


def test_deleting_an_account_or_category_leaves_the_bill():
    wallet = data.add_account("Wallet", "cash")
    fun = data.add_category("Fun", "expense")
    gym = data.add_bill("Gym", "30", "monthly", TODAY, account_id=wallet, category_id=fun)
    data.delete_account(wallet)
    assert data.bill(gym)["account_id"] is None


# ---- balances ---------------------------------------------------------------

def test_saving_several_balances_at_once_is_all_or_nothing():
    checking = data.add_account("Checking", "checking")
    card = data.add_account("Visa", "credit card", is_liability=True)
    assert data.save_balances([(checking, 1250.0), (card, None), (card, "430.25")], TODAY) == 2
    rows = data.balances()
    assert rows[["account", "amount"]].values.tolist() == [["Checking", Decimal("1250.00")],
                                                           ["Visa", Decimal("430.25")]]
    assert bool(rows.iloc[1]["is_liability"]) and logic.blank(rows.iloc[1]["closed_on"])
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        data.save_balances([(checking, 1), (999, 1)], date(2026, 10, 15))
    assert len(data.balances()) == 2                             # nothing from the failed run


# ---- goals ------------------------------------------------------------------

def test_goals_carry_their_accounts_latest_balance_and_list_open_ones_first():
    savings = data.add_account("Savings", "savings")
    data.save_balance(savings, date(2026, 9, 1), Decimal("100"))
    data.save_balance(savings, date(2026, 10, 1), Decimal("250"))
    trip = data.add_goal("Trip", "1000", target_on=date(2027, 6, 1), account_id=savings)
    fund = data.add_goal(" Fund ", Decimal("5000"), target_on=date(2027, 1, 1), account_id=savings)
    car = data.add_goal("Car", "20000")
    done_goal = data.add_goal("Done", "10", reached_on=TODAY)
    rows = data.goals()
    assert rows["goal_id"].tolist() == [fund, trip, car, done_goal]
    assert rows.iloc[0]["name"] == "Fund" and rows.iloc[0]["balance"] == Decimal("250.00")
    assert rows.iloc[0]["balance_on"] == date(2026, 10, 1) and rows.iloc[0]["account"] == "Savings"
    assert logic.blank(rows.iloc[2]["balance"]) and logic.blank(rows.iloc[2]["account"])
    data.update_goal(car, account_id=savings, target_amount="15000")
    assert data.goal(car)["target_amount"] == Decimal("15000.00")
    with pytest.raises(ValueError):
        data.update_goal(car, balance=1)
    with pytest.raises(ValueError):
        data.add_goal("X", "1", colour="red")
    data.delete_goal(done_goal)
    assert len(data.goals()) == 3


def test_deleting_the_account_leaves_the_goal_without_one():
    wallet = data.add_account("Wallet", "cash")
    goal_id = data.add_goal("Trip", "100", account_id=wallet)
    data.delete_account(wallet)
    assert data.goal(goal_id)["account_id"] is None


def test_transactions_since_a_date():
    s = seed_transactions()
    assert len(data.transactions(since=date(2026, 10, 1))) == 4
    assert data.transactions(since=date(2026, 10, 12))["transaction_id"].tolist() == [
        s["ids"][3], s["ids"][2]]


# ---- import -----------------------------------------------------------------

def test_importing_the_same_file_twice_adds_nothing():
    checking = data.add_account("Checking", "checking")
    rows, _ = logic.map_import(logic.read_csv(
        "Date,Description,Amount\n2026-10-12,CAFE #12,-4.50\n2026-10-01,PAYROLL,2500\n"), checking)
    assert data.import_transactions(rows, TODAY) == (2, 0)
    assert data.import_transactions(rows, TODAY) == (0, 2)
    stored = data.transactions()
    assert stored["payee"].tolist() == ["CAFE #12", "PAYROLL"]
    assert stored["import_key"].tolist()[0] == f"{checking}|2026-10-12|-4.50|cafe 12"
    assert stored["created_on"].tolist() == [TODAY, TODAY]
    assert data.known_import_keys([r["import_key"] for r in rows] + ["x"]) == {
        r["import_key"] for r in rows}
    assert data.known_import_keys([]) == set()


def test_an_import_is_all_or_nothing():
    checking = data.add_account("Checking", "checking")
    rows, _ = logic.map_import(logic.read_csv(
        "Date,Description,Amount\n2026-10-12,A,-1\n2026-10-13,B,-2\n"), checking)
    rows[1]["account_id"] = 999                                # breaks on the second row
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        data.import_transactions(rows, TODAY)
    assert data.transactions().empty


def test_an_accounts_apr_is_saved_and_the_live_database_gains_the_column(database):
    card = data.add_account("Visa", "credit card", is_liability=True, apr="22.99")
    assert data.account(card)["apr"] == Decimal("22.99")
    data.update_account(card, apr=None)
    assert data.account(card)["apr"] is None
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("alter table accounts drop column apr")
    data.migrate()
    data.update_account(card, apr=Decimal("19.5"))
    assert data.account(card)["apr"] == Decimal("19.50")
