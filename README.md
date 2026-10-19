# Finance Tracker

A private, phone-friendly money tracker for one person: where the money is,
where it goes, what's due, and whether the plan is working. Streamlit front
end, Neon Postgres database, hosted free on Streamlit Community Cloud.

## What's in it

The app is being built one page per pull request. So far:

- **Home**: the sign-in, the Dark mode switch, and an empty **Needs
  attention** list. As the other pages arrive it gains three headline
  numbers (net worth, this month's spending against budget, this month's
  savings rate) and flags bills due in the next 7 days or overdue, budget
  categories over 90% for the month, and accounts with no balance update
  for 30 days.
- **Accounts**: every place your money lives or is owed (checking, savings,
  credit card, brokerage, retirement, loan, cash, other), with its bank,
  latest balance and when that was taken. Cards and loans are liabilities,
  which net worth subtracts. An account with history is **closed**, never
  deleted (and can be reopened); only an empty one can be deleted.
- **Transactions**: every line of income, spending and transfers between your
  own accounts, with a date, account, amount, category, payee and notes.
  Filter by month, account, category or a word in the payee or notes, and
  see income, spending and the net for whatever is shown. You type amounts
  as positive numbers; the kind decides the sign (spending is stored
  negative).
- **Budgets**: pick a month and see, per spending category, what you
  budgeted against what you spent as a bar with the amount left; **Close
  to budget** at 90%, **Over budget** at 100%. Set all the month's amounts
  in one form, or **Copy last month**. Categories (income and expense) are
  added, renamed and archived here.
- **Bills**: recurring bills and subscriptions with their amount, cadence
  (weekly, monthly, yearly), next due date, the account they're paid from
  and an autopay flag. **Due** from today through 7 days ahead, **Overdue**
  after. **Mark paid** moves the due date on one cadence and, if the box is
  ticked, logs the payment as a transaction. A bill can be paused.
- **Net worth**: assets minus liabilities from each open account's latest
  balance; a form that lists every open account with its last balance
  filled in, to save the month's balances in one go; a line of net worth by
  month; and a table of assets against liabilities.
- **Goals**: savings goals with a target amount, a date and the account that
  holds the money. Progress is that account's latest balance, with how much
  a month would reach the target in time. **Reached** when the balance
  covers it, or when you say so.
- **Stats**: spending by category for a chosen month (bars) and the last
  three months (a table), income against spending for 12 months, the
  savings-rate trend, and the top payees.
- **Import**: a CSV exported from your bank or card (or rows pasted in).
  Headers are matched loosely (date; description or payee; one signed
  amount column, or debit and credit columns; category), you see a preview
  with any problems, and the rows go in all at once or not at all. The
  same row (account, date, amount, description) never imports twice, so
  re-importing an overlapping file is safe.

Coming next: Home's headline numbers and Needs attention list.

Settings you might want to change (the 7-day bill window, the 90% budget
warning, the 30-day balance reminder, the account types) are in
`app/config.py`.

**Look and feel.** The app opens in a light look; the **Dark mode** switch in
the sidebar (tap ≫ at the top left on a phone) flips it, and the choice is
saved in the database, so every device follows. Both looks are defined in
`app/theme.py`; `.streamlit/config.toml` carries the light look so the first
paint already matches.

## First-time setup (once)

1. **Create the database.** Sign in at [neon.tech](https://neon.tech), click
   **New project**, and name it `finance-tracker`. Make it a new project,
   never a branch of another app's database. On the project dashboard click
   **Connect** and copy the connection string; it starts `postgresql://`.
   That string is the database's password: never paste it into a file that
   goes to GitHub.
2. **Add it to GitHub for the weekly backup.** In this repository go to
   **Settings → Secrets and variables → Actions → New repository secret**.
   Name it `DATABASE_URL` and paste the connection string as the value.
   Then add a second secret named `BACKUP_PASSWORD`: a long password you make
   up and **keep somewhere safe** (a password manager). The backups are locked
   with it, and without it they can't be opened.
3. **Put it online.** At [share.streamlit.io](https://share.streamlit.io)
   click **Create app** and deploy from GitHub:
   - **Repository:** `nolanreed18/finance-tracker`, **Branch:** `main`
   - **Main file path:** `app/Home.py`
   - **Advanced settings → Python version:** `3.13`
   - **Advanced settings → Secrets:**

     ```toml
     DATABASE_URL = "postgresql://…the string from Neon…"
     APP_PASSWORD = "a password you choose"
     ```

   The first time the app opens it creates its tables in the new database;
   there's nothing to run.
4. **Decide who can see it.** Streamlit's free plan allows one private app.
   Money is more sensitive than most things, so consider giving this app
   that private slot (in the app's **Settings → Sharing**). Either way the
   **sign-in screen** keeps your data private: every page asks you to sign in
   first, and the app stays locked if no way in is set up. Use a long
   password that you don't use anywhere else.
5. **Sign in with Google** (recommended before entering real numbers): see
   below.
6. **Test the backup.** On GitHub go to **Actions → Backup → Run workflow**. A
   green check means it worked; the encrypted file is on that run's page
   under **Artifacts**.

## Sign in with Google

Instead of typing the password, sign in with your Google account; Streamlit
keeps you signed in for 30 days on each device. Only the emails in
`ALLOWED_EMAILS` get in; any other Google account is turned away. The
password keeps working as a second way in.

1. In the [Google Cloud console](https://console.cloud.google.com), open the
   Google client you already use for your other apps (**Google Auth Platform
   → Clients**) and add this app's address as another **authorized redirect
   URI**: `https://<your-app>.streamlit.app/oauth2callback` (the address
   Streamlit gave the app in step 3, with `/oauth2callback` on the end).
   If you don't have a client yet: make a project, give it a name and your
   email (**Branding**), choose **External** and add your Gmail as a test
   user (**Audience**), then **Clients → Create client → Web application**.
2. In the app's Streamlit **Settings → Secrets**, add these. The plain lines
   must come **above** the `[auth]` line:

   ```toml
   DATABASE_URL = "…unchanged…"
   APP_PASSWORD = "…unchanged…"
   ALLOWED_EMAILS = "you@gmail.com"

   [auth]
   redirect_uri = "https://<your-app>.streamlit.app/oauth2callback"
   cookie_secret = "…a long random string you make up…"
   client_id = "…from Google…"
   client_secret = "…from Google…"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

## Running it on your computer

Python 3.13, to match `.python-version`. From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
streamlit run app/Home.py
```

It opens at `http://localhost:8501`. It needs a file named `.env` in this
folder with two lines, `DATABASE_URL=postgresql://…` (the string from Neon)
and `APP_PASSWORD=…` (the password the app asks for);
`.env` is never uploaded to GitHub. `Ctrl+C` stops it.

`python apply_schema.py` creates the tables by hand. The app does this itself,
and it's safe to run again: it never deletes anything.

## Backups

`.github/workflows/backup.yml` runs `backup.py` every Sunday morning (and
whenever you click **Run workflow**). It copies every table to CSV and locks
the CSVs in a password-protected file, `finance-tracker-backup.7z`, using
`BACKUP_PASSWORD`. That's needed because the repo is public, and anyone signed
in to GitHub can download a public repo's run files. GitHub keeps each run's
file for 90 days under **Actions → Backup → the run → Artifacts**. To open
one, unzip the download, then open the `.7z` file with
[7-Zip](https://www.7-zip.org) (Windows) or
[The Unarchiver](https://theunarchiver.com) or Keka (Mac) and type the backup
password. If a run fails, or `BACKUP_PASSWORD` isn't set, GitHub emails you. Run
`python backup.py` yourself for a copy in `data/backups/` on your computer;
`data/` is never uploaded to GitHub.

## Tests

```bash
ruff check .
python3 -m pytest
```

The page and database tests need a **throwaway** Postgres. They empty the
database they're given, so they look for `TEST_DATABASE_URL` and refuse any
Neon address. Without it they're skipped and only the pure-logic tests run.
GitHub Actions (`.github/workflows/tests.yml`) starts a throwaway Postgres
and runs everything on every pull request. Claude Code cloud sessions set one
up automatically (`.claude/hooks/session-start.sh`).

## How the files fit together

| File | What it is |
|---|---|
| `app/Home.py`, `app/pages/` | The pages. The number in each filename is its order in the menu. |
| `app/data.py` | Every database read and write. |
| `app/logic.py` | The calculations (net worth, budgets, bills, stats, import), with no database. |
| `app/config.py` | Settings. |
| `app/ui.py`, `app/theme.py` | Sign-in, cards, badges, and the light and dark looks. |
| `schema.sql`, `apply_schema.py` | The tables (created automatically when the app first connects), and a script to create them by hand. |
| `db.py` | Finds `DATABASE_URL` (in `.env`, or Streamlit secrets when online). |
| `backup.py` | Dumps every table to CSV. |
| `CLAUDE.md` | Rules for Claude when it works on this project. |
