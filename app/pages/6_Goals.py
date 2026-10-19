"""Goals: savings targets, with progress read from the account holding the money."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import data
import logic
from ui import (
    bump_round,
    card,
    delete_button,
    disclosure,
    empty,
    goal_badge,
    index_of,
    md,
    round_key,
    setup,
)

setup("Goals", "What you're saving for")

today = data.today()
accounts = data.open_accounts()
account_names = {int(r.account_id): r.name for r in accounts.itertuples()}


def next_round(name: str) -> None:
    """Forms are keyed by a counter; bumping it gives a fresh, empty form."""
    st.session_state[name] = st.session_state.get(name, 0) + 1


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        next_round(form_counter)
    st.session_state["flash"] = message
    st.rerun()


def account_label(account_id) -> str:
    return "(no account yet)" if account_id is None else account_names.get(account_id, "?")


# ---- add --------------------------------------------------------------------

add_round = st.session_state.get("add_round", 0)
if disclosure("Add a goal", "add_goal"):
    with st.form(f"add_goal_{add_round}"):
        name = st.text_input("Name", placeholder="e.g. Emergency fund, Trip, New car")
        amount_col, date_col = st.columns(2)
        target_amount = amount_col.number_input("Target ($)", value=None, min_value=0.0,
                                                step=100.0, format="%.2f")
        target_on = date_col.date_input("By when", value=None)
        account_id = st.selectbox("Account holding the money", [None, *account_names],
                                  format_func=account_label,
                                  help="Progress is that account's latest balance (entered "
                                       "on the Net worth page).")
        note = st.text_input("Note")
        submitted = st.form_submit_button("Add goal", type="primary")
    if submitted:
        if not name.strip():
            st.error("Give the goal a name.")
        elif target_amount is None or target_amount <= 0:
            st.error("Enter the target amount.")
        else:
            new_id = data.add_goal(name, logic.to_money(target_amount), target_on=target_on,
                                   account_id=account_id, note=note)
            st.session_state["open_add_goal"] = False
            st.session_state[round_key("pick_goal")] = new_id
            done(f"Added {name.strip()}.", "add_round")

# ---- the list ---------------------------------------------------------------

goals = data.goals()
if goals.empty:
    empty("savings", "No goals yet",
          "Name something you're saving for, how much, by when, and which account holds it.")
    st.stop()

for row in goals.itertuples():
    saved, share = logic.goal_progress(row.balance, row.target_amount)
    state = logic.goal_state(row.balance, row.target_amount, row.target_on, today, row.reached_on)
    with card(f"goal-{row.goal_id}"):
        facts = [f"{logic.money(saved)} of {logic.money(row.target_amount)}"]
        if not logic.blank(row.target_on):
            facts.append(f"by {row.target_on:%b} {row.target_on.day}, {row.target_on.year}")
        if not logic.blank(row.account):
            facts.append(f"in {row.account}")
        elif logic.blank(row.account_id):
            facts.append("no account picked")
        st.markdown(f"**{md(row.name)}** {goal_badge(state)}  \n{md(' · '.join(facts))}")
        pace = ("" if state == "reached"
                else logic.goal_pace(row.balance, row.target_amount, row.target_on, today))
        st.progress(share, text=md(f"{share:.0%}" + (f" · {pace}" if pace else "")))
        if logic.blank(row.account_id):
            st.caption("Pick the account holding this money (Edit below) to see progress.")
        elif not logic.blank(row.account_closed_on):
            st.caption("That account is closed: its last balance still counts.")

st.caption("Progress is the holding account's latest balance, so keeping balances up to date "
           "on the Net worth page keeps goals honest. A goal is **Reached** when the balance "
           "covers the target, or when you mark it so below.")

# ---- edit -------------------------------------------------------------------

st.subheader("Edit")
labels = {int(r.goal_id): r.name for r in goals.itertuples()}
options = list(labels)
pick_key = round_key("pick_goal")
picked_now = st.session_state.get(pick_key)
if picked_now is not None and picked_now not in options:       # gone: a fresh dropdown
    bump_round("pick_goal")
    pick_key, picked_now = round_key("pick_goal"), None
picked = st.selectbox("Goal", options, format_func=lambda i: labels.get(i, str(i)),
                      placeholder="Choose one…", key=pick_key,
                      **({} if pick_key in st.session_state else {"index": None}))
if picked is None:
    st.stop()
g = data.goal(picked)
if g is None:
    st.warning("That goal no longer exists.")
    st.stop()

all_accounts = {int(r.account_id): r.name for r in data.accounts().itertuples()}
edit_round = st.session_state.get("edit_round", 0)
with st.form(f"edit_goal_{picked}_{edit_round}"):
    e_name = st.text_input("Name", value=g["name"])
    amount_col, date_col = st.columns(2)
    e_target = amount_col.number_input("Target ($)", value=float(g["target_amount"]),
                                       min_value=0.0, step=100.0, format="%.2f")
    e_on = date_col.date_input("By when", value=g["target_on"])
    account_options = [None, *all_accounts]
    e_account = st.selectbox("Account holding the money", account_options,
                             format_func=lambda i: "(no account yet)" if i is None
                             else all_accounts.get(i, "?"),
                             index=index_of(account_options, g["account_id"]))
    e_note = st.text_input("Note", value=g["note"] or "")
    saved_form = st.form_submit_button("Save changes", type="primary")
if saved_form:
    if not e_name.strip():
        st.error("The name can't be blank.")
    elif e_target <= 0:
        st.error("Enter the target amount.")
    else:
        data.update_goal(picked, name=e_name, target_amount=logic.to_money(e_target),
                         target_on=e_on, account_id=e_account, note=e_note)
        done("Saved.", "edit_round")

if g["reached_on"] is None:
    if st.button("Mark reached", key=f"reached_{picked}"):
        data.update_goal(picked, reached_on=today)
        done(f"{g['name']} reached. Well done.")
else:
    st.caption(f"Reached {logic.when(g['reached_on'], today)}.")
    if st.button("Reopen goal", key=f"reopen_{picked}"):
        data.update_goal(picked, reached_on=None)
        done(f"{g['name']} is open again.")

st.divider()
if delete_button("goal", f"goal_{picked}"):
    data.delete_goal(picked)
    bump_round("pick_goal")
    done(f"Deleted {g['name']}.")
