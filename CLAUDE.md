# Finance Tracker

A personal money tracker for one person: where the money is, where it goes,
what's due, and whether the plan is working. Streamlit (`app/`), Neon
Postgres, Streamlit Community Cloud from `main`. Built from
`nolanreed18/app-template` (its `BLUEPRINT.md` is the source of these rules);
it shares nothing with the owner's other apps at runtime. The owner is new to
GitHub and coding: explain in plain language, do the work yourself, and end
with a short numbered list of anything only they can do (accounts, secrets,
clicking merge).

## Rules
- `.env` holds `DATABASE_URL`. **Never read, print or copy it**; use `db.py`.
  A build session never uses a real database: a `DATABASE_URL` in a cloud
  environment belongs to some other app, so leave it alone and tell the owner.
- The repo and app are **public**. `ui.setup()` puts every page behind a
  sign-in: Google (`st.login`, only emails in the `ALLOWED_EMAILS` secret) or
  `APP_PASSWORD`. Every page calls it first, and it stays locked when neither
  is set up. Never commit data or secrets: `data/` and `*.csv` are gitignored.
  Backups are artifacts anyone signed in to GitHub can download: the workflow
  only ever uploads them inside a 7z file locked with `BACKUP_PASSWORD`.
- **Money is `numeric(12,2)` in Postgres and `Decimal` in Python, never
  float.** `logic.to_money()` turns typed or imported text into Decimal;
  `logic.money()` formats it. Transaction amounts are signed: income
  positive, spending negative. Balances are entered as the bank shows them
  (what's owed on a card or loan is positive) and net worth subtracts
  liabilities.
- **Never `current_date`, `now()` or the server timezone in SQL**: "today" is
  `data.today()` (America/Chicago), passed in. Dates are plain `date`s; a
  budget month is the first day of the month (`logic.month_start`).
- **All SQL lives in `app/data.py`**; calculations in `app/logic.py` (pure: no
  database, no Streamlit). Pages only lay out and call those two.
- **The look lives in `app/theme.py`**: a light palette (the default) and a dark
  one as Streamlit theme options, applied per run by `ui.setup()` from the
  `settings` table ("theme"), plus one stylesheet. `.streamlit/config.toml`
  must equal the light palette (`tests/test_theme.py` checks). Pages use
  `ui.card()`, `ui.empty()` and the badge helpers rather than emoji or raw
  HTML; colour means something (blue = in progress, green = good, orange =
  attention, red = overdue or bad, grey = neutral, yellow = unverified, such
  as a balance not updated for 30 days). Sub-pages are `ui.sections()` pills,
  never `st.tabs` (tabs forget their place on rerun); every delete goes
  through `ui.delete_button()` (tick box first); a "pick one" dropdown whose
  options can change takes `ui.round_key()` and `ui.bump_round()` after a
  delete, or it keeps showing the old choice.
- Knobs in `app/config.py`. **The lists are repeated in `schema.sql` CHECKs**
  (`ACCOUNT_TYPES`, `TRANSACTION_KINDS`, `CATEGORY_KINDS`, `CADENCES`):
  change both (tests fail if they drift). Add a table → add it to
  `backup.TABLES` and the `TABLES` list in `conftest.py`.
- `schema.sql` must stay re-runnable (`if not exists`): `data.py` runs it on the
  first connection of each process. Changing an existing table → also add an
  idempotent statement to `data.MIGRATIONS`, so the live database updates
  itself on the next connection.
- Imports are all-or-nothing (`data._transaction()`), and the same bank row
  never imports twice: its `import_key` is account, date, amount and the
  description lower-cased with punctuation dropped.
- Add forms sit behind `ui.disclosure()` buttons (server-side open state), not
  `st.expander`, which snaps shut when a click lands mid-load.
- Every page's first statement after `import streamlit` is `fresh.check()`:
  Community Cloud pulls new code into the running app but keeps old copies of
  `app/` modules loaded. Keep it first; a new page gets it too.
- Pass plain Python values to psycopg, not numpy (`int(x)` on DataFrame ids).
  Put user text into `st.markdown` through `ui.md()`: `$` would become maths,
  and this app is full of dollar signs.
- Forms reset by bumping a counter in their key; set a widget's session state
  only before it is drawn (or via a flag read at the top of the page).
- **The bank feed is Plaid**, through `app/plaid_api.py` only (thin: requests
  and their JSON; tests fake `plaid_api.post` or its functions). Plaid's
  shapes turn into our rows in `logic.plaid_rows`; `sync.py` (daily, in
  `.github/workflows/sync.yml`, and "Sync now" on Accounts) applies them with
  `data.apply_sync`, all or nothing, keyed `plaid:<transaction_id>` and also
  checked against the file-import key so a row never lands twice. Pending
  transactions wait until they post. Credentials are `PLAID_CLIENT_ID` and
  `PLAID_SECRET` (environment, or `st.secrets`); bank access tokens live in
  the `connections` table and are never printed or shown on a page.
- A scheduled Claude task (none yet; the categoriser is on the "later" list)
  reaches the database only through one small script over Neon's HTTPS
  endpoint (`db.HttpCursor`, `data.use_http()`), with its commands
  allow-listed in `.claude/settings.json`; any email it sends is rendered by
  code, not written by the model.

## Tests
- `ruff check .` and `python3 -m pytest` before every push. DB and page tests
  need `TEST_DATABASE_URL` (a throwaway Postgres; the cloud hook sets it, CI
  starts one). Never point it at Neon: `conftest.py` refuses, and the tests
  wipe it.
- Page tests use `streamlit.testing.v1.AppTest` against that database with
  `data.today` patched; every page gets a draws-empty and a draws-with-data
  test (`tests/test_pages.py` runs both for every file in `app/pages/`).
- Work on a branch and open a pull request; `main` is what's live.

## Plan
Pages, in sidebar order: Home, Accounts, Transactions, Budgets, Bills, Net
worth, Goals, Stats, Import, one pull request each. Later, not now: a monthly
review email built by code, a scheduled Claude task that categorises imported
transactions, and a year-in-review page.
