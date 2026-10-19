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
