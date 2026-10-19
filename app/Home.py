"""Home: where the money is, what's due, and whether the plan is working."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import data
from ui import empty, setup

today = data.today()
setup("Finance Tracker", f"{today:%A, %B %-d}")

st.subheader("Needs attention")
empty("account_balance", "Nothing to show yet",
      "Once your accounts, bills and budgets are in, what needs doing shows up here.")
