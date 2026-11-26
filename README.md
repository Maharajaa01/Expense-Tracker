# Expense Tracker

A personal finance app for Frappe v15: track spending and income across
accounts and cards, set budgets, plan savings goals, automate recurring
payments and see where your money goes. Installable on phones as a PWA and
usable offline.

Served at **`/expense`** on your Frappe site. Access is granted per user with
the **Expense User** role.

## Features

- **Quick Add** – record an expense in a few seconds (keyboard shortcut `N`,
  most-used categories first, remembered account, optional receipt photo).
- **Accounts** – cash, bank, credit cards and wallets; transfers and card bill
  payments are never counted as spending.
- **Transactions** – search, filters, date grouping, edit, delete, CSV export
  and import (bank statement formats, duplicate-safe).
- **Budgets** – monthly or custom periods, carry-over, alerts at 50/80/100 %.
- **Analytics** – income vs spending, categories, trends, savings rate,
  comparisons and plain-language insights computed from your data.
- **Recurring payments** – salary, rent, EMIs, subscriptions; posted
  automatically or confirmed by you, with reminders.
- **Savings goals** – progress, monthly amount needed, contributions as real
  transfers or tracked amounts.
- **Bank alert emails** – payments from Karnataka Bank / Axis Bank alerts are added
  automatically (balances update at once); you just pick the category, and it's
  remembered for that payee.
- **Receipts** – photos/PDFs stored privately per transaction; OCR-ready
  extension point (no OCR shipped).
- **PWA** – install button, works offline, queued changes sync safely with
  conflict handling.
- Light and dark themes, Indian number formatting (₹1,23,456.00).

## Documentation

| Document | Contents |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | Installing on a Frappe v15 bench |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Deploying updates (incl. on a shared site) and production checklist |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Structure, APIs, data isolation, decisions |
| [docs/ACCOUNTING.md](docs/ACCOUNTING.md) | How balances, transfers, cards, budgets and goals are calculated |
| [docs/OFFLINE.md](docs/OFFLINE.md) | Offline behaviour, sync, stored data, browser support |
| [docs/TESTING.md](docs/TESTING.md) | Backend, frontend unit, end-to-end and performance tests |
| [docs/BANK_ALERTS.md](docs/BANK_ALERTS.md) | Automatic payments from bank alert emails: setup, privacy, parser |
| [docs/AI.md](docs/AI.md) | Extension points and rules for future AI/OCR features |

## Development

```bash
cd apps/expense_tracker/frontend
yarn install
yarn dev            # Vite dev server (proxies the Frappe site)
yarn test:run       # unit tests
yarn build          # production build into expense_tracker/public/frontend
```

This app uses `pre-commit` (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/expense_tracker && pre-commit install
```

## License

MIT
