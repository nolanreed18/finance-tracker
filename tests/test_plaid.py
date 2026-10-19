"""The bank feed: Plaid's shapes into our rows (logic), the thin client with
Plaid faked (plaid_api), the connection tables (data), and a whole sync run
against the throwaway database (sync.py)."""

import io
import json
import urllib.error
from datetime import date
from decimal import Decimal

import pytest

import data
import logic
import plaid_api
import sync

TODAY = date(2026, 10, 14)


def tx(**fields) -> dict:
    base = {"transaction_id": "t1", "account_id": "pa-card", "amount": 4.5, "date": "2026-10-12",
            "name": "CAFE #12", "merchant_name": "Cafe 12", "pending": False,
            "personal_finance_category": {"primary": "FOOD_AND_DRINK",
                                          "detailed": "FOOD_AND_DRINK_COFFEE"}}
    return {**base, **fields}


ACCOUNTS = {"pa-card": (2, True), "pa-checking": (1, False)}


# ---- logic ------------------------------------------------------------------

def test_plaid_rows_negate_amounts_and_skip_pending_and_unmatched():
    rows, skipped = logic.plaid_rows([
        tx(),
        tx(transaction_id="t2", pending=True),
        tx(transaction_id="t3", account_id="pa-unknown"),
    ], ACCOUNTS)
    assert skipped == ["t2", "t3"]
    assert rows == [{
        "account_id": 2, "happened_on": date(2026, 10, 12), "amount": Decimal("-4.50"),
        "kind": "expense", "payee": "Cafe 12", "source_category": "FOOD_AND_DRINK_COFFEE",
        "import_key": "plaid:t1", "file_key": "2|2026-10-12|-4.50|cafe 12",
    }]


def test_plaid_kinds_follow_the_category_then_the_sign():
    rows, _ = logic.plaid_rows([
        tx(transaction_id="pay", amount=-250, name="PAYMENT THANK YOU", merchant_name=None,
           personal_finance_category={"primary": "LOAN_PAYMENTS", "detailed": "X"}),
        tx(transaction_id="out", account_id="pa-checking", amount=250, name="CHASE CARD PAYMENT",
           personal_finance_category={"primary": "LOAN_PAYMENTS", "detailed": "X"}),
        tx(transaction_id="pay2", amount=-250, name="PAYMENT - THANK YOU", merchant_name=None,
           personal_finance_category=None),
        tx(transaction_id="refund", amount=-12, name="STORE RETURN",
           personal_finance_category={"primary": "GENERAL_MERCHANDISE", "detailed": "Y"}),
        tx(transaction_id="salary", account_id="pa-checking", amount=-2500, name="PAYROLL",
           personal_finance_category={"primary": "INCOME", "detailed": "INCOME_WAGES"}),
        tx(transaction_id="save", account_id="pa-checking", amount=200, name="To savings",
           personal_finance_category={"primary": "TRANSFER_OUT", "detailed": "Z"}),
    ], ACCOUNTS)
    assert [(r["import_key"], r["amount"], r["kind"]) for r in rows] == [
        ("plaid:pay", Decimal("250.00"), "transfer"),
        ("plaid:out", Decimal("-250.00"), "transfer"),
        ("plaid:pay2", Decimal("250.00"), "transfer"),       # by the payment words
        ("plaid:refund", Decimal("12.00"), "expense"),       # a refund stays spending
        ("plaid:salary", Decimal("2500.00"), "income"),
        ("plaid:save", Decimal("-200.00"), "transfer"),
    ]
    assert rows[2]["source_category"] is None and rows[2]["payee"] == "PAYMENT - THANK YOU"


def test_plaid_balance_prefers_current():
    assert logic.plaid_balance({"balances": {"current": 430.25, "available": 9000}}) \
        == Decimal("430.25")
    assert logic.plaid_balance({"balances": {"current": None, "available": "12.1"}}) \
        == Decimal("12.10")
    assert logic.plaid_balance({"balances": {}}) is None and logic.plaid_balance({}) is None


# ---- plaid_api, with Plaid faked --------------------------------------------

@pytest.fixture
def plaid(monkeypatch):
    """A fake Plaid: replies keyed by path, calls recorded."""
    monkeypatch.setenv("PLAID_CLIENT_ID", "id")
    monkeypatch.setenv("PLAID_SECRET", "secret")
    calls = []
    replies: dict[str, list] = {}

    def post(path, **body):
        calls.append((path, body))
        queue = replies[path]
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(plaid_api, "post", post)
    post.calls, post.replies = calls, replies
    return post


def test_transactions_sync_follows_the_pages(plaid):
    plaid.replies["/transactions/sync"] = [
        {"added": [tx()], "modified": [], "removed": [], "next_cursor": "c1", "has_more": True},
        {"added": [tx(transaction_id="t2")], "modified": [tx(transaction_id="t1", amount=5)],
         "removed": [{"transaction_id": "t0"}], "next_cursor": "c2", "has_more": False},
    ]
    changes = plaid_api.transactions_sync("tok", None)
    assert [t["transaction_id"] for t in changes["added"]] == ["t1", "t2"]
    assert changes["removed"] == ["t0"] and changes["next_cursor"] == "c2"
    assert len(changes["modified"]) == 1
    assert [c[1]["cursor"] for c in plaid.calls] == ["", "c1"]
    assert plaid.calls[0][1]["options"] == {"include_personal_finance_category": True}


def test_link_results_and_exchange(plaid):
    plaid.replies["/link/token/create"] = [{"link_token": "lt", "hosted_link_url": "https://x"}]
    plaid.replies["/link/token/get"] = [{"link_sessions": [{"results": {"item_add_results": [
        {"public_token": "pub", "institution": {"name": "Chase", "institution_id": "ins_3"}}]}}]}]
    plaid.replies["/item/public_token/exchange"] = [{"access_token": "acc", "item_id": "item"}]
    assert plaid_api.create_link("me") == {"link_token": "lt", "hosted_link_url": "https://x"}
    body = plaid.calls[0][1]
    assert body["products"] == ["transactions"] and body["hosted_link"] == {}
    assert body["transactions"] == {"days_requested": plaid_api.HISTORY_DAYS}
    assert plaid_api.link_results("lt") == [
        {"public_token": "pub", "institution_name": "Chase", "institution_id": "ins_3"}]
    assert plaid_api.exchange("pub") == {"access_token": "acc", "item_id": "item"}
    plaid_api.create_link("me", access_token="acc")              # repair mode
    assert "products" not in plaid.calls[-1][1] and plaid.calls[-1][1]["access_token"] == "acc"


def test_accounts_are_shaped_for_the_tables(plaid):
    plaid.replies["/accounts/get"] = [{"accounts": [
        {"account_id": "pa", "name": "Plat Card", "official_name": "Platinum Card", "mask": "1234",
         "type": "credit", "subtype": "credit card", "balances": {"current": 430.25}}]}]
    assert plaid_api.accounts("tok") == [
        {"provider_account_id": "pa", "name": "Platinum Card", "mask": "1234", "kind": "credit",
         "subtype": "credit card", "balances": {"current": 430.25}}]


def test_a_plaid_error_is_raised_with_its_code(monkeypatch):
    monkeypatch.setenv("PLAID_CLIENT_ID", "id")
    monkeypatch.setenv("PLAID_SECRET", "secret")
    body = json.dumps({"error_type": "ITEM_ERROR", "error_code": "ITEM_LOGIN_REQUIRED",
                       "error_message": "the login details of this item have changed",
                       "display_message": "Please sign in to your bank again."}).encode()

    def urlopen(request, timeout):
        assert "secret" not in request.full_url
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO(body))

    monkeypatch.setattr(plaid_api.urllib.request, "urlopen", urlopen)
    with pytest.raises(plaid_api.PlaidError) as caught:
        plaid_api.accounts("tok")
    assert caught.value.error_code == "ITEM_LOGIN_REQUIRED"
    assert str(caught.value) == "Please sign in to your bank again."


def test_without_credentials_plaid_is_not_configured(monkeypatch):
    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)
    monkeypatch.delenv("PLAID_SECRET", raising=False)
    assert not plaid_api.configured()
    with pytest.raises(RuntimeError):
        plaid_api.post("/accounts/get")


# ---- data -------------------------------------------------------------------

@pytest.fixture
def linked(database):
    checking = data.add_account("Checking", "checking")
    card = data.add_account("Visa", "credit card", is_liability=True)
    conn = data.add_connection("item-1", "access-1", TODAY, institution_name="Chase")
    data.save_connected_accounts(conn, [
        {"provider_account_id": "pa-checking", "name": "Total Checking", "mask": "0001",
         "kind": "depository", "subtype": "checking"},
        {"provider_account_id": "pa-card", "name": "Freedom", "mask": "0002", "kind": "credit",
         "subtype": "credit card"},
    ])
    found = data.connected_accounts(conn).set_index("provider_account_id")
    data.match_connected_account(int(found.loc["pa-checking", "connected_account_id"]), checking)
    data.match_connected_account(int(found.loc["pa-card", "connected_account_id"]), card)
    return {"conn": conn, "checking": checking, "card": card}


def test_connections_list_without_tokens_and_count_matches(linked):
    rows = data.connections()
    assert "access_token" not in rows.columns
    assert rows.iloc[0][["institution_name", "accounts", "matched"]].tolist() == ["Chase", 2, 2]
    assert data.connection(linked["conn"])["access_token"] == "access-1"
    data.save_connected_accounts(linked["conn"], [
        {"provider_account_id": "pa-card", "name": "Freedom Unlimited", "mask": "0002",
         "kind": "credit", "subtype": "credit card"},
        {"provider_account_id": "pa-new", "name": "Savings", "mask": "0003",
         "kind": "depository", "subtype": "savings"},
    ])
    accounts = data.connected_accounts(linked["conn"]).set_index("provider_account_id")
    assert accounts.loc["pa-card", "name"] == "Freedom Unlimited"
    assert accounts.loc["pa-card", "account_id"] == linked["card"]           # the match survives
    assert logic.blank(accounts.loc["pa-new", "account_id"])
    assert data.connections().iloc[0][["accounts", "matched"]].tolist() == [3, 2]
    with pytest.raises(ValueError):
        data.update_connection(linked["conn"], access_token="x")           # never edited
    data.delete_connection(linked["conn"])
    assert data.connections().empty and data.connected_accounts().empty
    assert len(data.accounts()) == 2                                        # ours stay


def test_apply_sync_adds_updates_removes_and_never_duplicates(linked):
    rows, _ = logic.plaid_rows([tx(), tx(transaction_id="t2", amount=-2500, name="PAYROLL",
                                        account_id="pa-checking",
                                        personal_finance_category={"primary": "INCOME",
                                                                   "detailed": "INCOME_WAGES"})],
                               {"pa-card": (linked["card"], True),
                                "pa-checking": (linked["checking"], False)})
    assert data.apply_sync(rows, [], [], TODAY) == {"added": 2, "skipped": 0, "modified": 0,
                                                    "removed": 0}
    assert data.apply_sync(rows, [], [], TODAY)["skipped"] == 2        # the same feed again
    stored = data.transactions().set_index("import_key")
    assert stored.loc["plaid:t1", "amount"] == Decimal("-4.50")
    assert stored.loc["plaid:t1", "source_category"] == "FOOD_AND_DRINK_COFFEE"
    assert stored.loc["plaid:t2", "kind"] == "income"
    changed, _ = logic.plaid_rows([tx(amount=5.5, name="CAFE #12 TIP")],
                                  {"pa-card": (linked["card"], True)})
    counts = data.apply_sync([], changed, ["plaid:t2", "plaid:nope"], TODAY)
    assert counts == {"added": 0, "skipped": 0, "modified": 1, "removed": 1}
    stored = data.transactions().set_index("import_key")
    assert stored.index.tolist() == ["plaid:t1"] and stored.loc["plaid:t1", "amount"] \
        == Decimal("-5.50")


def test_a_row_already_imported_from_a_file_is_not_added_again(linked):
    file_rows, _ = logic.map_import(logic.read_csv(
        "Date,Description,Amount\n2026-10-12,CAFE #12,4.50\n"), linked["card"], flip_signs=True,
        is_liability=True)
    data.import_transactions(file_rows, TODAY)
    rows, _ = logic.plaid_rows([tx()], {"pa-card": (linked["card"], True)})
    assert data.apply_sync(rows, [], [], TODAY)["skipped"] == 1
    assert len(data.transactions()) == 1


def test_apply_sync_is_all_or_nothing(linked):
    rows, _ = logic.plaid_rows([tx(), tx(transaction_id="t2")],
                               {"pa-card": (linked["card"], True)})
    rows[1]["account_id"] = 999
    with pytest.raises(Exception):
        data.apply_sync(rows, [], [], TODAY)
    assert data.transactions().empty


def test_the_live_database_gains_the_source_category_column(database):
    import psycopg
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("alter table transactions drop column source_category")
    data.migrate()
    data.migrate()
    with psycopg.connect(database, autocommit=True) as conn:
        assert conn.execute("""select 1 from information_schema.columns
                               where table_name = 'transactions'
                                 and column_name = 'source_category'""").fetchone()


# ---- a whole sync run -------------------------------------------------------

@pytest.fixture
def fake_bank(monkeypatch):
    """plaid_api faked at the function level, as sync.py calls it."""
    state = {"accounts": [
        {"provider_account_id": "pa-checking", "name": "Total Checking", "mask": "0001",
         "kind": "depository", "subtype": "checking", "balances": {"current": 1250.0}},
        {"provider_account_id": "pa-card", "name": "Freedom", "mask": "0002", "kind": "credit",
         "subtype": "credit card", "balances": {"current": 430.25}},
    ], "changes": {"added": [tx(), tx(transaction_id="pend", pending=True)], "modified": [],
                   "removed": [], "next_cursor": "c9"}, "fail": None, "cursors": []}

    def accounts(token):
        if state["fail"]:
            raise plaid_api.PlaidError("ITEM_LOGIN_REQUIRED", "Please sign in to your bank again.")
        return state["accounts"]

    def transactions_sync(token, cursor):
        state["cursors"].append(cursor)
        return state["changes"]

    monkeypatch.setattr(plaid_api, "accounts", accounts)
    monkeypatch.setattr(plaid_api, "transactions_sync", transactions_sync)
    monkeypatch.setattr(data, "today", lambda: TODAY)
    return state


def test_a_sync_run_adds_rows_saves_balances_and_moves_the_cursor(linked, fake_bank):
    assert sync.main() == 0
    conn = data.connection(linked["conn"])
    assert (conn["cursor"], conn["last_synced_on"], conn["last_error"]) == ("c9", TODAY, None)
    assert fake_bank["cursors"] == [None]
    stored = data.transactions()
    assert stored["import_key"].tolist() == ["plaid:t1"]            # the pending one waits
    assert data.account(linked["checking"])["balance"] == Decimal("1250.00")
    assert data.account(linked["card"])["balance"] == Decimal("430.25")
    assert data.account(linked["card"])["balance_on"] == TODAY
    # The next run starts from the cursor and adds nothing new.
    fake_bank["changes"] = {"added": [], "modified": [], "removed": [], "next_cursor": "c10"}
    assert sync.sync_connection(linked["conn"]) == {"added": 0, "skipped": 0, "modified": 0,
                                                    "removed": 0, "balances": 2}
    assert fake_bank["cursors"][-1] == "c9"


def test_a_bank_that_wants_a_new_sign_in_is_recorded_and_the_run_is_red(linked, fake_bank,
                                                                         capsys):
    fake_bank["fail"] = True
    assert sync.main() == 1
    conn = data.connection(linked["conn"])
    assert conn["last_error"] == "ITEM_LOGIN_REQUIRED: Please sign in to your bank again."
    assert conn["cursor"] is None and conn["last_synced_on"] is None
    assert "Chase: FAILED: ITEM_LOGIN_REQUIRED" in capsys.readouterr().err
    assert "access-1" not in capsys.readouterr().out
    fake_bank["fail"] = None
    assert sync.main() == 0
    assert data.connection(linked["conn"])["last_error"] is None     # cleared by a good run


def test_an_unmatched_bank_account_is_left_alone(linked, fake_bank):
    found = data.connected_accounts(linked["conn"]).set_index("provider_account_id")
    data.match_connected_account(int(found.loc["pa-card", "connected_account_id"]), None)
    result = sync.sync_connection(linked["conn"])
    assert result["added"] == 0 and result["balances"] == 1
    assert data.account(linked["card"])["balance"] is None


def test_no_banks_linked_is_a_quiet_success(database, capsys):
    assert sync.main() == 0
    assert "no banks linked" in capsys.readouterr().out
