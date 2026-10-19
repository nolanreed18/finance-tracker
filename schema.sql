-- Finance tracker schema. Safe to re-run: apply_schema.py runs this whole file
-- and every statement is "if not exists".
--
-- Dates are plain `date`s in America/Chicago, computed in Python and passed in.
-- Nothing here defaults to current_date or now(). Money is numeric(12,2). The
-- type / kind / cadence lists are repeated from app/config.py; change both
-- together.

create table if not exists accounts (
    account_id    bigint generated always as identity primary key,
    name          text not null check (btrim(name) <> ''),
    kind          text not null check (kind in
                    ('checking', 'savings', 'credit card', 'brokerage', 'retirement',
                     'loan', 'cash', 'other')),
    institution   text,
    -- Money owed (a card, a loan): its balance counts against net worth.
    is_liability  boolean not null default false,
    opened_on     date,
    closed_on     date,              -- closed accounts keep their history
    apr           numeric(5,2) check (apr >= 0),   -- yearly interest rate, %, for what's owed
    notes         text,
    check (closed_on is null or opened_on is null or closed_on >= opened_on)
);
-- One account per name, whatever the capitalisation.
create unique index if not exists accounts_name_key on accounts (lower(name));

create table if not exists categories (
    category_id  bigint generated always as identity primary key,
    name         text not null check (btrim(name) <> ''),
    kind         text not null check (kind in ('income', 'expense')),
    archived     boolean not null default false,  -- hidden from pickers, history kept
    sort_order   integer not null default 0
);
create unique index if not exists categories_name_key on categories (lower(name));

-- Amounts are signed: income positive, spending negative.
create table if not exists transactions (
    transaction_id  bigint generated always as identity primary key,
    -- An account with transactions cannot be deleted: close it instead.
    account_id      bigint not null references accounts on delete restrict,
    happened_on     date not null,
    amount          numeric(12,2) not null,
    kind            text not null check (kind in ('income', 'expense', 'transfer')),
    category_id     bigint references categories on delete set null,
    payee           text,
    notes           text,
    -- Imported rows only: account|date|amount|description (logic.import_key),
    -- so the same bank row never imports twice.
    import_key      text unique,
    -- What the bank's data feed called it (Plaid's category), for the
    -- categoriser; blank for rows typed or imported by hand.
    source_category text,
    created_on      date not null
);
create index if not exists transactions_happened_on on transactions (happened_on);
create index if not exists transactions_account on transactions (account_id);

-- What you plan to spend per category per month.
create table if not exists budgets (
    budget_id    bigint generated always as identity primary key,
    month        date not null check (extract(day from month) = 1),  -- first of the month
    category_id  bigint not null references categories on delete cascade,
    amount       numeric(12,2) not null check (amount >= 0),
    unique (month, category_id)
);

-- Recurring bills and subscriptions. Marking one paid moves next_due_on on
-- by one cadence.
create table if not exists bills (
    bill_id      bigint generated always as identity primary key,
    name         text not null check (btrim(name) <> ''),
    amount       numeric(12,2) not null check (amount >= 0),
    cadence      text not null check (cadence in ('weekly', 'monthly', 'yearly')),
    next_due_on  date not null,
    account_id   bigint references accounts on delete set null,
    autopay      boolean not null default false,
    category_id  bigint references categories on delete set null,
    active       boolean not null default true,
    notes        text
);

-- An account's balance on a day, as the bank shows it: what you owe on a card
-- or loan is a positive number (net worth subtracts it).
create table if not exists balances (
    balance_id  bigint generated always as identity primary key,
    -- An account with balances cannot be deleted: close it instead.
    account_id  bigint not null references accounts on delete restrict,
    as_of       date not null,
    amount      numeric(12,2) not null,
    unique (account_id, as_of)
);

-- Savings goals; progress is the latest balance of the account holding it.
create table if not exists goals (
    goal_id        bigint generated always as identity primary key,
    name           text not null check (btrim(name) <> ''),
    target_amount  numeric(12,2) not null check (target_amount > 0),
    target_on      date,
    account_id     bigint references accounts on delete set null,
    note           text,
    reached_on     date
);

-- A bank linked through Plaid: one row per sign-in at a bank (a Plaid
-- "item"). The access token is what reads that bank; it lives here, with
-- the data it unlocks, and is removed with the connection. The cursor is
-- where the daily sync left off.
create table if not exists connections (
    connection_id     bigint generated always as identity primary key,
    provider          text not null default 'plaid' check (provider in ('plaid')),
    item_id           text not null unique,
    access_token      text not null,
    institution_name  text,
    cursor            text,
    linked_on         date not null,
    last_synced_on    date,
    last_error        text              -- e.g. ITEM_LOGIN_REQUIRED: sign in again
);

-- The bank's accounts under a connection, each matched to one of ours (or
-- not yet: account_id null means "don't sync this one").
create table if not exists connected_accounts (
    connected_account_id  bigint generated always as identity primary key,
    connection_id         bigint not null references connections on delete cascade,
    provider_account_id   text not null unique,
    account_id            bigint references accounts on delete set null,
    name                  text not null,
    mask                  text,            -- last four digits
    kind                  text,            -- the bank's type: depository, credit, loan...
    subtype               text             -- checking, credit card...
);

-- App settings, one row per key: "theme" is "light" or "dark".
create table if not exists settings (
    key    text primary key,
    value  text not null
);
