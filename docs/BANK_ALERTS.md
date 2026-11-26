# Bank alert emails

Payments are recorded automatically from bank alert emails (Karnataka Bank,
Axis Bank). Balances update immediately; the user only picks a category.

## How it works

```
Bank ──alert email──▶ personal Gmail ──filter: forward bank emails only──▶ alerts Gmail (dedicated)
                                                                              │ IMAP, read-only, every 10 min
                                                                              ▼
                     services/bank_alerts/mailbox.py → parser.py → ingest.py → Finance Transaction
```

1. **Mailbox** (`mailbox.py`): signs in to `imap.gmail.com` with a Google App
   Password, opens INBOX **read-only**, fetches with `BODY.PEEK[]` (nothing is
   marked read, moved or deleted), only messages newer than the last processed
   UID (starting at the "Read emails from" date). Max 100 per run.
2. **Sender check**: only mail from the banks' domains (`BANK_SENDER_DOMAINS`
   in `ingest.py`) is read.
3. **Parser** (`parser.py`, pure functions): direction (debit/credit *for the
   customer's account*), amount, account last 4 digits, UPI/RRN reference,
   payee (UPI path name → UPI ID → "to/from" phrase), date (day-first). OTPs,
   failed/declined payments, collect requests, "will be debited", due-date
   reminders, statements and offers are ignored.
4. **Posting** (`ingest.py`):
   - Account: the user's active account whose *Account Number (last 4 digits)*
     matches. None or several → logged as **Needs Account**, nothing posted.
   - Debit → Expense, credit → Income, `source = "Bank Alert"`.
   - Category: the one the user last chose for the same payee
     (`merchant_key` = UPI ID or normalised name); otherwise **Uncategorised**
     with `needs_review = 1` → shown under **To categorise**.
   - Duplicates: `client_txn_id = bank:<reference>` (unique per user), so the
     same payment arriving twice (two emails, a forwarded copy, a later CSV
     import with the same reference) is recorded once.
   - Every email gets one **Bank Alert** log row (parsed fields and outcome;
     never the email). Unrecognised alerts keep a 500-character snippet with
     long numbers masked, to improve the parser.
5. **Scheduler**: `expense_tracker.tasks.bank_alerts` every 10 minutes
   (`*/10 * * * *`). One failing mailbox never blocks others; a sign-in
   problem creates one notification per day.

## Privacy and security

- Option B (decided): a **separate Gmail** that only receives forwarded bank
  emails, so the server never holds access to the user's personal mailbox.
- The App Password is a Frappe *Password* field (encrypted at rest, never sent
  back to the browser; the API only reports `has_password`). It can be revoked
  any time in the Google Account.
- Frappe's built-in *Email Account* is deliberately not used: it imports mail
  into Communications that System Managers can read.
- Logs and transactions follow the normal per-user isolation rules.

## Setup (per user)

Shown in the app under **Settings → Bank alert emails → How to set it up**:

1. Create a new Gmail for alerts; turn on 2-Step Verification; create an App
   Password (myaccount.google.com/apppasswords).
2. In the personal Gmail: add the new address as a forwarding address
   (confirm the code), then a filter
   `from:(axisbank.com OR ktkbank.com OR karnatakabank.com)` → *Forward it to*
   the new address.
3. In the app: enter the address + App Password, *Test connection*, *Turn on*.
4. In Accounts, add the last 4 digits to each bank account.

## Adding or fixing a bank

- Sender domains: `BANK_SENDER_DOMAINS` in `ingest.py`; bank names: `BANKS` in `parser.py`.
- Wording: add the real (masked) alert text as a test case in
  `tests/test_bank_alerts.py`, then adjust the patterns until it passes.
  Unrecognised alerts in **Settings → Recent alerts** show what to add.

**Status:** parser patterns are based on common Indian alert formats and are
covered by tests; they still need checking against real Karnataka Bank and
Axis Bank emails.
