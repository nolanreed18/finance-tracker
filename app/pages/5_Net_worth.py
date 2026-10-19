"""Net worth: what you own minus what you owe, now and over time."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
import theme
from ui import badge, disclosure, empty, md, setup

setup("Net worth", "What you own, minus what you owe")

today = data.today()
accounts = data.accounts()
open_accounts = accounts[accounts["closed_on"].isna()]


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        st.session_state[form_counter] = st.session_state.get(form_counter, 0) + 1
    st.session_state["flash"] = message
    st.rerun()


if open_accounts.empty:
    empty("account_balance", "No open accounts yet",
          "Add your accounts first; then come back and enter each one's balance.")
    if st.button("Go to Accounts", type="primary"):
        st.switch_page("pages/1_Accounts.py")
    st.stop()

# ---- update balances --------------------------------------------------------

update_round = st.session_state.get("update_round", 0)
if disclosure("Update balances", "update_balances"):
    with st.form(f"update_balances_{update_round}"):
        as_of = st.date_input("As of", value=today,
                              help="A second entry for the same day replaces the first.")
        st.caption("Each account's last balance is filled in: change the ones you know. "
                   "Enter what you owe on a card or loan as a positive number.")
        typed = {}
        for row in open_accounts.itertuples():
            last = logic.value(row.balance)
            typed[int(row.account_id)] = st.number_input(
                f"{row.name}" + (" (owed)" if row.is_liability else ""),
                value=None if last is None else float(last), step=10.0, format="%.2f",
                key=f"balance_{row.account_id}_{update_round}")
        submitted = st.form_submit_button("Save balances", type="primary")
    if submitted:
        if all(v is None for v in typed.values()):
            st.error("Enter at least one balance.")
        else:
            saved = data.save_balances(list(typed.items()), as_of)
            st.session_state["open_update_balances"] = False
            done(f"Saved {logic.plural(saved, 'balance')} as of {logic.when(as_of, today)}.",
                 "update_round")

# ---- now --------------------------------------------------------------------

now = logic.net_worth_now(accounts)
net_col, assets_col, owed_col = st.columns(3, gap="xsmall", wrap=False)
net_col.metric("Net worth", logic.money(now["net"]), border=True)
assets_col.metric("Assets", logic.money(now["assets"]), border=True)
owed_col.metric("Liabilities", logic.money(now["liabilities"]), border=True)

history = logic.net_worth_history(data.balances())
if history.empty:
    empty("show_chart", "No balances yet",
          "Use Update balances above to enter today's balance for each account.")
    st.stop()

# ---- over time --------------------------------------------------------------

st.subheader("Over time")
if len(history) < 2:
    st.caption("The chart starts once balances span two months. Enter them around the same "
               "day each month.")
else:
    chart = history.assign(net_worth=history["net_worth"].astype(float))
    st.line_chart(chart, x="month", y="net_worth", color=theme.CHART_COLORS[0],
                  x_label="", y_label="", height=260)

# ---- assets vs liabilities --------------------------------------------------

st.subheader("Assets and liabilities")
stale = [logic.stale_balance(d, today) for d in open_accounts["balance_on"]]
if any(stale):
    names = [r.name for r, s in zip(open_accounts.itertuples(), stale) if s]
    st.markdown(f"{badge('yellow', 'Update balance')} {md(', '.join(names))}: no balance for "
                f"{config.STALE_BALANCE_DAYS} days, or none yet.")
table = open_accounts.assign(
    side=open_accounts["is_liability"].map({True: "Liability", False: "Asset"}))[
    ["name", "side", "kind", "balance", "balance_on"]].sort_values(["side", "name"])
st.dataframe(
    logic.for_display(table, dates=("balance_on",), amounts=("balance",)),
    hide_index=True, width="stretch",
    column_config={
        "name": "Account", "side": "Side",
        "kind": st.column_config.TextColumn("Type"),
        "balance": st.column_config.NumberColumn("Balance", format="dollar"),
        "balance_on": st.column_config.DateColumn("As of", format="MMM D, YYYY"),
    })
st.caption("Liabilities are what you owe, entered as positive numbers; net worth subtracts "
           "them. Closed accounts count until the month they were closed.")
