# Installation

## Requirements

| Component | Version |
|---|---|
| Frappe | v15 (tested on 15.113) |
| Python | 3.10+ (tested on 3.12) |
| Node.js | 20.19+ (frappe-ui 1.x requirement) |
| Yarn | 1.22 |
| MariaDB | 10.6+ |
| HTTPS | Required in production: service workers (offline, install) only work on HTTPS |

ERPNext is **not** required. The app installs alongside other apps without
touching their data.

## New site or dedicated bench

```bash
cd ~/frappe-bench
bench get-app <repository-url> --branch develop    # also runs yarn install for the frontend
bench --site <site> install-app expense_tracker     # creates DocTypes and the "Expense User" role
bench build --app expense_tracker                   # builds the Vue app into public/frontend
bench --site <site> enable-scheduler                # recurring payments, reminders, balance checks
bench restart
```

Open `https://<site>/expense`.

## Existing shared site

If the site runs other apps with pending patches, follow
[DEPLOY.md](DEPLOY.md) instead of `install-app`/`migrate`: it syncs only this
app's schema and scheduled jobs.

## Giving people access

1. Desk → **User** → open the user.
2. **Roles** → tick **Expense User** → Save. (Works for System Users and Website Users.)
3. On their first visit to `/expense` they get the default categories and a
   Cash account.

Each user only ever sees their own data. System Managers are deliberately not
exempt; only Administrator can see everyone's records (needed for the
scheduler and support).

## Verify the installation

- `https://<site>/expense` shows the dashboard after login (and redirects to
  login when logged out).
- `https://<site>/expense/sw.js` returns JavaScript with the header
  `Service-Worker-Allowed: /expense`.
- `https://<site>/expense/manifest.webmanifest` returns the app manifest.
- In Chrome on Android, the dashboard shows **Install the app**.
- Desk → **Scheduled Job Type** lists `expense_tracker.tasks.daily` and
  `expense_tracker.tasks.weekly`.

## Uninstall

```bash
bench --site <site> uninstall-app expense_tracker
```

This deletes all Expense Tracker data (transactions, accounts, receipts) for
every user. Export it first from Settings → *Export all transactions*.
