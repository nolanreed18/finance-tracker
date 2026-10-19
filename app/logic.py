"""Pure calculations over the frames data.py returns: net worth, budgets,
bills, the stats, formatting, and reading an imported bank file. No database
and no Streamlit, so all of it is tested directly.

Money is Decimal throughout, never float.
"""

import re
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd

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
