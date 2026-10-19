"""Accounts: where the money is, and where it's owed."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
from ui import (
    account_badges,
    bump_round,
    card,
    delete_button,
    disclosure,
    empty,
    index_of,
    md,
    round_key,
    setup,
)

setup("Accounts", "Where the money is")

today = data.today()
TYPE_HELP = ("Credit cards and loans are money owed: they're ticked as liabilities for you, "
             "and net worth subtracts them.")


def next_round(name: str) -> None:
    """Forms are keyed by a counter; bumping it gives a fresh, empty form."""
    st.session_state[name] = st.session_state.get(name, 0) + 1


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        next_round(form_counter)
    st.session_state["flash"] = message
    st.rerun()


def taken(name: str, except_id: int | None = None) -> bool:
    """Whether another account already has this name, whatever the capitalisation."""
    others = accounts if except_id is None else accounts[accounts["account_id"] != except_id]
    return name.strip().lower() in others["name"].str.lower().tolist()


# ---- add --------------------------------------------------------------------

accounts = data.accounts()
add_round = st.session_state.get("add_round", 0)
if disclosure("Add an account", "add_account"):
    with st.form(f"add_account_{add_round}"):
        name = st.text_input("Name", placeholder="e.g. Everyday checking")
        kind_col, bank_col = st.columns(2)
        kind = kind_col.selectbox("Type", config.ACCOUNT_TYPES, format_func=str.capitalize,
                                  help=TYPE_HELP)
        institution = bank_col.text_input("Bank or institution")
        liability = st.checkbox("Money owed (a liability)", help=TYPE_HELP)
        opened_on = st.date_input("Opened on", value=today)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add account", type="primary")
    if submitted:
        if not name.strip():
            st.error("Give the account a name.")
        elif taken(name):
            st.error("There's already an account with that name.")
        else:
            new_id = data.add_account(
                name, kind, institution=institution,
                is_liability=liability or kind in config.LIABILITY_TYPES,
                opened_on=opened_on, notes=notes)
            st.session_state["open_add_account"] = False
            st.session_state[round_key("pick_account")] = new_id
            done(f"Added {name.strip()}.", "add_round")

# ---- the list ---------------------------------------------------------------

if accounts.empty:
    empty("account_balance", "No accounts yet",
          "Add each place your money lives, or is owed: checking, savings, cards, loans.")
    st.stop()

open_accounts = accounts[accounts["closed_on"].isna()]
closed_accounts = accounts[accounts["closed_on"].notna()]


def draw(row) -> None:
    closed = not logic.blank(row.closed_on)
    stale = logic.stale_balance(row.balance_on, today)
    with card(f"account-{row.account_id}"):
        text_col, amount_col = st.columns([3, 2], vertical_alignment="center", wrap=False)
        facts = [x for x in (logic.value(row.institution),) if x]
        facts.append(f"closed {logic.when(row.closed_on, today)}" if closed
                     else logic.balance_age(row.balance_on, today))
        text_col.markdown(
            f"**{md(row.name)}**  \n"
            f"{account_badges(row.kind, bool(row.is_liability), closed, stale)}  \n"
            f"{md(' · '.join(facts))}")
        amount = logic.value(row.balance)
        amount_col.markdown(f"#### {md(logic.money(amount))}" if amount is not None else "")


st.subheader("Open")
if open_accounts.empty:
    empty("inventory_2", "Every account is closed", "Reopen one below, or add a new one.")
for row in open_accounts.itertuples():
    draw(row)

if not closed_accounts.empty:
    st.subheader("Closed")
    for row in closed_accounts.itertuples():
        draw(row)

st.caption(f"An open account with no balance for {config.STALE_BALANCE_DAYS} days is marked "
           "**Update balance**; balances are entered on the Net worth page.")

# ---- edit -------------------------------------------------------------------

st.subheader("Edit")
labels = {int(r.account_id): r.name for r in accounts.itertuples()}
options = list(labels)
pick_key = round_key("pick_account")
picked_now = st.session_state.get(pick_key)
if picked_now is not None and picked_now not in options:       # gone: a fresh dropdown
    bump_round("pick_account")
    pick_key, picked_now = round_key("pick_account"), None
picked = st.selectbox("Account", options, format_func=lambda i: labels.get(i, str(i)),
                      placeholder="Choose one…", key=pick_key,
                      **({} if pick_key in st.session_state else {"index": None}))
if picked is None:
    st.stop()
acct = data.account(picked)
if acct is None:
    st.warning("That account no longer exists.")
    st.stop()

edit_round = st.session_state.get("edit_round", 0)
with st.form(f"edit_account_{picked}_{edit_round}"):
    e_name = st.text_input("Name", value=acct["name"])
    kind_col, bank_col = st.columns(2)
    e_kind = kind_col.selectbox("Type", config.ACCOUNT_TYPES, format_func=str.capitalize,
                                index=index_of(config.ACCOUNT_TYPES, acct["kind"]), help=TYPE_HELP)
    e_institution = bank_col.text_input("Bank or institution", value=acct["institution"] or "")
    e_liability = st.checkbox("Money owed (a liability)", value=bool(acct["is_liability"]))
    e_opened = st.date_input("Opened on", value=acct["opened_on"])
    e_notes = st.text_area("Notes", value=acct["notes"] or "")
    saved = st.form_submit_button("Save changes", type="primary")
if saved:
    if not e_name.strip():
        st.error("The name can't be blank.")
    elif taken(e_name, picked):
        st.error("There's already an account with that name.")
    else:
        data.update_account(picked, name=e_name, kind=e_kind, institution=e_institution,
                            is_liability=e_liability, opened_on=e_opened, notes=e_notes)
        done("Saved.", "edit_round")

st.divider()
has_history = (acct["transactions"] or 0) + (acct["balances"] or 0) > 0
if acct["closed_on"] is None:
    st.caption("Closing keeps the account's history but takes it out of pickers and net worth.")
    if st.button("Close account", key=f"close_{picked}"):
        data.close_account(picked, today)
        done(f"Closed {acct['name']}.")
else:
    if st.button("Reopen account", key=f"reopen_{picked}"):
        data.reopen_account(picked)
        done(f"Reopened {acct['name']}.")

if has_history:
    st.caption(f"This account has {logic.plural(int(acct['transactions']), 'transaction')} and "
               f"{logic.plural(int(acct['balances']), 'balance')}, so it can't be deleted: "
               "close it instead.")
elif delete_button("account", f"account_{picked}"):
    try:
        data.delete_account(picked)
    except data.InUse as exc:
        st.error(str(exc).capitalize() + ".")
    else:
        bump_round("pick_account")
        done(f"Deleted {acct['name']}.")
