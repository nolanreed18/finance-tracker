"""Transactions: where the money goes, one line at a time."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
from ui import (
    bump_round,
    delete_button,
    disclosure,
    empty,
    index_of,
    kind_badge,
    md,
    round_key,
    setup,
)

setup("Transactions", "Where the money goes")

today = data.today()
accounts = data.open_accounts()
account_names = {int(r.account_id): r.name for r in accounts.itertuples()}
categories = data.categories()
category_names = {int(r.category_id): r.name for r in categories.itertuples()}
AMOUNT_HELP = ("Type the amount as a positive number; the kind decides the sign (spending is "
               "stored negative). For a transfer, make it negative when money leaves the account.")


def next_round(name: str) -> None:
    """Forms are keyed by a counter; bumping it gives a fresh, empty form."""
    st.session_state[name] = st.session_state.get(name, 0) + 1


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        next_round(form_counter)
    st.session_state["flash"] = message
    st.rerun()


def category_label(category_id) -> str:
    return "(none)" if category_id is None else category_names.get(category_id, "?")


if accounts.empty:
    empty("account_balance", "No open accounts yet",
          "Add an account first: every transaction belongs to one.")
    if st.button("Go to Accounts", type="primary"):
        st.switch_page("pages/1_Accounts.py")
    st.stop()

# ---- add --------------------------------------------------------------------

add_round = st.session_state.get("add_round", 0)
if disclosure("Add a transaction", "add_transaction"):
    with st.form(f"add_transaction_{add_round}"):
        date_col, account_col = st.columns(2)
        happened_on = date_col.date_input("Date", value=today)
        account_id = account_col.selectbox("Account", list(account_names),
                                           format_func=account_names.get)
        kind = st.radio("Kind", config.TRANSACTION_KINDS, horizontal=True,
                        format_func=str.capitalize, index=1)
        amount_col, category_col = st.columns(2)
        amount = amount_col.number_input("Amount ($)", value=None, step=1.0, format="%.2f",
                                         help=AMOUNT_HELP)
        category_id = category_col.selectbox("Category", [None, *category_names],
                                             format_func=category_label)
        payee = st.text_input("Payee", placeholder="Who was paid, or who paid you")
        notes = st.text_input("Notes")
        submitted = st.form_submit_button("Add transaction", type="primary")
    st.caption("Categories are managed on the Budgets page.")
    if submitted:
        if amount is None or amount == 0:
            st.error("Enter the amount.")
        else:
            new_id = data.add_transaction(
                account_id, happened_on, logic.signed(amount, kind), kind, today,
                category_id=category_id, payee=payee, notes=notes)
            st.session_state["open_add_transaction"] = False
            st.session_state[round_key("pick_transaction")] = new_id
            done(f"Added {logic.money(logic.signed(amount, kind))}"
                 + (f" at {payee.strip()}." if payee.strip() else "."), "add_round")

# ---- find -------------------------------------------------------------------

months = data.transaction_months()
if not months:
    empty("receipt_long", "No transactions yet",
          "Add one above, or bring in a bank file on the Import page.")
    st.stop()

st.subheader("Find")
month_col, account_col = st.columns(2)
month = month_col.selectbox("Month", [None, *months], key="tx_month",
                            format_func=lambda m: "All months" if m is None
                            else logic.month_label(m))
all_accounts = data.accounts()
all_account_names = {int(r.account_id): r.name for r in all_accounts.itertuples()}
account_filter = account_col.selectbox(
    "Account", [None, *all_account_names], key="tx_account",
    format_func=lambda i: "All accounts" if i is None else all_account_names[i])
category_col, search_col = st.columns(2)
all_categories = data.categories(include_archived=True)
all_category_names = {int(r.category_id): r.name for r in all_categories.itertuples()}
category_filter = category_col.selectbox(
    "Category", [None, *all_category_names], key="tx_category",
    format_func=lambda i: "All categories" if i is None else all_category_names[i])
search = search_col.text_input("Search", placeholder="Payee or notes", key="tx_search")

view = data.transactions(month=month, account_id=account_filter,
                         category_id=category_filter, search=search)
sums = logic.totals(view)
in_col, out_col, net_col = st.columns(3, gap="xsmall", wrap=False)
in_col.metric("Income", logic.money(sums["income"]), border=True)
out_col.metric("Spending", logic.money(sums["spending"]), border=True)
net_col.metric("Net", logic.money(sums["net"]), border=True)

if view.empty:
    empty("filter_alt", "Nothing matches", "Try All months, or clear the search.")
else:
    shown = view.assign(kind=view["kind"].str.capitalize())[
        ["happened_on", "payee", "amount", "kind", "category", "account", "notes"]]
    st.dataframe(
        logic.for_display(shown, dates=("happened_on",), amounts=("amount",)),
        hide_index=True, width="stretch",
        column_config={
            "happened_on": st.column_config.DateColumn("Date", format="MMM D"),
            "payee": st.column_config.TextColumn("Payee", width="medium"),
            "amount": st.column_config.NumberColumn("Amount", format="dollar"),
            "kind": "Kind", "category": "Category", "account": "Account", "notes": "Notes",
        })

# ---- one transaction --------------------------------------------------------

st.subheader("Edit")
labels = {int(r.transaction_id): logic.transaction_label(r.happened_on, r.payee, r.amount,
                                                          r.account)
          for r in view.itertuples()}
options = list(labels)
pick_key = round_key("pick_transaction")
picked_now = st.session_state.get(pick_key)
if picked_now is not None and picked_now not in options:
    if (row := data.transaction(picked_now)) is not None:     # just added: keep it on the list
        labels[picked_now] = logic.transaction_label(row["happened_on"], row["payee"],
                                                     row["amount"], row["account"])
        options = [picked_now, *options]
    else:                                                      # gone: a fresh dropdown
        bump_round("pick_transaction")
        pick_key, picked_now = round_key("pick_transaction"), None
picked = st.selectbox("Transaction", options, format_func=lambda i: labels.get(i, str(i)),
                      placeholder="Choose one…", key=pick_key,
                      **({} if pick_key in st.session_state else {"index": None}))
if picked is None:
    st.stop()
tx = data.transaction(picked)
if tx is None:
    st.warning("That transaction no longer exists.")
    st.stop()

st.markdown(f"{kind_badge(tx['kind'])} **{md(logic.money(tx['amount']))}** · "
            f"{md(tx['payee'] or tx['account'])} · {logic.when(tx['happened_on'], today)}")
edit_accounts = dict(all_account_names)
edit_categories = {None: "(none)", **all_category_names}
edit_round = st.session_state.get("edit_round", 0)
with st.form(f"edit_transaction_{picked}_{edit_round}"):
    date_col, account_col = st.columns(2)
    e_on = date_col.date_input("Date", value=tx["happened_on"])
    account_options = list(edit_accounts)
    e_account = account_col.selectbox("Account", account_options, format_func=edit_accounts.get,
                                      index=index_of(account_options, tx["account_id"]))
    e_kind = st.radio("Kind", config.TRANSACTION_KINDS, horizontal=True,
                      format_func=str.capitalize,
                      index=index_of(config.TRANSACTION_KINDS, tx["kind"]))
    amount_col, category_col = st.columns(2)
    e_amount = amount_col.number_input(
        "Amount ($)", value=float(abs(tx["amount"]) if tx["kind"] != "transfer" else tx["amount"]),
        step=1.0, format="%.2f", help=AMOUNT_HELP)
    category_options = list(edit_categories)
    e_category = category_col.selectbox("Category", category_options,
                                        format_func=edit_categories.get,
                                        index=index_of(category_options, tx["category_id"]))
    e_payee = st.text_input("Payee", value=tx["payee"] or "")
    e_notes = st.text_input("Notes", value=tx["notes"] or "")
    saved = st.form_submit_button("Save changes", type="primary")
if saved:
    if e_amount == 0:
        st.error("Enter the amount.")
    else:
        data.update_transaction(picked, happened_on=e_on, account_id=e_account, kind=e_kind,
                                amount=logic.signed(e_amount, e_kind), category_id=e_category,
                                payee=e_payee, notes=e_notes)
        done("Saved.", "edit_round")

st.divider()
if delete_button("transaction", f"transaction_{picked}"):
    data.delete_transaction(picked)
    bump_round("pick_transaction")
    done(f"Deleted {logic.money(tx['amount'])}"
         + (f" at {tx['payee']}." if tx["payee"] else "."))
