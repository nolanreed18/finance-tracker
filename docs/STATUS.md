---
updated: 2026-11-04
state: All nine planned pages, the Plaid bank feed, notifications and the Dark Desk look are merged; adding the standard app docs.
---

# Status

## Live

- What's on `main` deploys to Streamlit Community Cloud at the address in
  `app/config.py` (`APP_URL`). Latest change merged: PR #18 (Nov 3, 2026),
  after PR #17, the Dark Desk look (Nov 1, 2026). The app has no version
  numbers; the latest merged pull request is the version.
- All nine pages: Home, Accounts (with Payoff and Connected banks),
  Transactions, Budgets, Bills, Net worth, Goals, Stats, Import.
- Scheduled on GitHub Actions: bank sync (daily), notify (daily ping, Monday
  email), backup (Sundays). Tests run on every pull request.

## In progress

- This change: the five standard docs (`docs/`) and a check that every pull
  request changing the app updates `docs/STATUS.md` and `docs/HISTORY.md`.

## Next

The "later" list from the original plan, none started:

- A monthly review email, built by code.
- A scheduled Claude task that categorises imported transactions (it may
  reach the database only through one small allow-listed script over Neon's
  HTTPS endpoint).
- A year-in-review page.

## Needs the owner

- Check that the secrets each feature needs are set (names in the README;
  where they live: the mothership's `Studio/Secrets.md`): the database and
  sign-in in Streamlit, and the GitHub repository secrets for backup, bank
  sync and notifications. Until they're set, those jobs show red or do
  nothing.
- Link banks on the Accounts page once Plaid is set up.
- Decide which Google account sends the Monday email (see Known issues).

## Known issues

- **Which Gmail sends the weekly email isn't visible from the code.** It is
  whatever account the `GMAIL_ADDRESS` secret names. If that's still the
  owner's personal Gmail, it's due to move to the studio Gmail: change the
  `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` secrets.
- Not checked from here: whether the deployed app, the Plaid connection and
  the scheduled jobs are currently running green (no access to the live
  app, Actions run history or secrets from this repository's code).
- Signing in with the password doesn't survive a page reload; Google
  sign-in keeps you in for 30 days.
- Payoff interest runs slightly low once a card isn't paid in full (issuers
  then also charge interest on new purchases); the page says so.
- Schedules are set in UTC, so the jobs run an hour earlier by the clock in
  winter (CST) than in summer.
