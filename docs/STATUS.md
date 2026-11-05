---
updated: 2026-11-05
state: The app and its pages are live and backups now work (first good run Nov 4), but the bank feed, phone ping and Monday email are not switched on yet (their GitHub secrets are empty).
---

# Status

Checked against the GitHub Actions run logs on Nov 4, 2026, not guessed.

## Live

- What's on `main` deploys to Streamlit Community Cloud at the address in
  `app/config.py` (`APP_URL`). Latest change merged: PR #19, the standard
  docs (Nov 4, 2026). The app has no version numbers; the latest merged pull
  request is the version.
- All nine pages: Home, Accounts (with Payoff and Connected banks),
  Transactions, Budgets, Bills, Net worth, Goals, Stats, Import.
- The database secret is set for GitHub Actions, and the daily jobs reach the
  database.
- **Bank sync** (daily): runs green (last green: Nov 4, 2026), but every run
  says "no banks linked yet": the Plaid secrets are empty, so no bank is
  connected and nothing is synced. Transactions come in only by Import or
  by hand.
- **Notify** (daily): runs green on most days (last green: Nov 4, 2026), but
  only because there was nothing to ping about. The ntfy and Gmail secrets
  are empty, so no ping or email can be sent. The one Monday run so far
  (Nov 2) failed: "GMAIL_ADDRESS and GMAIL_APP_PASSWORD are not both set".
- **Backup** (Sundays, 11:00 UTC): **works now**. `BACKUP_PASSWORD` was set
  on Nov 4 and a manual run succeeded that night (first success, Nov 4). The
  three earlier Sunday runs (Oct 19, Oct 25, Nov 1) had failed for want of
  it. Next scheduled run: Sunday Nov 8, 11:00 UTC. Nothing for the owner to
  do here.
- **Tests** and the **docs check** run on every pull request and pass.

## In progress

Nothing.

## Next

The "later" list from the original plan, none started:

- A monthly review email, built by code.
- A scheduled Claude task that categorises imported transactions (it may
  reach the database only through one small allow-listed script over Neon's
  HTTPS endpoint).
- A year-in-review page.

Also open:

- **Copy the dark look ("Dark Desk") into the studio's app template**
  (`nolanreed18/app-template`), so new apps start with it. Offered, not
  started: nothing done yet.

## Needs the owner

Repository secrets are added at GitHub → this repository → Settings →
Secrets and variables → Actions. Where each value lives: the mothership's
`Studio/Secrets.md`.

1. **Turn on the Monday email:** add `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`,
   on the **studio Gmail**, not the personal one. This waits for the studio
   Gmail's two-step verification (Google app passwords need it; due Nov 11).
   Nothing has been sent from any address yet, so it can start on the studio
   account.
2. **Turn on the phone ping:** add `NTFY_TOPIC`.
3. **Turn on the bank feed** if still wanted: add `PLAID_CLIENT_ID` and
   `PLAID_SECRET` as repository secrets and in the app's Streamlit secrets,
   then link each bank on the Accounts page.
4. **Open every page of the live app once and make a test account** (checks
   5–8 of the Nov launch list were never run). A build session can't sign
   in to the live app; sign-ins are yours.

## Known issues

- The studio's notes say the bank sync and alerts have been live for a
  while; the run logs say otherwise (see Live). The green ticks hide that,
  because a missing Plaid or ntfy secret doesn't make the run fail.
- Scheduled runs start hours late: the bank sync is set for 11:30 UTC and
  notify for 12:00 UTC, but recent runs started between about 16:00 and 21:30 UTC.
  GitHub delays scheduled jobs on busy days; the order (sync before notify)
  has held so far.
- Not checked from here: the deployed app itself and its Streamlit secrets
  (sign-in, Plaid). No access to the live app.
- **The live app has never been fully checked.** The live-app checks
  stopped partway through check 4 (reloading a page signs you out of a
  password sign-in); checks 5–8 were never run. So nobody has yet opened
  every page on the live app or made a test account there.
- Signing in with the password doesn't survive a page reload; Google
  sign-in keeps you in for 30 days.
- Payoff interest runs slightly low once a card isn't paid in full (issuers
  then also charge interest on new purchases); the page says so.
