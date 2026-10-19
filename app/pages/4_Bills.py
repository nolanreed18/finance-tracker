"""Bills: recurring bills and subscriptions, and what's due next."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
from ui import (
    bill_badges,
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

setup("Bills", "What's due")

today = data.today()
accounts = data.open_accounts()
account_names = {int(r.account_id): r.name for r in accounts.itertuples()}
categories = data.categories()
expense_categories = {int(r.category_id): r.name
                      for r in categories[categories["kind"] == "expense"].itertuples()}


def next_round(name: str) -> None:
    """Forms are keyed by a counter; bumping it gives a fresh, empty form."""
    st.session_state[name] = st.session_state.get(name, 0) + 1


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        next_round(form_counter)
    st.session_state["flash"] = message
    st.rerun()


def optional_label(names: dict, none_text: str):
    return lambda i: none_text if i is None else names.get(i, "?")


# ---- add --------------------------------------------------------------------

add_round = st.session_state.get("add_round", 0)
if disclosure("Add a bill", "add_bill"):
    with st.form(f"add_bill_{add_round}"):
        name = st.text_input("Name", placeholder="e.g. Rent, Phone, Streaming")
        amount_col, cadence_col = st.columns(2)
        amount = amount_col.number_input("Amount ($)", value=None, min_value=0.0, step=1.0,
                                         format="%.2f")
        cadence = cadence_col.selectbox("How often", config.CADENCES, format_func=str.capitalize,
                                        index=index_of(config.CADENCES, "monthly"))
        due_col, account_col = st.columns(2)
        next_due_on = due_col.date_input("Next due", value=today)
        account_id = account_col.selectbox("Paid from", [None, *account_names],
                                           format_func=optional_label(account_names, "(no account)"))
        category_col, autopay_col = st.columns(2, vertical_alignment="bottom")
        category_id = category_col.selectbox(
            "Category", [None, *expense_categories],
            format_func=optional_label(expense_categories, "(none)"))
        autopay = autopay_col.checkbox("Autopay", help="Paid automatically; still marked paid "
                                                       "here so the due date moves on.")
        notes = st.text_input("Notes")
        submitted = st.form_submit_button("Add bill", type="primary")
    if submitted:
        if not name.strip():
            st.error("Give the bill a name.")
        elif amount is None or amount <= 0:
            st.error("Enter the amount.")
        else:
            new_id = data.add_bill(name, logic.to_money(amount), cadence, next_due_on,
                                   account_id=account_id, autopay=autopay,
                                   category_id=category_id, notes=notes)
            st.session_state["open_add_bill"] = False
            st.session_state[round_key("pick_bill")] = new_id
            done(f"Added {name.strip()}.", "add_round")

# ---- the list ---------------------------------------------------------------

bills = data.bills()
if bills.empty:
    empty("event_repeat", "No bills yet",
          "Add the bills and subscriptions that come round, and the next date each is due.")
    st.stop()

active = bills[bills["active"].astype(bool)]
paused = bills[~bills["active"].astype(bool)]
states = [logic.bill_state(d, today) for d in active["next_due_on"]]
overdue = sum(s == "overdue" for s in states)
due_soon = sum(s == "due" for s in states)

month_col, soon_col, late_col = st.columns(3, gap="xsmall", wrap=False)
month_col.metric("Per month", logic.money(logic.bills_per_month(active)), border=True)
soon_col.metric(f"Due in {config.BILL_LOOKAHEAD_DAYS} days", due_soon, border=True)
late_col.metric("Overdue", overdue, border=True)

st.subheader("Coming up")
log_payment = st.checkbox("Log a transaction when I mark a bill paid", value=True,
                          key="log_payment",
                          help="The payment goes on the bill's account, as an expense in its "
                               "category, dated today.")
if active.empty:
    empty("task_alt", "Every bill is paused", "Edit one below to make it active again.")
for row in active.itertuples():
    state = logic.bill_state(row.next_due_on, today)
    with card(f"bill-{row.bill_id}"):
        text_col, button_col = st.columns([3, 1], vertical_alignment="center", wrap=False)
        facts = [logic.money(row.amount), row.cadence, logic.due_text(row.next_due_on, today)]
        if not logic.blank(row.account):
            facts.append(row.account)
        badges = bill_badges(state, bool(row.autopay), True)
        text_col.markdown(f"**{md(row.name)}**" + (f" {badges}" if badges else "") + "  \n"
                          f"{md(' · '.join(facts))}")
        if button_col.button("Mark paid", key=f"paid_{row.bill_id}", width="stretch"):
            if log_payment and logic.blank(row.account_id):
                st.error(f"{row.name} has no account to log the payment against: edit it "
                         "below, or untick the box.")
            else:
                data.mark_bill_paid(int(row.bill_id), today, log_payment, today)
                moved = logic.next_due(row.next_due_on, row.cadence)
                done(f"{row.name} paid; next due {logic.when(moved, today)}."
                     + (" Transaction logged." if log_payment else ""))

if not paused.empty:
    st.subheader("Paused")
    for row in paused.itertuples():
        with card(f"bill-{row.bill_id}"):
            st.markdown(f"**{md(row.name)}** {bill_badges(None, bool(row.autopay), False)}  \n"
                        f"{md(f'{logic.money(row.amount)} · {row.cadence}')}")

st.caption(f"A bill is **Due** from today through {config.BILL_LOOKAHEAD_DAYS} days ahead and "
           "**Overdue** after its date passes. Per month counts weekly bills as 52 a year.")

# ---- edit -------------------------------------------------------------------

st.subheader("Edit")
labels = {int(r.bill_id): r.name for r in bills.itertuples()}
options = list(labels)
pick_key = round_key("pick_bill")
picked_now = st.session_state.get(pick_key)
if picked_now is not None and picked_now not in options:       # gone: a fresh dropdown
    bump_round("pick_bill")
    pick_key, picked_now = round_key("pick_bill"), None
picked = st.selectbox("Bill", options, format_func=lambda i: labels.get(i, str(i)),
                      placeholder="Choose one…", key=pick_key,
                      **({} if pick_key in st.session_state else {"index": None}))
if picked is None:
    st.stop()
b = data.bill(picked)
if b is None:
    st.warning("That bill no longer exists.")
    st.stop()

all_accounts = {int(r.account_id): r.name for r in data.accounts().itertuples()}
all_categories = {int(r.category_id): r.name
                  for r in data.categories(include_archived=True).itertuples()
                  if r.kind == "expense"}
edit_round = st.session_state.get("edit_round", 0)
with st.form(f"edit_bill_{picked}_{edit_round}"):
    e_name = st.text_input("Name", value=b["name"])
    amount_col, cadence_col = st.columns(2)
    e_amount = amount_col.number_input("Amount ($)", value=float(b["amount"]), min_value=0.0,
                                       step=1.0, format="%.2f")
    e_cadence = cadence_col.selectbox("How often", config.CADENCES, format_func=str.capitalize,
                                      index=index_of(config.CADENCES, b["cadence"]))
    due_col, account_col = st.columns(2)
    e_due = due_col.date_input("Next due", value=b["next_due_on"])
    account_options = [None, *all_accounts]
    e_account = account_col.selectbox("Paid from", account_options,
                                      format_func=optional_label(all_accounts, "(no account)"),
                                      index=index_of(account_options, b["account_id"]))
    category_col, flags_col = st.columns(2, vertical_alignment="bottom")
    category_options = [None, *all_categories]
    e_category = category_col.selectbox("Category", category_options,
                                        format_func=optional_label(all_categories, "(none)"),
                                        index=index_of(category_options, b["category_id"]))
    e_autopay = flags_col.checkbox("Autopay", value=bool(b["autopay"]))
    e_active = flags_col.checkbox("Active", value=bool(b["active"]),
                                  help="Untick to pause a bill without losing it.")
    e_notes = st.text_input("Notes", value=b["notes"] or "")
    saved = st.form_submit_button("Save changes", type="primary")
if saved:
    if not e_name.strip():
        st.error("The name can't be blank.")
    elif e_amount <= 0:
        st.error("Enter the amount.")
    else:
        data.update_bill(picked, name=e_name, amount=logic.to_money(e_amount), cadence=e_cadence,
                         next_due_on=e_due, account_id=e_account, category_id=e_category,
                         autopay=e_autopay, active=e_active, notes=e_notes)
        done("Saved.", "edit_round")

st.divider()
if delete_button("bill", f"bill_{picked}"):
    data.delete_bill(picked)
    bump_round("pick_bill")
    done(f"Deleted {b['name']}.")
