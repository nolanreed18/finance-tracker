"""Accounts: where the money is, and where it's owed."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
import plaid_api
import sync
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
    sync_badge,
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

# ---- connected banks --------------------------------------------------------

st.subheader("Connected banks")
PLAID_USER = "owner"             # one person: Plaid's id for you never changes
NEW_ACCOUNT, NO_SYNC = -1, 0     # choices in the matching dropdown besides our accounts


def match_label(choice) -> str:
    if choice == NEW_ACCOUNT:
        return "(create a new account)"
    if choice == NO_SYNC:
        return "(don't sync this one)"
    return labels_open.get(choice, str(choice))


def finish_link(link_token: str, repairing: int | None) -> None:
    """After the hosted sign-in: a repaired connection is synced again; a new
    bank becomes a connection with its accounts listed for matching."""
    if repairing is not None:
        data.update_connection(repairing, last_error=None)
        sync.sync_connection(repairing, today)
        st.session_state.pop("link", None)
        done("Signed in again; the bank is syncing.")
    results = plaid_api.link_results(link_token)
    if not results:
        st.warning("Plaid hasn't heard from your bank yet. Finish the sign-in in the other tab, "
                   "then press this button again.")
        return
    for result in results:
        tokens = plaid_api.exchange(result["public_token"])
        connection_id = data.add_connection(tokens["item_id"], tokens["access_token"], today,
                                            institution_name=result["institution_name"])
        data.save_connected_accounts(connection_id, plaid_api.accounts(tokens["access_token"]))
    st.session_state.pop("link", None)
    done(f"Linked {', '.join(r['institution_name'] or 'a bank' for r in results)}. Match its "
         "accounts to yours below.")


if not plaid_api.configured():
    st.caption("Bank sync isn't set up yet: add `PLAID_CLIENT_ID` and `PLAID_SECRET` to the "
               "app's secrets (README → Bank sync). Until then, use the Import page.")
else:
    labels_open = {int(r.account_id): r.name for r in open_accounts.itertuples()}
    link = st.session_state.get("link")        # {"token", "url", "repairing"} while signing in
    if link is None:
        if st.button("Connect a bank", icon=":material/add_link:", key="connect_bank"):
            try:
                made = plaid_api.create_link(PLAID_USER)
            except (plaid_api.PlaidError, RuntimeError) as exc:
                st.error(f"Couldn't start the bank sign-in: {md(str(exc))}")
            else:
                st.session_state["link"] = {"token": made["link_token"],
                                            "url": made["hosted_link_url"], "repairing": None}
                st.rerun()
    else:
        with card("link"):
            st.markdown("**Sign in at your bank** in the tab that opens, then come back and "
                        "press **I've finished**.")
            open_col, done_col, cancel_col = st.columns(3)
            open_col.link_button("Open the sign-in", link["url"], type="primary", width="stretch")
            if done_col.button("I've finished", key="link_done", width="stretch"):
                try:
                    finish_link(link["token"], link["repairing"])
                except (plaid_api.PlaidError, RuntimeError) as exc:
                    st.error(f"Plaid said: {md(str(exc))}")
            if cancel_col.button("Cancel", key="link_cancel", width="stretch"):
                st.session_state.pop("link", None)
                st.rerun()

    connections = data.connections()
    if connections.empty and link is None:
        empty("account_balance_wallet", "No banks connected",
              "Connect a bank and its transactions and balances arrive every morning by "
              "themselves. Until then, the Import page takes a CSV.")
    for conn in connections.itertuples():
        cid = int(conn.connection_id)
        state = logic.sync_badge_state(conn.last_synced_on, conn.last_error, today)
        with card(f"connection-{cid}"):
            text_col, button_col = st.columns([3, 1], vertical_alignment="center", wrap=False)
            facts = [f"{int(conn.matched)} of {logic.plural(int(conn.accounts), 'account')} "
                     "matched"]
            if not logic.blank(conn.last_synced_on):
                facts.append(f"synced {logic.when(conn.last_synced_on, today)}")
            text_col.markdown(f"**{md(conn.institution_name or 'Bank')}** {sync_badge(state)}  \n"
                              f"{md(' · '.join(facts))}")
            if state == "error":
                text_col.caption(md(logic.sync_problem(conn.last_error)))
            if button_col.button("Sync now", key=f"sync_{cid}", width="stretch"):
                result = sync.sync_connection(cid, today)
                if "error" in result:
                    done(f"Sync failed: {logic.sync_problem(result['error'])}")
                done(f"Synced {conn.institution_name or 'the bank'}: {result['added']} new, "
                     f"{result['balances']} balances updated.")
            if state == "error" and st.button("Sign in again", key=f"relink_{cid}",
                                              type="primary"):
                try:
                    made = plaid_api.create_link(PLAID_USER, data.connection(cid)["access_token"])
                except (plaid_api.PlaidError, RuntimeError) as exc:
                    st.error(f"Couldn't start the bank sign-in: {md(str(exc))}")
                else:
                    st.session_state["link"] = {"token": made["link_token"],
                                                "url": made["hosted_link_url"], "repairing": cid}
                    st.rerun()

            bank_accounts = data.connected_accounts(cid)
            match_round = st.session_state.get(f"match_round_{cid}", 0)
            with st.form(f"match_{cid}_{match_round}"):
                st.caption("Which of your accounts each bank account feeds. Pick **create a new "
                           "account** for one you haven't added yet.")
                choices = {}
                for ba in bank_accounts.itertuples():
                    current = (int(ba.account_id) if not logic.blank(ba.account_id)
                               else logic.suggest_account(ba.name, ba.mask, accounts) or NEW_ACCOUNT)
                    options = [NEW_ACCOUNT, NO_SYNC, *labels_open]
                    choices[int(ba.connected_account_id)] = st.selectbox(
                        f"{ba.name}" + (f" ····{ba.mask}" if not logic.blank(ba.mask) else ""),
                        options, index=index_of(options, current), format_func=match_label,
                        key=f"match_{ba.connected_account_id}_{match_round}")
                saved_matches = st.form_submit_button("Save matches", type="primary")
            if saved_matches:
                created = []
                for ba in bank_accounts.itertuples():
                    choice = choices[int(ba.connected_account_id)]
                    if choice == NEW_ACCOUNT:
                        kind, owed = logic.account_kind_for(ba.kind, ba.subtype)
                        name = ba.name if not taken(ba.name) else f"{ba.name} ····{ba.mask}"
                        choice = data.add_account(name, kind, is_liability=owed,
                                                  institution=conn.institution_name, opened_on=today)
                        created.append(name)
                    data.match_connected_account(int(ba.connected_account_id),
                                                 None if choice == NO_SYNC else int(choice))
                next_round(f"match_round_{cid}")
                done("Matches saved." + (f" Created {', '.join(created)}." if created else "")
                     + " Press Sync now to pull the history.")

            if delete_button("bank connection", f"connection_{cid}"):
                try:
                    plaid_api.remove(data.connection(cid)["access_token"])
                except (plaid_api.PlaidError, RuntimeError):
                    pass                    # Plaid may already have forgotten it
                data.delete_connection(cid)
                done(f"Removed {conn.institution_name or 'the bank'}. Your accounts and their "
                     "transactions stay.")
    st.caption("Linked banks sync every morning; **Sync now** pulls what's new straight away. "
               "Removing a bank keeps everything already imported.")

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
    opened_col, apr_col = st.columns(2)
    e_opened = opened_col.date_input("Opened on", value=acct["opened_on"])
    e_apr = apr_col.number_input("Interest rate (APR %)", min_value=0.0, max_value=99.99,
                                 step=0.25, format="%.2f",
                                 value=None if acct["apr"] is None else float(acct["apr"]),
                                 help="From the card's or loan's statement. Used by the payoff "
                                      "calculator below.")
    e_notes = st.text_area("Notes", value=acct["notes"] or "")
    saved = st.form_submit_button("Save changes", type="primary")
if saved:
    if not e_name.strip():
        st.error("The name can't be blank.")
    elif taken(e_name, picked):
        st.error("There's already an account with that name.")
    else:
        data.update_account(picked, name=e_name, kind=e_kind, institution=e_institution,
                            is_liability=e_liability, opened_on=e_opened, notes=e_notes,
                            apr=None if e_apr is None else logic.to_money(e_apr))
        done("Saved.", "edit_round")

# ---- payoff ------------------------------------------------------------------

if acct["is_liability"]:
    st.subheader("Payoff")
    owed_now = logic.value(acct["balance"])
    owed_col, apr_col, pay_col = st.columns(3)
    owed = owed_col.number_input("Owed ($)", min_value=0.0, step=10.0, format="%.2f",
                                 value=0.0 if owed_now is None else float(owed_now),
                                 key=f"payoff_owed_{picked}")
    apr = apr_col.number_input("APR %", min_value=0.0, max_value=99.99, step=0.25, format="%.2f",
                               value=0.0 if acct["apr"] is None else float(acct["apr"]),
                               key=f"payoff_apr_{picked}")
    payment = pay_col.number_input("I'll pay ($/month)", min_value=0.0, step=10.0, format="%.2f",
                                   value=owed, key=f"payoff_pay_{picked}")
    if acct["apr"] is None:
        st.caption("Save the card's APR in the form above and it's filled in here.")
    plan = logic.payoff_plan(owed, apr, payment)
    next_col, months_col, total_col = st.columns(3, gap="xsmall", wrap=False)
    next_col.metric("Interest next month", logic.money(logic.interest_if_short(owed, payment, apr)),
                    border=True)
    months_col.metric("Months to clear", "never" if plan is None else plan["months"], border=True)
    total_col.metric("Total interest", "—" if plan is None else logic.money(plan["interest"]),
                     border=True)
    if plan is None:
        st.warning("That payment doesn't cover the interest, so the balance never shrinks.")
    elif plan["months"] > 1:
        clear = [f"**{md(logic.money(logic.payment_to_clear(owed, apr, n)))}** a month clears it "
                 f"in {n} months" for n in (3, 6, 12) if n < plan["months"]]
        if clear:
            st.markdown("; ".join(clear) + ".")
    st.caption("Interest is added monthly at APR ÷ 12 on what's left after the payment. Once a "
               "card isn't paid in full, most issuers also charge interest on new purchases, so "
               "the real figure runs a little higher. Paying the full balance costs nothing.")

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
