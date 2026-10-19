"""Pure calculations over the frames data.py returns: net worth, budgets,
bills, the stats, formatting, and reading an imported bank file. No database
and no Streamlit, so all of it is tested directly.

Money is Decimal throughout, never float.
"""

import re
from datetime import date, time, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd

import config

CENT = Decimal("0.01")


def blank(value) -> bool:
    """None, NaN, NaT or empty text."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def value(x):
    """x, or None when blank -- for handing DataFrame cells back to Python."""
    return None if blank(x) else x


# ---- months -----------------------------------------------------------------

def month_start(d: date) -> date:
    """The first day of d's month: how budgets name a month."""
    return d.replace(day=1)


def add_months(d: date, n: int) -> date:
    """d moved n months (back when negative), its day kept where the month has
    it, else the month's last day (Jan 31 + 1 month = Feb 28)."""
    months = d.year * 12 + d.month - 1 + n
    year, month = divmod(months, 12)
    month += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError(d)  # unreachable: every month has a 28th


def month_label(d: date) -> str:
    return f"{d:%B %Y}"


def recent_months(today: date, n: int) -> list[date]:
    """The first days of this month and the n-1 before it, newest first."""
    this = month_start(today)
    return [add_months(this, -k) for k in range(n)]


# ---- money ------------------------------------------------------------------

def to_money(x) -> Decimal | None:
    """x as Decimal to the cent; None when blank. Text may carry a $ sign,
    commas and brackets for a negative ("($12.50)" is -12.50). Raises
    ValueError on anything else."""
    if blank(x):
        return None
    if isinstance(x, Decimal):
        number = x
    elif isinstance(x, (int, float)):
        number = Decimal(str(x))                  # str(): 0.1 stays 0.1
    else:
        text = str(x).strip().replace("$", "").replace(",", "").replace(" ", "")
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError(f"not an amount: {x!r}") from None
        if negative:
            number = -number
    if not number.is_finite():
        raise ValueError(f"not an amount: {x!r}")
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def money(n) -> str:
    """'$1,234.56', '−$12.00' (a real minus sign), '—' when blank."""
    n = to_money(n)
    if n is None:
        return "—"
    return f"−${-n:,.2f}" if n < 0 else f"${n:,.2f}"


def percent(share) -> str:
    """'42%' for 0.42; '—' when there is no share to show."""
    return "—" if share is None else f"{share:.0%}"


# ---- transactions -----------------------------------------------------------

def signed(amount, kind: str) -> Decimal:
    """The stored amount from what was typed: an expense is negative, income
    positive, a transfer keeps its sign (negative leaves the account)."""
    amount = to_money(amount) or Decimal("0.00")
    if kind == "expense":
        return -abs(amount)
    if kind == "income":
        return abs(amount)
    return amount


def totals(frame: pd.DataFrame) -> dict[str, Decimal]:
    """Income, spending (as a positive number), transfers (net) and the net
    of income minus spending, over a frame of transactions."""
    zero = Decimal("0.00")
    sums = {"income": zero, "spending": zero, "transfers": zero}
    for row in frame.itertuples(index=False):
        amount = to_money(row.amount) or zero
        if row.kind == "income":
            sums["income"] += amount
        elif row.kind == "expense":
            sums["spending"] -= amount
        else:
            sums["transfers"] += amount
    sums["net"] = sums["income"] - sums["spending"]
    return sums


def transaction_label(happened_on, payee, amount, account) -> str:
    """'Oct 12 · Grocer · −$42.10 · Checking', for the pick-one dropdown."""
    who = value(payee) or value(account) or ""
    tail = f" · {account}" if value(payee) and value(account) else ""
    return f"{happened_on:%b} {happened_on.day} · {who} · {money(amount)}{tail}"


# ---- bills ------------------------------------------------------------------

def next_due(due: date, cadence: str) -> date:
    """The due date one cadence on: a week, a month (same day where the
    month has it), or a year."""
    if cadence == "weekly":
        return due + timedelta(days=7)
    if cadence == "monthly":
        return add_months(due, 1)
    if cadence == "yearly":
        return add_months(due, 12)
    raise ValueError(f"unknown cadence {cadence!r}")


def bill_state(due, today: date, lookahead: int = config.BILL_LOOKAHEAD_DAYS) -> str | None:
    """'overdue' before today, 'due' from today through `lookahead` days,
    None when it's further off."""
    due = value(due)
    if due is None:
        return None
    if due < today:
        return "overdue"
    if due <= today + timedelta(days=lookahead):
        return "due"
    return None


def due_text(due: date, today: date) -> str:
    """'3 days overdue', 'due today', 'due tomorrow', 'due Tue Oct 20'."""
    late = (today - due).days
    if late > 0:
        return f"{plural(late, 'day')} overdue"
    return f"due {when(due, today)}"


def monthly_cost(amount, cadence: str) -> Decimal:
    """What a bill costs per month on average: weekly x 52/12, yearly / 12."""
    amount = to_money(amount) or Decimal("0")
    if cadence == "weekly":
        return (amount * 52 / 12).quantize(CENT, rounding=ROUND_HALF_UP)
    if cadence == "yearly":
        return (amount / 12).quantize(CENT, rounding=ROUND_HALF_UP)
    return amount


def bills_per_month(frame: pd.DataFrame) -> Decimal:
    """The average monthly cost of a frame of active bills."""
    total = Decimal("0.00")
    for row in frame.itertuples(index=False):
        total += monthly_cost(row.amount, row.cadence)
    return total


# ---- goals ------------------------------------------------------------------

def goal_progress(balance, target) -> tuple[Decimal, float]:
    """(saved, share) for a goal: the holding account's latest balance (zero
    when none) and how far it is to the target, 0.0 to 1.0 for a bar."""
    saved = to_money(balance) or Decimal("0.00")
    target = to_money(target)
    if target is None or target <= 0:
        return saved, 0.0
    return saved, float(max(Decimal("0"), min(saved / target, Decimal("1"))))


def goal_state(balance, target, target_on, today: date, reached_on=None) -> str:
    """'reached' (marked so, or the balance covers the target), 'late' when the
    target date has passed, 'on_track' otherwise."""
    if value(reached_on) is not None:
        return "reached"
    saved, share = goal_progress(balance, target)
    if share >= 1.0:
        return "reached"
    target_on = value(target_on)
    if target_on is not None and target_on < today:
        return "late"
    return "on_track"


def goal_pace(balance, target, target_on, today: date) -> str:
    """'$120.00 a month to reach it', '$300.00 to go', or '' when nothing is
    left or there's no date ahead."""
    saved, _ = goal_progress(balance, target)
    target = to_money(target) or Decimal("0")
    to_go = target - saved
    if to_go <= 0:
        return ""
    target_on = value(target_on)
    if target_on is None or target_on <= today:
        return f"{money(to_go)} to go"
    months = max(1, (target_on.year - today.year) * 12 + target_on.month - today.month)
    return f"{money((to_go / months).quantize(CENT, rounding=ROUND_HALF_UP))} a month to reach it"


# ---- budgets ----------------------------------------------------------------

def budget_state(budgeted, spent, warn: Decimal = config.BUDGET_WARN) -> str | None:
    """'over' at 100% of the budget, 'close' at BUDGET_WARN, 'ok' below;
    None when nothing is budgeted."""
    budgeted, spent = to_money(budgeted), to_money(spent) or Decimal("0")
    if budgeted is None or budgeted <= 0:
        return None
    if spent >= budgeted:
        return "over"
    if spent >= budgeted * warn:
        return "close"
    return "ok"


def budget_share(budgeted, spent) -> float:
    """Spent as a share of budgeted, for a progress bar: 0.0 to 1.0."""
    budgeted, spent = to_money(budgeted), to_money(spent) or Decimal("0")
    if budgeted is None or budgeted <= 0:
        return 0.0
    return float(max(Decimal("0"), min(spent / budgeted, Decimal("1"))))


def budget_summary(frame: pd.DataFrame) -> dict[str, Decimal]:
    """Budgeted and spent totals over a month's budget rows (data.budgets),
    and what's left, counting only budgeted categories' spending as "left"."""
    zero = Decimal("0.00")
    budgeted = spent = spent_budgeted = zero
    for row in frame.itertuples(index=False):
        b, s = to_money(row.budgeted), to_money(row.spent) or zero
        spent += s
        if b is not None:
            budgeted += b
            spent_budgeted += s
    return {"budgeted": budgeted, "spent": spent, "left": budgeted - spent_budgeted}


# ---- stats ------------------------------------------------------------------

UNCATEGORISED = "(uncategorised)"


def savings_rate(income, spending) -> Decimal | None:
    """(income - spending) / income, or None when there's no income."""
    income, spending = to_money(income) or Decimal("0"), to_money(spending) or Decimal("0")
    if income <= 0:
        return None
    return ((income - spending) / income).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def in_month(frame: pd.DataFrame, month: date) -> pd.DataFrame:
    """The transactions dated in a month (its first day)."""
    if frame.empty:
        return frame
    end = add_months(month, 1)
    return frame[(frame["happened_on"] >= month) & (frame["happened_on"] < end)]


def spending_by_category(frame: pd.DataFrame) -> pd.DataFrame:
    """Expense totals per category over a frame of transactions, as positive
    numbers, biggest first; uncategorised spending is one row of its own.
    Columns: category, spent."""
    columns = ["category", "spent"]
    expenses = frame[frame["kind"] == "expense"] if not frame.empty else frame
    if expenses.empty:
        return pd.DataFrame(columns=columns)
    sums: dict[str, Decimal] = {}
    for row in expenses.itertuples(index=False):
        name = value(row.category) or UNCATEGORISED
        sums[name] = sums.get(name, Decimal("0.00")) - (to_money(row.amount) or Decimal("0"))
    rows = sorted(sums.items(), key=lambda kv: (-kv[1], kv[0]))
    return pd.DataFrame(rows, columns=columns)


def category_by_month(frame: pd.DataFrame, months: list[date]) -> pd.DataFrame:
    """Spending per category (rows) for each month (columns, labelled "Oct
    2026"), with a Total column, biggest total first. Empty when nothing was
    spent in those months."""
    labels = [f"{m:%b %Y}" for m in months]
    table: dict[str, dict[str, Decimal]] = {}
    for m, label in zip(months, labels):
        for row in spending_by_category(in_month(frame, m)).itertuples(index=False):
            table.setdefault(row.category, {})[label] = row.spent
    if not table:
        return pd.DataFrame(columns=["category", *labels, "Total"])
    zero = Decimal("0.00")
    rows = [{"category": name, **{label: cells.get(label, zero) for label in labels},
             "Total": sum(cells.values(), zero)} for name, cells in table.items()]
    rows.sort(key=lambda r: (-r["Total"], r["category"]))
    return pd.DataFrame(rows, columns=["category", *labels, "Total"])


def monthly_flows(frame: pd.DataFrame, months: list[date]) -> pd.DataFrame:
    """Income, spending, net and savings rate for each month given (oldest
    first), zeros for quiet months. Columns: month, income, spending, net,
    savings_rate (None when no income)."""
    rows = []
    for m in sorted(months):
        sums = totals(in_month(frame, m))
        rows.append((m, sums["income"], sums["spending"], sums["net"],
                     savings_rate(sums["income"], sums["spending"])))
    return pd.DataFrame(rows, columns=["month", "income", "spending", "net", "savings_rate"])


def top_payees(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Where the spending went: payees by total spent (positive), biggest
    first, with how many transactions each. Columns: payee, spent, count."""
    columns = ["payee", "spent", "count"]
    expenses = frame[frame["kind"] == "expense"] if not frame.empty else frame
    if expenses.empty:
        return pd.DataFrame(columns=columns)
    sums: dict[str, list] = {}
    for row in expenses.itertuples(index=False):
        name = value(row.payee) or "(no payee)"
        entry = sums.setdefault(name, [Decimal("0.00"), 0])
        entry[0] -= to_money(row.amount) or Decimal("0")
        entry[1] += 1
    rows = sorted(((name, spent, count) for name, (spent, count) in sums.items()),
                  key=lambda r: (-r[1], r[0]))[:limit]
    return pd.DataFrame(rows, columns=columns)


# ---- accounts ---------------------------------------------------------------

def net_worth_now(accounts: pd.DataFrame) -> dict[str, Decimal]:
    """Assets, liabilities (as a positive number) and net worth from the
    latest balance of each open account (data.accounts' balance column);
    accounts with no balance count as nothing."""
    zero = Decimal("0.00")
    assets = liabilities = zero
    for row in accounts.itertuples(index=False):
        if not blank(row.closed_on):
            continue
        amount = to_money(row.balance)
        if amount is None:
            continue
        if row.is_liability:
            liabilities += amount
        else:
            assets += amount
    return {"assets": assets, "liabilities": liabilities, "net": assets - liabilities}


def net_worth_history(balances: pd.DataFrame) -> pd.DataFrame:
    """Net worth at the end of every month from the first balance to the
    last: each account's latest balance up to that month end, liabilities
    negative, counting an account until the month it was closed. Columns:
    month (first day), assets, liabilities, net_worth."""
    columns = ["month", "assets", "liabilities", "net_worth"]
    if balances.empty:
        return pd.DataFrame(columns=columns)
    first = month_start(min(balances["as_of"]))
    last = month_start(max(balances["as_of"]))
    months = []
    m = first
    while m <= last:
        months.append(m)
        m = add_months(m, 1)
    zero = Decimal("0.00")
    rows = []
    for m in months:
        end = add_months(m, 1)
        latest: dict[int, tuple] = {}
        for row in balances.itertuples(index=False):
            if row.as_of >= end:
                continue
            closed = value(row.closed_on)
            if closed is not None and closed < m:
                continue                      # closed before this month began
            key = int(row.account_id)
            if key not in latest or row.as_of >= latest[key][0]:
                latest[key] = (row.as_of, to_money(row.amount) or zero, bool(row.is_liability))
        assets = sum((amt for _, amt, owed in latest.values() if not owed), zero)
        liabilities = sum((amt for _, amt, owed in latest.values() if owed), zero)
        rows.append((m, assets, liabilities, assets - liabilities))
    return pd.DataFrame(rows, columns=columns)


def stale_balance(as_of, today: date, days: int = config.STALE_BALANCE_DAYS) -> bool:
    """An account whose latest balance is `days` old or more, or that has none,
    is due an update."""
    as_of = value(as_of)
    return as_of is None or (today - as_of).days >= days


def balance_age(as_of, today: date) -> str:
    """'updated today', 'updated 3 days ago', 'updated Sep 2', or 'no balance yet'."""
    as_of = value(as_of)
    if as_of is None:
        return "no balance yet"
    days = (today - as_of).days
    if days <= 0:
        return "updated today"
    if days < 14:
        return f"updated {plural(days, 'day')} ago"
    return f"updated {as_of:%b} {as_of.day}" + ("" if as_of.year == today.year else f", {as_of.year}")


# ---- formatting -------------------------------------------------------------

def for_display(frame: pd.DataFrame, dates: tuple[str, ...] = (),
                amounts: tuple[str, ...] = ()) -> pd.DataFrame:
    """A copy for st.dataframe: missing text shows as blank rather than "None",
    the named date columns become real dates (blank when missing), and the
    named money columns become numbers st.dataframe can format and sort."""
    out = frame.copy()
    for column in out.columns:
        if column in dates:
            out[column] = pd.to_datetime(out[column], errors="coerce")
        elif column in amounts:
            out[column] = pd.to_numeric(out[column].map(to_money), errors="coerce")
        elif out[column].dtype == object or pd.api.types.is_string_dtype(out[column]):
            out[column] = out[column].fillna("")
    return out


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def when(d: date, today: date) -> str:
    days = (d - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    return f"{d:%a %b} {d.day}"


def clock(t: time) -> str:
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'am' if t.hour < 12 else 'pm'}"


# ---- bank file import -------------------------------------------------------

# Headers each field is recognised by, compared lower-case with underscores
# and dashes as spaces. A file has one signed amount column, or separate
# debit and credit columns.
ALIASES = {
    "date": ["date", "transaction date", "posted date", "posting date", "trans date",
             "post date"],
    "description": ["description", "payee", "merchant", "name", "memo", "details",
                    "transaction description"],
    "amount": ["amount", "transaction amount", "amount usd", "net amount"],
    "debit": ["debit", "debits", "withdrawal", "withdrawals", "money out", "debit amount"],
    "credit": ["credit", "credits", "deposit", "deposits", "money in", "credit amount"],
    "category": ["category", "type of spend", "spending category"],
}


def _norm(header: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(header)).strip().lower()


def match_columns(headers, aliases: dict[str, list[str]] = ALIASES) -> dict[str, str]:
    """{field: file header} for every field a header was found for."""
    by_norm = {_norm(h): h for h in headers}
    found = {}
    for field, names in aliases.items():
        for name in names:
            if name in by_norm and by_norm[name] not in found.values():
                found[field] = by_norm[name]
                break
    return found


def words(text) -> str:
    """Text lower-cased with punctuation and extra spaces dropped, so "CAFE
    #12 - Main St." and "cafe 12 main st" match."""
    return " ".join(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def import_key(account_id: int, happened_on: date, amount, description) -> str:
    """What makes an imported row the same row: its account, date, amount and
    description (lower-cased, punctuation dropped). A row with this key
    already stored never imports again."""
    return f"{account_id}|{happened_on.isoformat()}|{to_money(amount)}|{words(description)}"


def read_csv(text: str) -> pd.DataFrame:
    """A bank file's rows from its text, every cell as text (so amounts and
    dates are read by map_import, not guessed by pandas). Blank lines and
    a byte-order mark are ignored; raises ValueError when there's no table."""
    from io import StringIO

    body = text.lstrip("\ufeff").strip()
    if not body:
        raise ValueError("The file is empty.")
    try:
        frame = pd.read_csv(StringIO(body), dtype=str, skip_blank_lines=True,
                            skipinitialspace=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"Couldn't read that as a CSV file: {exc}") from None
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def map_import(frame: pd.DataFrame, account_id: int, categories: dict[str, int] | None = None,
               flip_signs: bool = False) -> tuple[list[dict], list[str]]:
    """Rows ready for data.import_transactions, and a note for each problem.

    The file needs a date column, a description column and either one
    amount column (signed) or debit and credit columns. Spending must come
    out negative: tick flip_signs for a card statement that lists charges as
    positive numbers. A row's category is matched to yours by name (any
    capitalisation); unknown ones are left blank. Row numbers in the notes
    are file rows (the header is row 1).
    """
    columns = match_columns(frame.columns)
    problems = []
    if "date" not in columns:
        problems.append("No date column found — expected a header like “Date”.")
    if "description" not in columns:
        problems.append("No description column found — expected a header like “Description” "
                        "or “Payee”.")
    if "amount" not in columns and not ("debit" in columns or "credit" in columns):
        problems.append("No amount column found — expected “Amount”, or “Debit” and “Credit”.")
    if problems:
        return [], problems
    lookup = {name.lower(): cid for name, cid in (categories or {}).items()}
    unknown_categories: set[str] = set()

    def cell(row, field):
        header = columns.get(field)
        return None if header is None else value(row[header])

    rows, seen = [], set()
    for index, row in frame.iterrows():
        line = index + 2 if isinstance(index, int) else index
        if all(blank(v) for v in row.values):
            continue
        raw_date = cell(row, "date")
        parsed = pd.to_datetime(raw_date, errors="coerce") if raw_date is not None else pd.NaT
        if pd.isna(parsed):
            problems.append(f"Row {line}: skipped — couldn't read the date “{raw_date}”.")
            continue
        try:
            if "amount" in columns:
                amount = to_money(cell(row, "amount"))
            else:
                debit = to_money(cell(row, "debit")) or Decimal("0")
                credit = to_money(cell(row, "credit")) or Decimal("0")
                amount = credit - abs(debit)
                if blank(cell(row, "debit")) and blank(cell(row, "credit")):
                    amount = None
        except ValueError:
            problems.append(f"Row {line}: skipped — couldn't read the amount.")
            continue
        if amount is None:
            problems.append(f"Row {line}: skipped — no amount.")
            continue
        if flip_signs:
            amount = -amount
        description = str(cell(row, "description") or "").strip()
        category_id = None
        if (raw_category := cell(row, "category")) is not None:
            category_id = lookup.get(str(raw_category).strip().lower())
            if category_id is None:
                unknown_categories.add(str(raw_category).strip())
        key = import_key(account_id, parsed.date(), amount, description)
        if key in seen:
            problems.append(f"Row {line}: skipped — the same as an earlier row in this file.")
            continue
        seen.add(key)
        rows.append({
            "account_id": account_id, "happened_on": parsed.date(), "amount": amount,
            "kind": "income" if amount > 0 else "expense", "category_id": category_id,
            "payee": description or None, "import_key": key,
        })
    if unknown_categories:
        shown = ", ".join(sorted(unknown_categories)[:5])
        problems.append(f"Categories not in your list were left blank: {shown}"
                        + ("…" if len(unknown_categories) > 5 else "."))
    return rows, problems
