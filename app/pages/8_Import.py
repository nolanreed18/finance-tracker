"""Import: a CSV exported from a bank or card, previewed, then added all at once."""

import pandas as pd
import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import data
import logic
from ui import badge, empty, md, setup

setup("Import", "A file from your bank or card")

today = data.today()
accounts = data.open_accounts()
account_names = {int(r.account_id): r.name for r in accounts.itertuples()}
liabilities = {int(r.account_id): bool(r.is_liability) for r in accounts.itertuples()}

if accounts.empty:
    empty("account_balance", "No open accounts yet",
          "Add the account the file belongs to first; every imported row goes on one.")
    if st.button("Go to Accounts", type="primary"):
        st.switch_page("pages/1_Accounts.py")
    st.stop()

st.markdown(
    "Export the transactions from your bank's or card's website as a **CSV** file and drop it "
    "here. Headers are matched loosely: a date, a description (or payee), and either one signed "
    "amount column or separate debit and credit columns; a category column is used when it "
    "matches one of yours. Nothing is saved until you press **Import**, and the same row never "
    "imports twice.")

import_round = st.session_state.get("import_round", 0)
account_id = st.selectbox("Account the file belongs to", list(account_names),
                          format_func=account_names.get, key="import_account")
uploaded = st.file_uploader("CSV file", type=["csv", "txt"], key=f"import_file_{import_round}")
pasted = st.text_area("…or paste the rows, header line first", height=120,
                      key=f"import_text_{import_round}",
                      placeholder="Date,Description,Amount\n2026-10-12,CAFE #12,-4.50")

text = None
if uploaded is not None:
    text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
elif pasted.strip():
    text = pasted
if text is None:
    st.stop()

try:
    frame = logic.read_csv(text)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

is_liability = liabilities[account_id]
# Ticked for you when a card file lists charges as positive numbers (Discover,
# Amex); a new file or account gets a fresh guess (the key changes).
guess = logic.spending_looks_positive(frame, is_liability)
flip_signs = st.checkbox("Spending is positive in this file (flip the signs)", value=guess,
                         key=f"import_flip_{account_id}_{hash(tuple(frame.columns))}_{guess}",
                         help="Discover and Amex list charges as positive numbers; Chase and "
                              "Capital One don't. Ticked for you when the file looks that way.")
categories = {r.name: int(r.category_id) for r in data.categories().itertuples()}
rows, problems = logic.map_import(frame, account_id, categories, flip_signs, is_liability)
known = data.known_import_keys([r["import_key"] for r in rows])
new_rows = [r for r in rows if r["import_key"] not in known]

st.subheader("Preview")
for problem in problems:
    st.warning(problem)
if not rows:
    empty("upload_file", "Nothing to import", "Fix the file's headers (see above) and try again.")
    st.stop()

sums = logic.totals(pd.DataFrame(new_rows)) if new_rows else None
summary = [f"{logic.plural(len(new_rows), 'new transaction')}"]
if known:
    summary.append(f"{badge('gray', str(len(known)))} already imported, skipped")
if sums is not None:
    summary.append(f"income {logic.money(sums['income'])}, spending {logic.money(sums['spending'])}")
st.markdown(" · ".join(summary))

preview = pd.DataFrame(rows)
preview = preview.assign(status=preview["import_key"].map(
    lambda k: "already imported" if k in known else "new"),
    category=preview["category_id"].map(
        lambda c: next((n for n, i in categories.items() if i == c), None)))[
    ["happened_on", "payee", "amount", "kind", "category", "status"]]
st.dataframe(
    logic.for_display(preview, dates=("happened_on",), amounts=("amount",)),
    hide_index=True, width="stretch",
    column_config={
        "happened_on": st.column_config.DateColumn("Date", format="MMM D, YYYY"),
        "payee": st.column_config.TextColumn("Description", width="large"),
        "amount": st.column_config.NumberColumn("Amount", format="dollar"),
        "kind": "Kind", "category": "Category", "status": "Status",
    })
if sums is not None and sums["income"] > sums["spending"] and not flip_signs:
    st.caption("Mostly positive amounts? If this is a card statement, tick **Spending is "
               "positive** above so charges are stored as spending.")
if is_liability and any(r["kind"] == "transfer" for r in rows):
    st.caption("Payments onto this card come in as **transfers** (money moved from another "
               "account), so they don't count as income. Refunds stay as spending with a "
               "positive sign, which reduces the month's total.")

if not new_rows:
    st.info("Every row in this file is already in your transactions.")
    st.stop()

if st.button(f"Import {logic.plural(len(new_rows), 'transaction')} into "
             f"{account_names[account_id]}", type="primary", key="import_go"):
    added, skipped = data.import_transactions(new_rows, today)
    st.session_state["import_round"] = import_round + 1
    st.session_state["flash"] = (f"Imported {logic.plural(added, 'transaction')}."
                                 + (f" {skipped} already there, skipped." if skipped else ""))
    st.rerun()
st.caption(md(f"Rows go on {account_names[account_id]} as income or spending by their sign, "
              "with the description as the payee. Fix categories afterwards on Transactions."))
