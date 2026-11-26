# Architecture

Personal finance PWA built on Frappe v15 (backend) and Vue 3 + frappe-ui 1.x
(frontend), served at `/expense`.

## Environment (as inspected 2026-11-23)

| Component | Version |
|---|---|
| Frappe | 15.113.4 |
| Python / Node | 3.12 / 20.20 |
| MariaDB / Redis | 10.11 / 7.0 |
| frappe-ui | 1.2.0 (fallback: 0.1.261, proven on this bench by CRM) |

Target site: `admin.dreamtechsolution.com` (shared with ERPNext, HRMS, CRM …).
Because the site is shared, deploy this app **without** a site-wide
`bench migrate` — see [DEPLOY.md](DEPLOY.md).

## Layout

```
expense_tracker/
├── expense_tracker/              Python app
│   ├── api/                      @frappe.whitelist endpoints only (thin)
│   ├── services/                 business rules (Decimal-based, no HTTP)
│   ├── expense_tracker/doctype/  DocTypes with thin controllers
│   ├── permissions.py            row-level isolation hooks
│   ├── www/expense.py            SPA shell + boot data
│   └── public/frontend/          build output (git-ignored)
├── frontend/                     Vue 3 + TS + Vite source
│   └── src/{pages,components,features,stores,services,offline,theme}
└── docs/
```

## Request flow

1. `GET /expense/...` → `website_route_rules` → `www/expense.py`. Guests are
   redirected to `/login`. The page embeds boot data (user, CSRF token,
   currency) via frappe-ui's `jinjaBootData` plugin.
2. The SPA calls `/api/method/expense_tracker.api.<module>.<fn>` with the
   session cookie and `X-Frappe-CSRF-Token`.
3. Every endpoint returns `{ok: true, data, meta?}`. Errors are Frappe
   exceptions (HTTP 4xx/5xx) which the client normalises into `ApiError`
   kinds: `network | auth | permission | validation | conflict | not_found | server`.

## Data isolation

* Every user-owned DocType has a mandatory, indexed `user` field set on the
  server to `frappe.session.user` (not `owner`, because scheduler-generated
  records are created by Administrator).
* `permission_query_conditions` and `has_permission` hooks restrict all reads
  and writes to `user = session user`. System Managers are deliberately **not**
  exempt (personal finances stay private); only Administrator is, because the
  scheduler runs as Administrator.
* APIs never accept a `user` parameter. Linked records (account, category …)
  are validated to belong to the same user.

## Decisions log

| # | Decision | Reason |
|---|---|---|
| D1 | Balances recomputed from SQL `SUM`, stored as cache | No drift; one formula ([ACCOUNTING.md](ACCOUNTING.md)) |
| D2 | `user` field instead of `owner` | Scheduler-created docs must belong to the user |
| D3 | Idempotency via unique `(user, client_txn_id)` | Offline replays and recurring jobs can't duplicate |
| D4 | Optimistic concurrency on `modified` | Multi-device edits surface conflicts instead of silent overwrite |
| D5 | Single currency (INR) | Agreed v1 scope |
| D6 | Service worker served from `/expense/sw.js` via a `page_renderer` hook, scope `/expense` | SW scope must cover `/expense` (Frappe redirects `/expense/` → `/expense`); assets live under `/assets/...`; no nginx change needed ([OFFLINE.md](OFFLINE.md)) |
| D7 | Foreground sync is the primary path; Background Sync is an enhancement | Background Sync is Chromium-only |
| D8 | Access only via the admin-assigned "Expense User" role | Shared ERP site; the app never grants the role itself |
| D9 | Every figure (net worth, totals, % change, day totals) computed server-side | The client never does financial arithmetic |
| D11 | Recurring occurrences use `client_txn_id = rec:<name>:<date>` | The unique index makes double posting impossible even if the job runs twice |
| D12 | Budget alerts fire once per budget, period and threshold; lower thresholds passed in the same save are stored silently | No duplicate or noisy alerts |
| D13 | Insights only from calculated figures above minimum-data thresholds | Never "+400 %" from a ₹20 base; empty list when nothing applies |
| D14 | Connectivity judged from real request outcomes, not only `navigator.onLine` | Captive portals / dead connections report "online" |
| D15 | Offline read cache is an explicit allowlist in IndexedDB, per user, wiped on logout | Financial API responses are never cached indiscriminately |
| D16 | History references (notifications, sync log) are plain text, not Dynamic Links | A Dynamic Link would block deleting the referenced transaction/budget |
| D17 | CSV import is stateless preview → commit with `client_txn_id = imp:<file hash>:<row>` | Re-importing a file never duplicates; possible duplicates of existing entries are flagged |
| D18 | OCR only via the `expense_tracker_receipt_extractors` hook; output stored as a suggestion | No fake OCR; nothing changes a transaction without the user ([AI.md](AI.md)) |
| D19 | Bank alerts via a dedicated Gmail + read-only IMAP reader, not Frappe Email Account | Personal mail never reaches the shared server or Communications; App Password is revocable |
| D20 | Alert payments post immediately as Uncategorised (`needs_review`), deduplicated by bank reference | Balances stay right; the user only categorises; categories are remembered per payee |
| D10 | Chart income/expense colours separated by lightness | Green/red fails deuteranopia (ΔE 1.8); validated pairs: light #166534/#f87171 (ΔE 16.1), dark #15803d/#f43f5e (ΔE 6.3, with fixed order, legend, gaps and table view) |

## API

All under `expense_tracker.api.*`; reads are GET, writes are POST; every call requires the role.

| Module | Endpoints |
|---|---|
| `boot` | `get_boot` |
| `transactions` | `list(filters, page, page_size≤100, sort)` → rows, day_totals, summary (page 1), meta; `get`; `create(data, client_txn_id)` (idempotent); `update(name, data, expected_modified)` (409-style conflict); `delete`; `suggested_categories` |
| `accounts` | `list` (+ net_worth/assets/liabilities meta), `get`, `create`, `update`, `set_archived`, `delete` (only without transactions) |
| `categories` | `list`, `create`, `update`, `set_archived` (cascades to subcategories), `delete` (only unused) |
| `dashboard` | `summary(preset, from_date, to_date)`: totals, previous period, % change, net worth, categories, trend, 6-month series, recent; cached per user + data version |
| `profile` | `update(theme, week_start, default_account)` |
| `budgets` | `list(month)` with progress (spent, carried, remaining, %, level); `history(name, months)`; `create`; `update`; `delete` |
| `analytics` | `summary(preset incl. quarter/year/custom)`: totals, previous, % change, categories, income sources, category comparison, trend, daily, 12-month series, savings trend, budget use, insights |
| `recurring` | `list`, `upcoming(days)`, `create`, `update`, `post_now` (mark paid), `skip_next`, `delete` (keeps posted history) |
| `goals` | `list`, `create`, `update`, `contribute(amount, kind, date, source_account)`, `remove_contribution`, `delete` |
| `notifications` | `list(unread_only)` (+ unread count), `mark_read(name | all)` |
| `attachments` | `upload(transaction, file)` (multipart; JPG/PNG/WebP/HEIC/PDF by magic bytes, ≤ 10 MB, private), `list`, `delete` |
| `io` | `export_csv(filters)` (download, formula-safe), `preview_import(text, options)` (writes nothing), `commit_import(text, options)` (idempotent per file row) |
| `alerts` | `get_settings` (password never returned), `save_settings`, `test_connection`, `check_now`, `log` ([BANK_ALERTS.md](BANK_ALERTS.md)) |
| `sync` | `push(ops, device_id)`: idempotent batch of offline create/update/delete; per-op `applied / duplicate / conflict / rejected / error` |

Clients can only set whitelisted fields (`EDITABLE` in each module); `user`, balances, `source` and link fields like `savings_goal` are never accepted from the client.

## Scheduled jobs (`tasks.py`)

| Frequency | Job |
|---|---|
| Daily | Post due recurring transactions (catch-up capped at 12 per template), send reminders / due notices, re-check budget alerts |
| Weekly | Reconcile every stored balance against the ledger |
| Every 10 min | Read new bank alert emails for users who turned it on |

Each job logs failures to Error Log and continues; a recurring posting that
fails (e.g. archived account) also creates a notification for the user.

## Design system (frontend/src)

| Piece | Where | Notes |
|---|---|---|
| Tokens | `theme/tokens.css`, `tailwind.config.js` | RGB-channel CSS variables; dark mode via `[data-theme="dark"]` (frappe-ui `useColorScheme`). `*-solid` fills keep ≥ 4.5:1 with white text in both themes. |
| Icons | `theme/icon-set.json` | Lucide names offered in pickers; safelisted so DB-stored icon names render. |
| Money | `components/ui/Money.vue` | The one way amounts are drawn: tabular figures, Indian grouping, raised ₹ at display sizes, lighter paise. |
| Components | `components/ui/` | AppCard, StatTile, TransactionRow, CategoryIcon, SegmentedControl, AmountInput, ProgressBar/Ring, Empty/Error/Skeleton states, ResponsiveSheet (bottom sheet on phones, dialog on desktop), Icon/Colour pickers. |
| Shell | `components/layout/` | Desktop sidebar with Add button (`N` shortcut); mobile bottom bar with raised Add. |

Colour meaning: income green, spending coral, transfers neutral, savings teal,
budget tone by utilisation (< 80 % emerald, 80–99 % amber, ≥ 100 % coral).

A design review build (`ET_OUT_DIR=<dir> VITE_DESIGN_GALLERY=1 npx vite build
--base=/review-assets/`) adds `/expense/design`. It writes outside the app so
the live site never serves it.

## Testing

See [TESTING.md](TESTING.md): 149 backend tests, 43 frontend unit tests,
21 end-to-end tests and a 50,000-transaction performance check.
