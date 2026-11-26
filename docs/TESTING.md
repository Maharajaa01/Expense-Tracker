# Testing

Four layers. All of them clean up after themselves and can run against the
shared production site.

## 1. Backend (149 tests)

`expense_tracker/tests/`: ledger and accounting rules, validation, data
isolation between users, every API, budgets and alerts, recurring schedules
(month ends, leap years, catch-up, idempotency), savings goals, insights,
offline sync (idempotency, conflicts, partial failure), receipts (file-type
checks, privacy), CSV import/export, bank alert emails (parsing, posting, duplicates, learning,
read-only mailbox access with a fake IMAP server).

```bash
# Shared / live site: no scheduler toggling, no global test records,
# any commit() fails the run, every test rolls back.
bench --site admin.dreamtechsolution.com execute expense_tracker.tests.live_runner.run

# One file
bench --site <site> execute expense_tracker.tests.live_runner.run --kwargs "{'pattern': 'test_sync.py'}"

# CI / throwaway site
bench --site test_site run-tests --app expense_tracker
```

Do not use `bench run-tests` on a shared site: it disables the site-wide
scheduler while it runs.

## 2. Frontend unit tests (43 tests)

Vitest + happy-dom (+ fake-indexeddb): money formatting and input parsing,
dates, components (amount colours, keyboard navigation, accessibility
attributes), the offline queue and sync engine, the install button state, and
HTML escaping in chart tooltips.

```bash
cd frontend && yarn test:run
```

## 3. End-to-end (21 tests, Playwright)

`frontend/e2e/`: Quick Add from the keyboard, double-submit protection, edit
and delete with balance checks, credit card bill payments, installability and
offline use (offline reload, offline entry, sync exactly once, conflict
resolution), budgets and alerts, savings goal transfers, private receipts,
CSV export and re-import, and every page on a phone-sized screen.

```bash
cd frontend
npx playwright install chromium        # once
ET_BASE_URL=https://admin.dreamtechsolution.com \
ET_USER=<test user with the Expense User role> \
ET_PASSWORD=<password> \
yarn e2e
```

Optional: `ET_RESOLVE="MAP admin.dreamtechsolution.com 127.0.0.1"` to test the
site from the server itself. Use a dedicated test user: tests create uniquely
named accounts and data through the API and delete them afterwards. On this
server Chromium also needs `libasound2t64` (`sudo apt-get install libasound2t64`).

## 4. Performance

```bash
bench --site <site> execute expense_tracker.tests.perf.run --kwargs "{'n': 50000}"
```

Seeds 50,000 transactions for a throwaway user inside one database
transaction, times the heavy paths, prints query plans, then rolls back.

Results on this server (2026-11-24, 50,000 transactions for one user):

| Operation | Time |
|---|---|
| Transaction list, page 1 / page 100 | 44 ms / 49 ms |
| List filtered by account / by category + year | 37 ms / 133 ms |
| Text search | 131 ms |
| Search by exact amount | ~480 ms (rare matches scan the user's rows) |
| Dashboard summary (this month) | 150–190 ms (then cached until data changes) |
| Analytics (this year / 3 years) | 0.7 s / 1.25 s (cached until data changes) |
| Recompute one account balance | 40 ms |
| Add a transaction (validation + balance) | 70–80 ms |
| CSV export, all 50,000 rows | 1.25 s |

Fixes made from these measurements: a `STRAIGHT_JOIN` so the list walks the
`(user, transaction_date, creation)` index instead of sorting every row
(378 ms → 44 ms), and splitting the balance sum so each part uses its own
index instead of a table-wide `OR` scan.

Mobile load (throttled to ~1.6 Mbit/s, 150 ms latency, 4× CPU slowdown):
balance visible in ~3.5–5 s on the first visit and ~2 s on later visits (app
served from the service worker cache). Bundle (gzipped): app 122 KB, charts
190 KB (loaded only with charts), styles 53 KB.
