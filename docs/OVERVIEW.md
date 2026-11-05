# Finance Tracker: overview

## What it is, and for whom

A private, phone-friendly money tracker for one person, the owner (Nolan):
where the money is, where it goes, what's due, and whether the plan is
working. It is a website only he can get into (Google sign-in limited to his
email, or a password).

## What it does

Nine pages, in sidebar order:

| Page | What it's for |
|---|---|
| **Home** | Net worth now, this month's spending against its budget, this month's savings rate, and **Needs attention**: bills due or overdue, budgets at 90% or over, balances not updated for 30 days, a bank that needs a new sign-in. |
| **Accounts** | Every place money lives or is owed (checking, savings, cards, loans, retirement, brokerage, cash, other). Closing instead of deleting. APR and a **Payoff** calculator for cards and loans. **Connected banks** (the Plaid bank feed). |
| **Transactions** | Every line of income, spending and transfers; filters and totals; add, edit, delete. |
| **Budgets** | Per-category budget for a month against what was spent; copy last month; manage categories. |
| **Bills** | Recurring bills and subscriptions, what's due or overdue, **Mark paid** (moves the date on and can log the payment). |
| **Net worth** | Assets minus liabilities, the month's balances in one form, a line by month. |
| **Goals** | Savings goals tracked by the balance of the account that holds the money. |
| **Stats** | Spending by category, income against spending for 12 months, savings rate, top payees. |
| **Import** | A bank or card CSV (Capital One, Discover, Amex, Chase and others), previewed, then added all at once; the same row never imports twice. |

Behind the scenes, three scheduled jobs on GitHub Actions:

- **Bank sync** (daily, 06:30 Chicago in summer): new transactions and
  balances from banks linked through Plaid (`sync.py`).
- **Notify** (daily, 07:00 Chicago in summer): a phone ping through ntfy.sh
  when a bill is due within 3 days or overdue, and on Mondays a summary
  email through Gmail (`notify.py`, words in `app/digest.py`).
- **Backup** (Sundays): every table to CSV, locked in a password-protected
  7z file, kept 90 days as a run artifact (`backup.py`).

## How it's built

- **Stack**: Python 3.13 and Streamlit for the pages; Postgres for the data.
- **Services**: Neon (hosted Postgres), Streamlit Community Cloud (hosting,
  deployed from the `main` branch), Google sign-in (`st.login`), Plaid (bank
  feed), ntfy.sh (phone pings), Gmail SMTP (the weekly email), GitHub
  Actions (tests, sync, notifications, backups).
- **Where it runs**: the app at the address in `app/config.py` (`APP_URL`)
  on Streamlit Community Cloud; the jobs on GitHub Actions.
- **Secrets**: named in the README and in `CLAUDE.md`, never written down
  here. Where each one lives and who holds it: the mothership's
  `Studio/Secrets.md` (github.com/nolanreed18/mothership).
- Started from `nolanreed18/app-template` (its `BLUEPRINT.md` is the source
  of the working rules); shares nothing with the owner's other apps at
  runtime.

## Where things live in the code

| Path | What it is |
|---|---|
| `app/Home.py`, `app/pages/` | The pages; the number in each filename is its menu order. |
| `app/data.py` | Every database read and write (all SQL), plus `MIGRATIONS`. |
| `app/logic.py` | The calculations, pure: no database, no Streamlit. |
| `app/digest.py` | The words of the ping and the weekly email, pure. |
| `app/config.py` | Settings worth tuning (bill window, budget warning, stale-balance days, account types). |
| `app/ui.py`, `app/theme.py` | Sign-in, cards, badges, sections; the dark and light looks. |
| `app/plaid_api.py` | The handful of Plaid calls. |
| `app/fresh.py` | Reloads stale modules after Community Cloud pulls new code. |
| `schema.sql`, `apply_schema.py` | The tables (created automatically on first connection). |
| `db.py` | Finds the database connection (never print it). |
| `sync.py`, `notify.py`, `backup.py` | The three scheduled jobs. |
| `.github/workflows/` | Tests, sync, notify, backup, and the docs check. |
| `tests/`, `conftest.py` | The tests (database tests need a throwaway Postgres). |

## Other documents

- [`README.md`](../README.md): first-time setup, running locally, bank sync,
  notifications, backups and tests, step by step.
- [`SEED.md`](../SEED.md): how to enter the first records.
- [`DESIGN.md`](../DESIGN.md): the Dark Desk style guide every screen follows.
- [`CLAUDE.md`](../CLAUDE.md): how to work in this repository.
- [`STATUS.md`](STATUS.md), [`DECISIONS.md`](DECISIONS.md),
  [`HISTORY.md`](HISTORY.md): where things stand, why they are the way they
  are, and what changed when.
