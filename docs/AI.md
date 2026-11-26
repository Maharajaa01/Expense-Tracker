# AI-ready architecture

No AI or OCR feature ships with this app, and nothing in the app pretends to
extract data. What exists are clean extension points so a future integration
can be added without changing the core, plus rules any integration must follow.

## Principles for any AI integration

1. **Suggest, never apply.** Model output is stored as a suggestion and shown
   to the user, who confirms it. Ledger entries are only ever created or
   changed through the normal validated paths (`Finance Transaction`
   controller, same permission and ownership checks).
2. **Opt-in and private.** Sending receipts or transactions to an external
   service needs explicit per-user consent and must be documented. Nothing is
   sent anywhere by default.
3. **Server-side only.** API keys live in site config / encrypted settings,
   never in the frontend bundle.
4. **Failures are visible.** A failed extraction is marked `Failed` and logged;
   it never blocks saving the transaction.

## Extension point: receipt extraction (OCR)

Register one or more extractors in another app's `hooks.py`:

```python
expense_tracker_receipt_extractors = ["my_app.ocr.extract_receipt"]
```

Contract (`expense_tracker/services/receipts.py`):

* Signature: `fn(file_doc: File) -> dict | None`
* Return keys (all optional): `merchant`, `date` (YYYY-MM-DD), `total`
  (string decimal), `currency`, `tax`, `line_items` (list of
  `{description, amount}`), `confidence` (0–1).
* Return `None` if the receipt can't be read; the next extractor is tried.
* Runs in a background job (`queue="short"`) after upload. The attachment's
  `ocr_status` moves `Not Processed → Queued → Done | Failed`, and the result
  is stored in `Transaction Attachment.extracted_data` (JSON).
* The transaction is **not** modified. A future UI can offer "Use these
  details" which then calls the normal `transactions.update` API.

The contract is covered by tests (`tests/test_phase7.py::TestExtractorHook`):
output is stored only as a suggestion, crashes are marked `Failed` and
logged, and nothing is queued when no extractor is installed.

## Data available to future features

All read through whitelisted, per-user APIs (see ARCHITECTURE.md):

| Need | Source |
|---|---|
| Categorisation suggestions | `transactions.list` (title, amount, category history); `transactions.suggested_categories` already ranks by recency/frequency without any model |
| Spending insights | `analytics.summary` (server-computed totals, comparisons); `services/insights.py` is rule-based and can be extended with new rules |
| Receipts | `Transaction Attachment` (private files, `extracted_data`) |

Insights shown today are generated only from calculated figures with
minimum-data thresholds (`services/insights.py`); a model-based insight must
meet the same bar: every number it states has to be traceable to the ledger.
