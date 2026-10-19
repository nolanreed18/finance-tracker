"""The few Plaid calls the app makes, over plain HTTPS.

Plaid is the bank feed: you sign in at your bank once through Plaid's hosted
page, and from then on the daily sync (sync.py) pulls new transactions and
balances. The credentials come from PLAID_CLIENT_ID and PLAID_SECRET (the
environment, or the app's secrets online); they never appear in output.
Everything here is thin: no logic, just requests and their JSON, so the
tests fake post() and the rest of the app never sees Plaid's shapes except
through logic.plaid_rows.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ENVIRONMENTS = {"production": "https://production.plaid.com",
                "sandbox": "https://sandbox.plaid.com"}
TIMEOUT_S = 60
APP_NAME = "Finance Tracker"
HISTORY_DAYS = 730               # how far back the first sync of a bank reaches


class PlaidError(Exception):
    """Plaid said no. error_code is its code (ITEM_LOGIN_REQUIRED and the
    like); str() is the message meant for people."""

    def __init__(self, error_code: str, message: str, error_type: str = ""):
        super().__init__(message)
        self.error_code = error_code
        self.error_type = error_type


def secret(name: str) -> str | None:
    """A secret from the environment, or st.secrets inside a running
    Streamlit app (looked up through sys.modules, so scripts never import
    Streamlit)."""
    if value := os.environ.get(name):
        return value
    st = sys.modules.get("streamlit")
    if st is None:
        return None
    try:
        from streamlit import runtime

        if runtime.exists() and name in st.secrets:
            return st.secrets[name]
    except FileNotFoundError:
        pass
    return None


def configured() -> bool:
    return bool(secret("PLAID_CLIENT_ID") and secret("PLAID_SECRET"))


def post(path: str, **body) -> dict:
    """One Plaid call; its JSON. Raises PlaidError on a Plaid error, and
    RuntimeError when Plaid can't be reached or isn't set up."""
    client_id, client_secret = secret("PLAID_CLIENT_ID"), secret("PLAID_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Plaid isn't set up: add PLAID_CLIENT_ID and PLAID_SECRET.")
    base = ENVIRONMENTS[secret("PLAID_ENV") or "production"]
    payload = json.dumps({"client_id": client_id, "secret": client_secret, **body}).encode()
    request = urllib.request.Request(f"{base}{path}", data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read())
        except ValueError:
            detail = {}
        raise PlaidError(detail.get("error_code", str(exc.code)),
                         detail.get("display_message") or detail.get("error_message")
                         or f"Plaid error {exc.code}", detail.get("error_type", "")) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"couldn't reach Plaid: {exc.reason}") from None


# ---- linking a bank ---------------------------------------------------------

def create_link(user_id: str, access_token: str | None = None) -> dict:
    """Start a hosted Link session: {"link_token", "hosted_link_url"}. With an
    access_token, the session repairs an existing connection (a bank that
    wants you to sign in again) instead of adding one."""
    body = {
        "client_name": APP_NAME, "language": "en", "country_codes": ["US"],
        "user": {"client_user_id": user_id}, "hosted_link": {},
    }
    if access_token:
        body["access_token"] = access_token
    else:
        body["products"] = ["transactions"]
        body["transactions"] = {"days_requested": HISTORY_DAYS}
    reply = post("/link/token/create", **body)
    return {"link_token": reply["link_token"], "hosted_link_url": reply.get("hosted_link_url")}


def link_results(link_token: str) -> list[dict]:
    """What a finished hosted Link session produced: one dict per bank added,
    {"public_token", "institution_name", "institution_id"}; empty while the
    session isn't finished."""
    reply = post("/link/token/get", link_token=link_token)
    results = []
    for session in reply.get("link_sessions") or []:
        for item in (session.get("results") or {}).get("item_add_results") or []:
            institution = item.get("institution") or {}
            results.append({"public_token": item["public_token"],
                            "institution_name": institution.get("name"),
                            "institution_id": institution.get("institution_id")})
    return results


def exchange(public_token: str) -> dict:
    """{"access_token", "item_id"} for a freshly linked bank."""
    reply = post("/item/public_token/exchange", public_token=public_token)
    return {"access_token": reply["access_token"], "item_id": reply["item_id"]}


def remove(access_token: str) -> None:
    """Tell Plaid to forget the bank (stops any billing for it)."""
    post("/item/remove", access_token=access_token)


# ---- reading a bank ---------------------------------------------------------

def accounts(access_token: str) -> list[dict]:
    """The bank's accounts, with balances, as data.save_connected_accounts
    wants them plus a "balance" (logic.plaid_balance)."""
    reply = post("/accounts/get", access_token=access_token)
    return [{"provider_account_id": a["account_id"], "name": a.get("official_name") or a["name"],
             "mask": a.get("mask"), "kind": a.get("type"), "subtype": a.get("subtype"),
             "balances": a.get("balances") or {}} for a in reply.get("accounts", [])]


def institution_name(access_token: str) -> str | None:
    reply = post("/item/get", access_token=access_token)
    return (reply.get("item") or {}).get("institution_name")


def transactions_sync(access_token: str, cursor: str | None) -> dict:
    """Everything that changed since `cursor` (all history when None), in
    one bundle: {"added": [...], "modified": [...], "removed": [ids],
    "next_cursor"}. Plaid pages the answer; this follows the pages."""
    added, modified, removed = [], [], []
    next_cursor = cursor or ""
    while True:
        reply = post("/transactions/sync", access_token=access_token, cursor=next_cursor,
                     count=500, options={"include_personal_finance_category": True})
        added += reply.get("added", [])
        modified += reply.get("modified", [])
        removed += [r["transaction_id"] for r in reply.get("removed", [])]
        next_cursor = reply.get("next_cursor") or next_cursor
        if not reply.get("has_more"):
            break
    return {"added": added, "modified": modified, "removed": removed,
            "next_cursor": next_cursor}
