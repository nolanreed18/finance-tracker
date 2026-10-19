"""Pull new transactions and today's balances from every linked bank.

    python sync.py

Runs daily in GitHub Actions (.github/workflows/sync.yml) and from the
Accounts page's "Sync now". For each connection: ask Plaid what changed since
last time (its cursor), turn that into rows (logic.plaid_rows), apply them
all-or-nothing (data.apply_sync), then save each matched account's balance
for today. A bank that fails (most often ITEM_LOGIN_REQUIRED: it wants you
to sign in again) is recorded on its connection and the others carry on;
the run exits non-zero so a scheduled run shows red.

Nothing here prints a token or a secret.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))

import data  # noqa: E402
import logic  # noqa: E402
import plaid_api  # noqa: E402


def sync_connection(connection_id: int, today=None) -> dict:
    """One bank: {"added", "skipped", "modified", "removed", "balances"} or
    {"error": message}. Records the outcome on the connection either way."""
    today = today or data.today()
    conn = data.connection(connection_id)
    token = conn["access_token"]
    try:
        found = plaid_api.accounts(token)
        data.save_connected_accounts(connection_id, found)
        matched = data.connected_accounts(connection_id)
        accounts = {r.provider_account_id: (int(r.account_id), bool(r.is_liability))
                    for r in matched.itertuples() if not logic.blank(r.account_id)}
        changes = plaid_api.transactions_sync(token, conn["cursor"])
    except (plaid_api.PlaidError, RuntimeError) as exc:
        code = getattr(exc, "error_code", "")
        message = f"{code}: {exc}" if code else str(exc)
        data.update_connection(connection_id, last_error=message[:300])
        return {"error": message}
    rows, _ = logic.plaid_rows(changes["added"], accounts)
    modified, _ = logic.plaid_rows(changes["modified"], accounts)
    removed = [logic.plaid_key(t) for t in changes["removed"]]
    counts = data.apply_sync(rows, modified, removed, today)
    balances = 0
    for acct in found:
        match = accounts.get(acct["provider_account_id"])
        amount = logic.plaid_balance(acct)
        if match is not None and amount is not None:
            data.save_balance(match[0], today, amount)
            balances += 1
    data.update_connection(connection_id, cursor=changes["next_cursor"], last_synced_on=today,
                           last_error=None)
    return {**counts, "balances": balances}


def main() -> int:
    """Every connection; 0 when all synced, 1 when any failed."""
    links = data.connections()
    if links.empty:
        print("no banks linked yet")
        return 0
    failed = 0
    for row in links.itertuples():
        result = sync_connection(int(row.connection_id))
        name = row.institution_name or f"connection {row.connection_id}"
        if "error" in result:
            failed += 1
            print(f"{name}: FAILED: {result['error']}", file=sys.stderr)
        else:
            print(f"{name}: {result['added']} added, {result['modified']} changed, "
                  f"{result['removed']} removed, {result['skipped']} already there, "
                  f"{result['balances']} balances")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
