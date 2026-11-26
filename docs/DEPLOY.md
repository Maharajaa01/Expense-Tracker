# Deploying

For a first installation see [INSTALL.md](INSTALL.md). This guide covers
deploying updates.

`admin.dreamtechsolution.com` also runs ERPNext, HRMS, CRM and others, so a
site-wide `bench migrate` (which runs every app's pending patches) is avoided
for routine Expense Tracker deploys. On a dedicated site, `bench --site <site>
migrate` + `bench build --app expense_tracker` + `bench restart` is enough.

## Before deploying

```bash
cd apps/expense_tracker/frontend && yarn typecheck && yarn test:run
cd ~/dreamtech-bench && bench --site admin.dreamtechsolution.com execute expense_tracker.tests.live_runner.run
```

## Build the frontend

```bash
cd ~/dreamtech-bench
bench build --app expense_tracker     # runs the frontend's yarn build (type check + Vite)
```

The build is memory-hungry (~1.5 GB). On this 8 GB server run it on its own,
not alongside browser tests.

## Sync only this app's schema

```bash
cd ~/dreamtech-bench/sites
../env/bin/python -c "
import frappe
frappe.init(site='admin.dreamtechsolution.com', sites_path='.')
frappe.connect()
from frappe.model.sync import sync_for
# Import Savings Goal first on a brand-new site: Finance Transaction links to it.
frappe.reload_doc('expense_tracker', 'doctype', 'savings_goal_contribution')
frappe.reload_doc('expense_tracker', 'doctype', 'savings_goal')
sync_for('expense_tracker', force=False, reset_permissions=False)
from expense_tracker.setup.provision import ensure_role
ensure_role()
frappe.db.commit()
"
```

## Register this app's scheduled jobs (first deploy, or when `scheduler_events` change)

`bench migrate` normally does this; on a shared site register only this app's jobs:

```bash
../env/bin/python -c "
import frappe
frappe.init(site='admin.dreamtechsolution.com', sites_path='.')
frappe.connect()
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import insert_events
insert_events(frappe.get_hooks('scheduler_events', app_name='expense_tracker'))
frappe.db.commit()
"
```

## Reload, then clear caches (order matters)

Running workers keep hooks in memory and will re-populate Redis with stale
route rules if the cache is cleared first.

```bash
kill -HUP $(pgrep -f "gunicorn -b 127.0.0.1:8000" -o)   # graceful reload
bench --site admin.dreamtechsolution.com clear-cache
bench --site admin.dreamtechsolution.com clear-website-cache
```

Verify: `https://admin.dreamtechsolution.com/expense` loads after login,
`/expense/anything` returns the SPA (not 404), and `/expense/sw.js` returns
JavaScript with a `Service-Worker-Allowed: /expense` header.

Each build gets a new service worker version (content hash of the asset
list). Open tabs pick it up on their next navigation; a tab that requests a
removed lazy chunk reloads itself once.

## Granting access

Only users with the **Expense User** role can open `/expense` (the app never
assigns it). In the desk: *User → Roles → Expense User*. Works for both System
Users and Website Users. Their categories and a Cash account are created on
their first visit.

## Production checklist

- [ ] HTTPS (service worker, install and offline need it).
- [ ] Scheduler enabled for the site (`bench --site <site> scheduler status`):
      daily job posts recurring payments and sends reminders; weekly job
      reconciles balances.
- [ ] Background workers running (receipt extraction jobs, if an extractor is installed).
- [ ] Database backups include `tabFinance *` tables and **private files**
      (`sites/<site>/private/files`) for receipts: `bench --site <site> backup --with-files`.
- [ ] Only intended users have the **Expense User** role.
- [ ] `Error Log` filtered on "Expense Tracker" is empty after the deploy.

## Rolling back

1. `git checkout <previous tag>` in `apps/expense_tracker`.
2. `bench build --app expense_tracker`, then reload and clear caches as above.
3. Schema changes in this app so far only add fields/indexes, so older code
   runs against a newer schema. Check `git log -- expense_tracker/expense_tracker/doctype`
   before rolling back across a release that changed DocTypes.

Installed apps pick up the rolled-back build on their next start (new service
worker version).
