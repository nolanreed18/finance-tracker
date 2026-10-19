"""Home: where the money is, what's due, and whether the plan is working."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
from ui import attention_badge, card, empty, md, setup

today = data.today()
setup("Finance Tracker", f"{today:%A, %B %-d}")
this_month = logic.month_start(today)
accounts = data.accounts()
budgets = data.budgets(this_month)
bills = data.bills(active_only=True)
month_sums = logic.totals(data.transactions(month=this_month))

# ---- the headline numbers ---------------------------------------------------

worth = logic.net_worth_now(accounts)
budget = logic.budget_summary(budgets)
rate = logic.savings_rate(month_sums["income"], month_sums["spending"])
worth_col, spent_col, rate_col = st.columns(3, gap="xsmall", wrap=False)
worth_col.metric("Net worth", logic.money(worth["net"]), border=True)
spent_col.metric("Spent this month" if budget["budgeted"] == 0
                 else f"Spent of {logic.money(budget['budgeted'])} budget",
                 logic.money(month_sums["spending"]), border=True)
rate_col.metric("Savings rate", logic.percent(rate), border=True,
                help="(income − spending) ÷ income, this month")

# ---- needs attention --------------------------------------------------------

st.subheader("Needs attention")
items = logic.needs_attention(bills, budgets, accounts, today)
if accounts.empty:
    empty("account_balance", "Nothing to show yet",
          "Start on Accounts: add each place your money lives or is owed.")
elif not items:
    empty("task_alt", "Nothing needs attention",
          f"Bills due in {config.BILL_LOOKAHEAD_DAYS} days or overdue, budgets past "
          f"{config.BUDGET_WARN:.0%}, and balances {config.STALE_BALANCE_DAYS} days old show here.")
for n, item in enumerate(items):
    with card(f"attention-{n}"):
        text_col, button_col = st.columns([4, 1], vertical_alignment="center", wrap=False)
        text_col.markdown(f"{attention_badge(item.kind)} **{md(item.headline)}**  \n"
                          f"{md(item.detail)}")
        if button_col.button("Open", key=f"attention_{n}", width="stretch"):
            st.switch_page(item.page)

# ---- quick actions ----------------------------------------------------------

add_col, balances_col = st.columns(2)
if add_col.button("Add transaction", type="primary", width="stretch"):
    st.session_state["open_add_transaction"] = True
    st.switch_page("pages/2_Transactions.py")
if balances_col.button("Add balances", width="stretch"):
    st.session_state["open_update_balances"] = True
    st.switch_page("pages/5_Net_worth.py")
