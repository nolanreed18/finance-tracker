# History

Newest first. Dates are America/Chicago.

- **2026-11-05**: Needs the owner: open every page of the live app and make
  a test account (the unfinished launch checks 5–8).
- **2026-11-05**: Handoff notes written down: the live-app checks stopped
  at check 4 (Known issues); copying Dark Desk into the app template is
  open (Next); CLAUDE.md now says to check a pull request's status yourself,
  since GitHub's "check finished" notice can fail to arrive.

- **2026-11-04**: Backups now work: `BACKUP_PASSWORD` is set and a manual
  Backup run succeeded (first good run). STATUS updated.
- **2026-11-04**: STATUS checked against the Actions run logs: backups have
  never run (no `BACKUP_PASSWORD`), and the bank sync, phone ping and Monday
  email are not switched on (their secrets are empty), though the sync and
  notify runs show green. Needs the owner now lists the secrets to add.
- **2026-11-04**: The standard app docs (`docs/OVERVIEW.md`, `STATUS.md`,
  `DECISIONS.md`, `HISTORY.md`) and a check that every pull request
  changing the app updates STATUS and HISTORY. The "Plan" in CLAUDE.md
  moved to STATUS.
- **2026-11-03**: CLAUDE.md: standing approval to merge your own green PR;
  no leftover scheduled tasks (#18).
- **2026-11-01**: The look follows the Dark Desk style guide (`DESIGN.md`);
  dark is the default, light is the companion (#17).
- **2026-10-19**: Notifications: the morning phone ping (ntfy.sh) and the
  Monday email (Gmail), built by `app/digest.py` (#16).
- **2026-10-19**: APR on accounts and a Payoff calculator for cards and
  loans; migration adds `accounts.apr` (#15).
- **2026-10-19**: Bank feed part 2: Connected banks on the Accounts page;
  Home flags a bank needing sign-in (#14).
- **2026-10-19**: Bank feed part 1: Plaid client, `connections` and
  `connected_accounts` tables, daily `sync.py`; migration adds
  `transactions.source_category` (#13).
- **2026-10-19**: Import reads Capital One, Discover, Amex and Chase files;
  card payments import as transfers (#12).
- **2026-10-19**: `SEED.md`, how to enter the first records (#11).
- **2026-10-19**: Home page: headline numbers and Needs attention (#10).
- **2026-10-19**: Import page: CSV preview, all-or-nothing, never twice (#9).
- **2026-10-19**: Stats page (#8).
- **2026-10-19**: Goals page (#7).
- **2026-10-19**: Net worth page (#6).
- **2026-10-19**: Bills page (#5).
- **2026-10-19**: Budgets page (#4).
- **2026-10-19**: Transactions page (#3).
- **2026-10-19**: Accounts page (#2).
- **2026-10-19**: The skeleton: template files, schema, sign-in, empty Home,
  tests, weekly encrypted backup (#1).
