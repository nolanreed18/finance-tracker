"""Knobs. Anything you might want to tune lives here.

The lists below are also enforced by CHECK constraints in schema.sql; change
both together (tests/test_data.py fails if they drift apart).
"""

from decimal import Decimal

# Account types. A new account of a LIABILITY_TYPES type is ticked as a
# liability (money owed) by default; any account can be ticked either way.
ACCOUNT_TYPES = [
    "checking",
    "savings",
    "credit card",
    "brokerage",
    "retirement",
    "loan",
    "cash",
    "other",
]
LIABILITY_TYPES = ["credit card", "loan"]

# Transaction kinds. Amounts are signed: income positive, spending negative.
# Transfers (between your own accounts) count as neither income nor spending.
TRANSACTION_KINDS = ["income", "expense", "transfer"]

# What a category is for.
CATEGORY_KINDS = ["income", "expense"]

# How often a bill comes round.
CADENCES = ["weekly", "monthly", "yearly"]

# Home lists bills due from today through this many days ahead (and any overdue).
BILL_LOOKAHEAD_DAYS = 7

# The morning ping reminds you of bills due within this many days (and any
# overdue); the weekly email uses BILL_LOOKAHEAD_DAYS.
REMINDER_DAYS = 3

# The weekly summary goes out on this weekday (0 = Monday).
SUMMARY_WEEKDAY = 0

# Where the app lives, for the links in pings and emails (the APP_URL secret
# overrides it).
APP_URL = "https://finance-tracke-sgtkbk6rogansxzkzwydqh.streamlit.app"

# A budget category is "close" at this share of its budget and "over" at 100%.
BUDGET_WARN = Decimal("0.9")

# An open account whose latest balance is this many days old (or that has
# none) is flagged on Home for an update.
STALE_BALANCE_DAYS = 30

# Months shown in the income vs spending chart on Stats.
STATS_MONTHS = 12
