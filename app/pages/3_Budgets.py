"""Budgets: what you planned to spend per category this month, against what
you did. Categories are managed here too."""

import streamlit as st

import fresh

fresh.check()                   # after a redeploy: no stale copies of the app's modules

import config
import data
import logic
from ui import (
    badge,
    budget_badge,
    bump_round,
    card,
    disclosure,
    empty,
    index_of,
    kind_badge,
    md,
    round_key,
    sections,
    setup,
)

setup("Budgets", "The plan, against the month")

today = data.today()
this_month = logic.month_start(today)


def next_round(name: str) -> None:
    """Forms are keyed by a counter; bumping it gives a fresh, empty form."""
    st.session_state[name] = st.session_state.get(name, 0) + 1


def done(message: str, form_counter: str | None = None) -> None:
    if form_counter:
        next_round(form_counter)
    st.session_state["flash"] = message
    st.rerun()


section = sections("budgets", ["Budget", "Categories"])

# ---- the month's budget -----------------------------------------------------

if section == "Budget":
    months = [logic.add_months(this_month, 1), *logic.recent_months(today, config.STATS_MONTHS)]
    for extra in data.budget_months():                  # older months with a budget still show
        if extra not in months:
            months.append(extra)
    month = st.selectbox("Month", months, index=1, key="budget_month",
                         format_func=lambda m: logic.month_label(m)
                         + (" (this month)" if m == this_month else ""))
    rows = data.budgets(month)
    if rows.empty:
        empty("category", "No categories yet",
              "Add your spending categories under Categories, then set a budget for each.")
        st.stop()

    summary = logic.budget_summary(rows)
    budgeted_col, spent_col, left_col = st.columns(3, gap="xsmall", wrap=False)
    budgeted_col.metric("Budgeted", logic.money(summary["budgeted"]), border=True)
    spent_col.metric("Spent", logic.money(summary["spent"]), border=True)
    left_col.metric("Left", logic.money(summary["left"]), border=True)

    last_month = logic.add_months(month, -1)
    if rows["budget_id"].isna().all():
        if last_month in data.budget_months():
            st.caption(f"Nothing is budgeted for {logic.month_label(month)} yet.")
            if st.button(f"Copy {logic.month_label(last_month)}", type="primary",
                         key="copy_last_month"):
                copied = data.copy_budgets(last_month, month)
                done(f"Copied {logic.plural(copied, 'budget')} from "
                     f"{logic.month_label(last_month)}.")
        else:
            st.caption(f"Nothing is budgeted for {logic.month_label(month)} yet: set the "
                       "amounts below.")

    for row in rows.itertuples():
        budgeted = logic.value(row.budgeted)
        spent = logic.to_money(row.spent)
        state = logic.budget_state(budgeted, spent)
        with card(f"budget-{row.category_id}"):
            name_col, badge_col = st.columns([3, 2], vertical_alignment="center", wrap=False)
            name_col.markdown(f"**{md(row.name)}**"
                              + (f" {badge('gray', 'Archived')}" if row.archived else ""))
            if state is not None:
                badge_col.markdown(budget_badge(state))
            if budgeted is None:
                st.caption(f"{md(logic.money(spent))} spent · no budget set")
            else:
                left = budgeted - spent
                st.progress(logic.budget_share(budgeted, spent),
                            text=md(f"{logic.money(spent)} of {logic.money(budgeted)} · "
                                    + (f"{logic.money(-left)} over" if left < 0
                                       else f"{logic.money(left)} left")))

    st.caption(f"A category is **Close to budget** at {config.BUDGET_WARN:.0%} of its amount "
               "and **Over budget** at 100%. Only spending counts; transfers don't.")

    set_round = st.session_state.get("set_round", 0)
    if disclosure("Set budgets", "set_budgets"):
        active = rows[~rows["archived"].astype(bool)]
        with st.form(f"set_budgets_{month}_{set_round}"):
            st.caption(f"Amounts for {logic.month_label(month)}. Leave one blank for no budget.")
            amounts = {}
            for row in active.itertuples():
                current = logic.value(row.budgeted)
                amounts[int(row.category_id)] = st.number_input(
                    row.name, value=None if current is None else float(current),
                    min_value=0.0, step=10.0, format="%.2f", key=f"budget_{row.category_id}")
            saved = st.form_submit_button("Save budgets", type="primary")
        if saved:
            for category_id, amount in amounts.items():
                data.set_budget(month, category_id, amount)
            st.session_state["open_set_budgets"] = False
            done(f"Budgets saved for {logic.month_label(month)}.", "set_round")

# ---- categories -------------------------------------------------------------

if section == "Categories":
    categories = data.categories(include_archived=True)

    add_round = st.session_state.get("add_round", 0)
    if disclosure("Add a category", "add_category"):
        with st.form(f"add_category_{add_round}"):
            name_col, kind_col = st.columns(2)
            name = name_col.text_input("Name", placeholder="e.g. Groceries")
            kind = kind_col.selectbox("Kind", config.CATEGORY_KINDS, format_func=str.capitalize,
                                      index=index_of(config.CATEGORY_KINDS, "expense"),
                                      help="Expense categories get budgets; income ones "
                                           "only label where money came from.")
            submitted = st.form_submit_button("Add category", type="primary")
        if submitted:
            if not name.strip():
                st.error("Give the category a name.")
            elif name.strip().lower() in categories["name"].str.lower().tolist():
                st.error("There's already a category with that name.")
            else:
                new_id = data.add_category(name, kind,
                                           sort_order=int(len(categories)))
                st.session_state["open_add_category"] = False
                st.session_state[round_key("pick_category")] = new_id
                done(f"Added {name.strip()}.", "add_round")

    if categories.empty:
        empty("category", "No categories yet",
              "Add a few to start: Groceries, Rent, Eating out, Pay…")
        st.stop()

    for kind in config.CATEGORY_KINDS:
        group = categories[categories["kind"] == kind]
        if group.empty:
            continue
        st.subheader(f"{kind.capitalize()} categories")
        lines = [f"- {md(row.name)}" + (f" {badge('gray', 'Archived')}" if row.archived else "")
                 for row in group.itertuples()]
        st.markdown("\n".join(lines))

    st.subheader("Edit")
    labels = {int(r.category_id): r.name for r in categories.itertuples()}
    options = list(labels)
    pick_key = round_key("pick_category")
    picked = st.selectbox("Category", options, format_func=lambda i: labels.get(i, str(i)),
                          placeholder="Choose one…", key=pick_key,
                          **({} if pick_key in st.session_state else {"index": None}))
    if picked is None:
        st.stop()
    cat = categories.set_index("category_id").loc[picked]

    edit_round = st.session_state.get("edit_round", 0)
    with st.form(f"edit_category_{picked}_{edit_round}"):
        name_col, kind_col = st.columns(2)
        e_name = name_col.text_input("Name", value=cat["name"])
        e_kind = kind_col.selectbox("Kind", config.CATEGORY_KINDS, format_func=str.capitalize,
                                    index=index_of(config.CATEGORY_KINDS, cat["kind"]))
        e_order = st.number_input("Order in lists", value=int(cat["sort_order"]), step=1,
                                  help="Lower numbers come first.")
        saved = st.form_submit_button("Save changes", type="primary")
    if saved:
        others = categories[categories["category_id"] != picked]["name"].str.lower().tolist()
        if not e_name.strip():
            st.error("The name can't be blank.")
        elif e_name.strip().lower() in others:
            st.error("There's already a category with that name.")
        else:
            data.update_category(picked, name=e_name, kind=e_kind, sort_order=int(e_order))
            done("Saved.", "edit_round")

    st.markdown(kind_badge(cat["kind"])
                + (f" {badge('gray', 'Archived')}" if cat["archived"] else ""))
    if cat["archived"]:
        if st.button("Unarchive", key=f"unarchive_{picked}"):
            data.archive_category(picked, archived=False)
            done(f"{cat['name']} is back in the pickers.")
    else:
        st.caption("Archiving hides a category from pickers; its transactions and budgets stay.")
        if st.button("Archive", key=f"archive_{picked}"):
            data.archive_category(picked)
            bump_round("pick_category")
            done(f"Archived {cat['name']}.")
