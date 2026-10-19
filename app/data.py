"""Every database read and write the app makes.

Reads return DataFrames (or a dict for one row). Writes take plain Python
values; dates are computed in Python ("today" comes from today() below, in
America/Chicago) and passed in, never current_date or now() in SQL. Money
comes back from Postgres as Decimal, and goes in as Decimal: never float.

One connection per process, in autocommit, shared by every page. Neon
suspends idle databases, so a connection idle for PING_AFTER_IDLE_S or more
is pinged before use and replaced if it has died. The first connection a
process opens also runs schema.sql -- every statement in it is "if not
exists" -- so a brand-new database gets its tables the first time the app
opens, with nothing to run by hand.
"""

import sys
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db  # noqa: E402
import logic  # noqa: E402

PING_AFTER_IDLE_S = 20

_lock = threading.RLock()
_conn: psycopg.Connection | None = None
_last_used = 0.0
_schema_ready = False


class InUse(Exception):
    """A delete refused because other rows still point at this one."""


def today() -> date:
    return datetime.now(db.LOCAL_TZ).date()


# ---- connection -------------------------------------------------------------

# Changes to tables that already existed on the live database, each safe to
# run again (schema.sql only creates what's missing). _connection() runs them
# after schema.sql. Add one whenever an existing table changes.
MIGRATIONS: list[str] = []


def _connection() -> psycopg.Connection:
    global _conn, _last_used, _schema_ready
    if _conn is None or _conn.closed:
        _conn = db.connect(autocommit=True)
        if not _schema_ready:
            _conn.execute((ROOT / "schema.sql").read_text(encoding="utf-8"))
            for statement in MIGRATIONS:
                _conn.execute(statement)
            _schema_ready = True
    elif time.monotonic() - _last_used >= PING_AFTER_IDLE_S:
        try:
            _conn.execute("select 1")
        except psycopg.Error:
            reset_connection()
            _conn = db.connect(autocommit=True)
    _last_used = time.monotonic()
    return _conn


def reset_connection() -> None:
    """Drop the shared connection; the next call opens a fresh one."""
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except psycopg.Error:
            pass
    _conn = None


_over_http = False


def use_http() -> None:
    """Send every query over Neon's HTTPS endpoint (db.HttpCursor) instead of
    a Postgres connection: for a scheduled cloud session, which can't open
    one. Statements then commit one at a time, and schema.sql isn't run (the
    app has made the tables)."""
    global _over_http
    _over_http = True


@contextmanager
def _cursor(row_factory=None):
    if _over_http:
        yield db.HttpCursor(row_factory)
        return
    with _lock:
        conn = _connection()
        with conn.cursor(row_factory=row_factory) as cur:
            yield cur


@contextmanager
def _transaction():
    """All-or-nothing: every statement inside commits together or not at all.
    Nests (as a savepoint) inside another _transaction(). Over HTTPS each
    statement commits on its own."""
    if _over_http:
        yield db.HttpCursor()
        return
    with _lock:
        conn = _connection()
        with conn.transaction(), conn.cursor() as cur:
            yield cur


def migrate() -> None:
    """Bring an existing database's tables up to date (MIGRATIONS), for the
    HTTPS path, which never runs schema.sql."""
    with _cursor() as cur:
        for statement in MIGRATIONS:
            cur.execute(statement)


def _read(query: str, params=None) -> pd.DataFrame:
    with _cursor() as cur:
        cur.execute(query, params)
        columns = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def _one(query: str, params=None) -> dict | None:
    with _cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def _clean(value):
    """Strip text; blank text becomes NULL."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _insert(table: str, key: str, fields: dict) -> int:
    cleaned = {k: _clean(v) for k, v in fields.items()}
    query = sql.SQL("insert into {} ({}) values ({}) returning {}").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, cleaned)),
        sql.SQL(", ").join(map(sql.Placeholder, cleaned)),
        sql.Identifier(key),
    )
    with _cursor() as cur:
        cur.execute(query, cleaned)
        return cur.fetchone()[0]


def _update(table: str, key: str, key_value: int, fields: dict, allowed: set[str]) -> None:
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"cannot update {sorted(unknown)} on {table}")
    if not fields:
        return
    cleaned = {k: _clean(v) for k, v in fields.items()}
    query = sql.SQL("update {} set {} where {} = {}").format(
        sql.Identifier(table),
        sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k)) for k in cleaned
        ),
        sql.Identifier(key),
        sql.Placeholder("_key"),
    )
    with _cursor() as cur:
        cur.execute(query, {**cleaned, "_key": key_value})


def _delete(table: str, key: str, key_value: int, in_use_message: str = "") -> None:
    query = sql.SQL("delete from {} where {} = %s").format(
        sql.Identifier(table), sql.Identifier(key))
    try:
        with _cursor() as cur:
            cur.execute(query, (key_value,))
    except psycopg.errors.IntegrityError as exc:
        # ForeignKeyViolation or RestrictViolation, depending on the Postgres version.
        raise InUse(in_use_message or "other records still use this one") from exc


# ---- accounts ---------------------------------------------------------------

ACCOUNT_FIELDS = {"name", "kind", "institution", "is_liability", "opened_on", "closed_on",
                  "notes"}

_ACCOUNTS = """
    select a.*, b.amount as balance, b.as_of as balance_on,
           (select count(*) from transactions t where t.account_id = a.account_id)
               as transactions,
           (select count(*) from balances x where x.account_id = a.account_id) as balances
    from accounts a
    left join lateral (select amount, as_of from balances b
                       where b.account_id = a.account_id
                       order by as_of desc limit 1) b on true
"""


def accounts() -> pd.DataFrame:
    """Every account, open ones first then by name, with its latest balance
    (and the day it was taken) and how many transactions and balances it has."""
    return _read(_ACCOUNTS + " order by a.closed_on is not null, lower(a.name)")


def open_accounts() -> pd.DataFrame:
    return _read(_ACCOUNTS + " where a.closed_on is null order by lower(a.name)")


def account(account_id: int) -> dict | None:
    return _one(_ACCOUNTS + " where a.account_id = %s", (account_id,))


def add_account(name: str, kind: str, **fields) -> int:
    unknown = set(fields) - ACCOUNT_FIELDS
    if unknown:
        raise ValueError(f"unknown account fields {sorted(unknown)}")
    return _insert("accounts", "account_id", {"name": name, "kind": kind, **fields})


def update_account(account_id: int, **fields) -> None:
    _update("accounts", "account_id", account_id, fields, ACCOUNT_FIELDS)


def close_account(account_id: int, on: date) -> None:
    """Closed accounts keep their history and drop out of pickers and net worth."""
    _update("accounts", "account_id", account_id, {"closed_on": on}, ACCOUNT_FIELDS)


def reopen_account(account_id: int) -> None:
    _update("accounts", "account_id", account_id, {"closed_on": None}, ACCOUNT_FIELDS)


def delete_account(account_id: int) -> None:
    """Only an account with no transactions and no balances; close the others."""
    _delete("accounts", "account_id", account_id,
            "this account has transactions or balances; close it instead")


# ---- categories -------------------------------------------------------------

CATEGORY_FIELDS = {"name", "kind", "archived", "sort_order"}


def categories(include_archived: bool = False) -> pd.DataFrame:
    """Categories in picker order: expense ones first, then by sort order and name."""
    where = "" if include_archived else "where not archived"
    return _read(f"""
        select * from categories {where}
        order by kind, sort_order, lower(name)
    """)


def add_category(name: str, kind: str, **fields) -> int:
    unknown = set(fields) - CATEGORY_FIELDS
    if unknown:
        raise ValueError(f"unknown category fields {sorted(unknown)}")
    return _insert("categories", "category_id", {"name": name, "kind": kind, **fields})


def update_category(category_id: int, **fields) -> None:
    _update("categories", "category_id", category_id, fields, CATEGORY_FIELDS)


def archive_category(category_id: int, archived: bool = True) -> None:
    """Archived categories leave the pickers; their transactions and budgets stay."""
    _update("categories", "category_id", category_id, {"archived": archived}, CATEGORY_FIELDS)


# ---- transactions -----------------------------------------------------------

TRANSACTION_FIELDS = {"account_id", "happened_on", "amount", "kind", "category_id", "payee",
                      "notes"}

_TRANSACTIONS = """
    select t.*, a.name as account, c.name as category
    from transactions t
    join accounts a using (account_id)
    left join categories c using (category_id)
"""


def transactions(month: date | None = None, account_id: int | None = None,
                 category_id: int | None = None, search: str | None = None) -> pd.DataFrame:
    """Transactions newest first, with account and category names, narrowed
    by any of: a month (its first day), an account, a category, and text in
    the payee or notes."""
    where, params = [], {}
    if month is not None:
        where.append("t.happened_on >= %(start)s and t.happened_on < %(end)s")
        params.update(start=month, end=logic.add_months(month, 1))
    if account_id is not None:
        where.append("t.account_id = %(account_id)s")
        params["account_id"] = account_id
    if category_id is not None:
        where.append("t.category_id = %(category_id)s")
        params["category_id"] = category_id
    if search and search.strip():
        where.append("(t.payee ilike %(search)s or t.notes ilike %(search)s)")
        params["search"] = f"%{search.strip()}%"
    clause = f"where {' and '.join(where)}" if where else ""
    return _read(_TRANSACTIONS + f" {clause} order by t.happened_on desc, t.transaction_id desc",
                 params)


def transaction(transaction_id: int) -> dict | None:
    return _one(_TRANSACTIONS + " where t.transaction_id = %s", (transaction_id,))


def transaction_months() -> list[date]:
    """The first day of every month with a transaction, newest first."""
    with _cursor() as cur:
        cur.execute("""
            select distinct date_trunc('month', happened_on)::date from transactions
            order by 1 desc
        """)
        return [row[0] for row in cur.fetchall()]


def add_transaction(account_id: int, happened_on: date, amount, kind: str, on: date,
                    **fields) -> int:
    """A transaction, dated `on` as created. The amount is stored as given
    (signed: income positive, spending negative; logic.signed sorts that out
    from what was typed)."""
    unknown = set(fields) - TRANSACTION_FIELDS
    if unknown:
        raise ValueError(f"unknown transaction fields {sorted(unknown)}")
    return _insert("transactions", "transaction_id", {
        "account_id": account_id, "happened_on": happened_on, "amount": amount,
        "kind": kind, "created_on": on, **fields})


def update_transaction(transaction_id: int, **fields) -> None:
    _update("transactions", "transaction_id", transaction_id, fields, TRANSACTION_FIELDS)


def delete_transaction(transaction_id: int) -> None:
    _delete("transactions", "transaction_id", transaction_id)


# ---- budgets ----------------------------------------------------------------

def budgets(month: date) -> pd.DataFrame:
    """Every active expense category for a month (its first day), with what
    was budgeted (None when nothing yet) and what was spent, as a positive
    number. Archived categories appear only when they have a budget or
    spending that month."""
    return _read("""
        select c.category_id, c.name, c.archived, c.sort_order, b.budget_id, b.amount as budgeted,
               coalesce((select -sum(t.amount) from transactions t
                         where t.category_id = c.category_id and t.kind = 'expense'
                           and t.happened_on >= %(start)s and t.happened_on < %(end)s), 0)
                   as spent
        from categories c
        left join budgets b on b.category_id = c.category_id and b.month = %(start)s
        where c.kind = 'expense'
        order by c.archived, c.sort_order, lower(c.name)
    """, {"start": month, "end": logic.add_months(month, 1)})


def set_budget(month: date, category_id: int, amount) -> None:
    """The budget for a category in a month (its first day): saved over, or
    removed when the amount is None or zero."""
    amount = logic.to_money(amount)
    with _cursor() as cur:
        if amount is None or amount == 0:
            cur.execute("delete from budgets where month = %s and category_id = %s",
                        (month, category_id))
        else:
            cur.execute("""
                insert into budgets (month, category_id, amount) values (%s, %s, %s)
                on conflict (month, category_id) do update set amount = excluded.amount
            """, (month, category_id, amount))


def copy_budgets(from_month: date, to_month: date) -> int:
    """Last month's budgets into a month that has none yet, all or nothing;
    how many were copied. Categories already budgeted in `to_month` are
    left as they are."""
    with _transaction() as cur:
        cur.execute("""
            insert into budgets (month, category_id, amount)
            select %(to)s, category_id, amount from budgets where month = %(from)s
            on conflict (month, category_id) do nothing
        """, {"from": from_month, "to": to_month})
        return cur.rowcount


def budget_months() -> list[date]:
    """The first day of every month with a budget, newest first."""
    with _cursor() as cur:
        cur.execute("select distinct month from budgets order by 1 desc")
        return [row[0] for row in cur.fetchall()]


# ---- bills ------------------------------------------------------------------

BILL_FIELDS = {"name", "amount", "cadence", "next_due_on", "account_id", "autopay",
               "category_id", "active", "notes"}

_BILLS = """
    select b.*, a.name as account, c.name as category
    from bills b
    left join accounts a using (account_id)
    left join categories c using (category_id)
"""


def bills(active_only: bool = False) -> pd.DataFrame:
    """Bills soonest due first, with their account and category names;
    paused (inactive) ones last, or left out."""
    where = "where b.active" if active_only else ""
    return _read(_BILLS + f" {where} order by b.active desc, b.next_due_on, lower(b.name)")


def bill(bill_id: int) -> dict | None:
    return _one(_BILLS + " where b.bill_id = %s", (bill_id,))


def add_bill(name: str, amount, cadence: str, next_due_on: date, **fields) -> int:
    unknown = set(fields) - BILL_FIELDS
    if unknown:
        raise ValueError(f"unknown bill fields {sorted(unknown)}")
    return _insert("bills", "bill_id", {"name": name, "amount": amount, "cadence": cadence,
                                        "next_due_on": next_due_on, **fields})


def update_bill(bill_id: int, **fields) -> None:
    _update("bills", "bill_id", bill_id, fields, BILL_FIELDS)


def delete_bill(bill_id: int) -> None:
    _delete("bills", "bill_id", bill_id)


def mark_bill_paid(bill_id: int, paid_on: date, log_transaction: bool, on: date) -> int | None:
    """Move the bill's due date on by one cadence and, when asked, log the
    payment as an expense on its account, both together or neither. The new
    transaction's id, or None."""
    row = bill(bill_id)
    with _transaction() as cur:
        cur.execute("update bills set next_due_on = %s where bill_id = %s",
                    (logic.next_due(row["next_due_on"], row["cadence"]), bill_id))
        if not log_transaction:
            return None
        if row["account_id"] is None:
            raise ValueError("the bill has no account to log the payment against")
        return add_transaction(row["account_id"], paid_on, logic.signed(row["amount"], "expense"),
                               "expense", on, category_id=row["category_id"], payee=row["name"],
                               notes="Bill marked paid")


# ---- balances ---------------------------------------------------------------

def save_balance(account_id: int, as_of: date, amount) -> None:
    """An account's balance on a day, as the bank shows it (what's owed on a
    card or loan is positive); a second entry for the same day replaces the
    first."""
    with _cursor() as cur:
        cur.execute("""
            insert into balances (account_id, as_of, amount) values (%s, %s, %s)
            on conflict (account_id, as_of) do update set amount = excluded.amount
        """, (account_id, as_of, amount))


# ---- settings ---------------------------------------------------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    """A saved app setting (e.g. "theme"), or the default when unset."""
    row = _one("select value from settings where key = %s", (key,))
    return default if row is None else row["value"]


def set_setting(key: str, value: str) -> None:
    with _cursor() as cur:
        cur.execute("""
            insert into settings (key, value) values (%s, %s)
            on conflict (key) do update set value = excluded.value
        """, (key, value))
