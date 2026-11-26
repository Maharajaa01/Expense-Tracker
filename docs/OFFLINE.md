# Offline and installable app (PWA)

## What works offline

After the app has been opened online once on a device:

| Works offline | How |
|---|---|
| Opening the app (any `/expense/...` URL) | Service worker serves the last good copy of the app page and the precached build files |
| Dashboard (this month), recent transactions, budgets (this month), accounts, categories | Shown from the device copy, with "Showing … saved at <time>" |
| Adding expenses, income and transfers | Queued on the device; synced later |
| Editing and deleting transactions | Queued; edits carry the version they were based on for conflict detection |

Not available offline (needs the server): analytics, other periods/months,
filtered transaction searches, budgets/recurring/goal changes, receipts.
Balances and totals are never computed on the device: queued entries show a
"waiting to sync" marker and are included in balances once the server has
them.

## How sync works

1. Each queued change keeps its client transaction ID (a UUID). The server's
   unique `(user, client_txn_id)` index makes creates idempotent: replaying a
   change after a timeout, crash or double tap returns `duplicate`, never a
   second record. Deletes of already-deleted records count as done.
2. `expense_tracker.api.sync.push` applies up to 50 changes per call, each in
   its own savepoint, so one bad change never blocks the rest. Each result is
   `applied`, `duplicate`, `conflict`, `rejected` or `error`, and every
   operation is recorded in **Offline Sync Log**.
3. Conflicts: an edit made offline is sent with the `modified` timestamp it was
   based on. If the record changed (or was deleted) on another device, the app
   shows both versions and the user chooses **Keep my version** (re-sent with
   `force`) or **Keep the other version** (local edit dropped). Nothing is
   overwritten silently.
4. Rejected changes (e.g. the account was archived meanwhile) are kept with the
   server's explanation until the user discards them.
5. Expired sessions: sync refreshes the CSRF token once; if the session itself
   has expired the changes are kept and the user is asked to log in again.

Sync runs on app start, when the browser reports it is online, when the tab
becomes visible, every 30 s while anything is pending, on Background Sync
(where supported) and on **Sync now**. Because `navigator.onLine` can report
"online" on captive portals and dead connections, the app also treats any
request that cannot reach the server as "offline" and probes every 30 s to
detect recovery.

## What is stored on the device

| Where | What | Cleared |
|---|---|---|
| Service worker cache `et-static-<version>` | Hashed JS/CSS/fonts/icons (no user data) | Replaced on each new build |
| Service worker cache `et-shell` | The `/expense` page (contains the user's name and session token) | On logout |
| IndexedDB `expense-tracker` → `cache` | Allowlist only: accounts, categories, this month's dashboard, first page of recent transactions, this month's budgets — keyed by user | On logout; other users' entries dropped on login |
| IndexedDB `expense-tracker` → `queue` | Unsynced changes, keyed by user | When synced, or on logout (after a warning if any are unsynced) |

API responses are **never** cached by the service worker; only the allowlist
above is written, by the app itself.

## Browser support and limitations

| Capability | Chrome / Edge / Samsung (Android) | Chrome / Edge (desktop) | Safari (iPhone / iPad) | Firefox |
|---|---|---|---|---|
| Install | Native prompt via the **Install app** button | Native prompt | Share → *Add to Home Screen* (instructions shown) | Android: browser menu; desktop: not supported |
| Offline app + queue | Yes | Yes | Yes | Yes |
| Background Sync (sync while the app is closed) | Yes | Yes | **No** | **No** |
| Foreground sync (app open) | Yes | Yes | Yes | Yes |

Notes:

* Background Sync only wakes an **open** tab in this design (the sync request
  needs the session's CSRF token, which lives in the page). With the app
  closed, queued changes sync the next time it is opened online. This is the
  reliable path on every browser.
* iOS may evict storage for sites not used for several weeks; installed
  (home-screen) apps are kept longer. Unsynced changes are therefore shown
  prominently and synced at the first opportunity.
* Private/incognito windows may block IndexedDB; the app then says that
  changes can only be saved online instead of failing silently.

## The Install app button

Shown on the mobile dashboard, in the desktop sidebar and on the Profile page
until the app is installed. "Installed" means: running in standalone mode, the
browser fired `appinstalled`, or an install was accepted on this browser. If
the browser later offers installation again (the app was uninstalled), the
button returns.

## Service worker scope

Frappe serves build files from `/assets/...`, but a service worker only
controls pages under the path it is served from. `expense_tracker/pwa.py`
(a `page_renderer` hook) serves `/expense/sw.js` and
`/expense/manifest.webmanifest`, with `Service-Worker-Allowed: /expense`.
The scope is `/expense` (no trailing slash) because Frappe redirects
`/expense/` → `/expense`, and the bare URL must be controlled. No web-server
configuration is needed.
