"""data.py against a real (throwaway) Postgres with the real schema."""

import psycopg
import pytest

import apply_schema
import config
import data


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
    assert columns == [(name, 12, 2) for name in (
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
