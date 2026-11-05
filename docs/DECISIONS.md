# Decisions

Each rule or choice as it stands now, why, and how it got there. Dates are
America/Chicago. When a decision changes, rewrite "Now" and add a line to
its history; don't delete the history.

## Stack: Streamlit, Neon Postgres, Streamlit Community Cloud

**Now:** Streamlit pages in `app/`, a Neon Postgres database of its own (a
new Neon project, never a branch of another app's), hosted free on Streamlit
Community Cloud from `main`.
**Why:** the owner's app template; free hosting; one person's data fits a
small Postgres.
**History:** 2026-10-19, set up from `nolanreed18/app-template` (PR #1).

## Public repo and app, everything behind a sign-in

**Now:** the repository and app are public, so every page calls
`ui.setup()` first, which asks for Google sign-in (only emails in
`ALLOWED_EMAILS`) or `APP_PASSWORD`, and stays locked when neither is set.
No data or secrets are committed (`data/` and `*.csv` are gitignored).
**Why:** free hosting needs a public repo; the data is money, so nothing
shows without signing in.
**History:** 2026-10-19, from the template (PR #1). The README suggests
also giving this app Streamlit's one private-app slot.

## Backups encrypted, weekly

**Now:** `backup.py` every Sunday on GitHub Actions; the CSVs are only ever
uploaded inside a 7z file locked with `BACKUP_PASSWORD`, kept 90 days.
**Why:** anyone signed in to GitHub can download a public repo's run files.
**History:** 2026-10-19, from the template (PR #1).

## Money is exact: numeric(12,2) and Decimal, never float

**Now:** money is `numeric(12,2)` in Postgres and `Decimal` in Python;
`logic.to_money()` reads text, `logic.money()` formats it. Transaction
amounts are signed (income positive, spending negative); you type a positive
amount and the kind decides the sign. Balances are entered as the bank shows
them (a card's debt is positive) and net worth subtracts liabilities.
**Why:** floats lose cents; entering balances the bank's way avoids sign
mistakes.
**History:** 2026-10-19, PR #1 and PR #3.

## "Today" is Chicago, passed in

**Now:** never `current_date`, `now()` or the server's timezone in SQL;
"today" is `data.today()` (America/Chicago). A budget month is the first
day of the month.
**Why:** the servers run in UTC, so late-evening entries would land on
tomorrow.
**History:** 2026-10-19, PR #1.

## Code layout: SQL in data.py, maths in logic.py, pages only lay out

**Now:** all SQL in `app/data.py`; calculations in `app/logic.py` (and the
notification words in `app/digest.py`), pure; pages call those two.
**Why:** the maths can be tested without a database or a browser.
**History:** 2026-10-19, PR #1; `digest.py` added 2026-10-19, PR #16.

## Schema updates itself

**Now:** `schema.sql` is re-runnable and runs on each process's first
connection; changes to existing tables also go in `data.MIGRATIONS`. The
config lists are repeated as CHECKs in `schema.sql` and tests catch drift.
**Why:** nothing to run by hand after a deploy.
**History:** 2026-10-19, PR #1. Migrations added: `source_category` on
transactions (PR #13), `apr` on accounts (PR #15).

## Imports are all-or-nothing and never twice

**Now:** a file import goes in in one transaction. The dedupe key is
account, date, amount and the description lower-cased with punctuation
dropped. On a card or loan, a positive "payment" row imports as a transfer;
"Spending is positive" ticks itself from the sign of the payment rows.
**Why:** re-importing an overlapping file must be safe; card payments
counted as income would inflate the savings rate.
**History:** 2026-10-19, Import page (PR #9); card files from Capital One,
Discover, Amex and Chase handled (PR #12).

## Bank feed: Plaid, synced daily

**Now:** Plaid through `app/plaid_api.py` only; `sync.py` runs daily and on
"Sync now", applies changes all or nothing, keyed `plaid:<transaction_id>`
and also checked against the file-import key. Pending transactions wait
until they post. Bank access tokens live in the database and are never
shown.
**Why:** saves the monthly CSV routine; never-twice keeps hand imports and
the feed from doubling up.
**History:** 2026-10-19, plumbing and daily sync (PR #13), Connected banks
on the Accounts page (PR #14).

## Notifications built by code

**Now:** `app/digest.py` writes the morning ping (ntfy.sh, bills due within
3 days or overdue, a bank needing sign-in) and the Monday email (Gmail SMTP
with an app password); `notify.py` sends each at most once a day. The email
is email-safe and escapes user text.
**Why:** what the messages say is tested; a re-run never double-sends.
**History:** 2026-10-19, PR #16.

## The look: Dark Desk, dark by default

**Now:** all UI follows `DESIGN.md` (Dark Desk), adapted to Streamlit as its
preface says. The look lives in `app/theme.py` (tokens only, no inline hex);
dark is the default with a light companion behind the Dark mode switch,
saved in the database. Numbers are mono and tabular; missing is `—`; colour
means something.
**Why:** the owner supplied the guide as the standard.
**History:** 2026-10-19, light by default from the template (PR #1).
2026-11-01, Dark Desk adopted and dark made the default, on purpose unlike
the template (PR #17).

## Streamlit quirks we work around

**Now:** sub-pages are `ui.sections()` pills, not `st.tabs`; add forms sit
behind `ui.disclosure()`, not `st.expander`; every delete has a tick box;
every page starts with `fresh.check()`; user text goes through `ui.md()`.
**Why:** tabs and expanders lose their state on rerun; Community Cloud keeps
old modules loaded after an update; `$` turns into maths in markdown.
**History:** 2026-10-19, PR #1 onward.

## Working rules for Claude sessions

**Now:** work on a branch, open a pull request, merge your own once the
check is green (standing approval). Don't leave scheduled tasks behind.
Every pull request that changes the app updates `docs/STATUS.md` and
`docs/HISTORY.md`, enforced by `.github/workflows/docs-check.yml` (label
`no-docs` for tooling-only changes).
**Why:** `main` is live; the repository, not any one chat, is the memory.
**History:** 2026-11-03, standing merge approval and no leftover tasks
written down (PR #18). 2026-11-04, the studio's five-docs standard and the
docs check (this change).
