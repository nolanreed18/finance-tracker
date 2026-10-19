"""Stats: where the money went, and whether the plan is working."""

import pandas as pd
import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
import theme
from ui import empty, setup

setup("Stats", "Where it went, and whether the plan is working")

today = data.today()
this_month = logic.month_start(today)
year = logic.recent_months(today, config.STATS_MONTHS)              # newest first
transactions = data.transactions(since=min(year))

if transactions.empty:
    empty("insights", "Nothing to chart yet",
          "Add transactions, or import a bank file, and the month's picture appears here.")
    st.stop()

# ---- spending by category ---------------------------------------------------

st.subheader("Spending by category")
month = st.selectbox("Month", year, key="stats_month",
                     format_func=lambda m: logic.month_label(m)
                     + (" (this month)" if m == this_month else ""))
by_category = logic.spending_by_category(logic.in_month(transactions, month))
if by_category.empty:
    empty("pie_chart", "No spending that month", "Pick another month above.")
else:
    chart = by_category.assign(spent=by_category["spent"].astype(float))
    st.bar_chart(chart, x="category", y="spent", horizontal=True, color=theme.CHART_COLORS[0],
                 x_label="", y_label="", height=max(160, 28 * len(chart) + 40))

last_three = logic.recent_months(month, 3)
st.markdown(f"**Last 3 months** ({logic.month_label(last_three[-1])} to "
            f"{logic.month_label(last_three[0])})")
by_month = logic.category_by_month(transactions, list(reversed(last_three)))
if by_month.empty:
    st.caption("No spending in those months.")
else:
    amount_columns = tuple(c for c in by_month.columns if c != "category")
    st.dataframe(
        logic.for_display(by_month, amounts=amount_columns), hide_index=True, width="stretch",
        column_config={"category": "Category", **{
            c: st.column_config.NumberColumn(c, format="dollar") for c in amount_columns}})

# ---- income vs spending -----------------------------------------------------

st.subheader(f"Income and spending, {config.STATS_MONTHS} months")
flows = logic.monthly_flows(transactions, year)
long = pd.concat([
    pd.DataFrame({"month": flows["month"], "series": "Income",
                  "amount": flows["income"].astype(float)}),
    pd.DataFrame({"month": flows["month"], "series": "Spending",
                  "amount": flows["spending"].astype(float)}),
])
st.bar_chart(long, x="month", y="amount", color="series", stack=False,
             x_label="", y_label="", height=260)

st.subheader("Savings rate")
rates = flows.assign(rate=flows["savings_rate"].map(
    lambda r: None if r is None else float(r) * 100))
if rates["rate"].notna().sum() < 1:
    st.caption("The savings rate needs a month with income: (income − spending) ÷ income.")
else:
    st.line_chart(rates, x="month", y="rate", color=theme.CHART_COLORS[1],
                  x_label="", y_label="%", height=200)
    st.caption("Savings rate = (income − spending) ÷ income, per month. Months without income "
               "are left out. Transfers between your own accounts count as neither.")

# ---- top payees -------------------------------------------------------------

st.subheader("Top payees")
payees = logic.top_payees(logic.in_month(transactions, month))
if payees.empty:
    st.caption(f"No spending in {logic.month_label(month)}.")
else:
    st.dataframe(
        logic.for_display(payees, amounts=("spent",)), hide_index=True, width="stretch",
        column_config={"payee": "Payee",
                       "spent": st.column_config.NumberColumn("Spent", format="dollar"),
                       "count": st.column_config.NumberColumn("Times", format="%d")})
