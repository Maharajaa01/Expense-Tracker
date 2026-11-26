# Accounting Rules

These rules are the single source of truth for every number the app shows.
They are implemented in `expense_tracker/services/ledger.py` (balances) and
`expense_tracker/services/analytics.py` (period figures). The frontend never
computes balances; it only displays server results.

## Currency and precision

* Single currency per user: **INR** (v1). Multi-currency is out of scope.
* All amounts are stored as Frappe `Currency` fields (DECIMAL(21,9) in MariaDB)
  and rounded to **2 decimal places** with `ROUND_HALF_UP` on write.
* Server-side arithmetic uses Python `decimal.Decimal`
  (`expense_tracker/services/money.py`), never `float`.
* Aggregates (`SUM`) are computed in SQL on DECIMAL columns.

## Transaction types

Every `Finance Transaction` stores a **positive** `amount` and one type:

| Type | Fields | Effect on `account` | Effect on `to_account` | Counted as |
|---|---|---|---|---|
| Expense | account, category (Expense) | − amount | – | Spending |
| Expense + `is_refund` | account, category (Expense) | + amount | – | Negative spending in that category |
| Income | account, category (Income) | + amount | – | Income |
| Transfer | account, to_account (≠ account) | − amount | + amount | Neither income nor spending |

## Account balance

```
balance(account) = opening_balance
                 + Σ Income
                 + Σ Expense where is_refund
                 − Σ Expense where not is_refund
                 − Σ Transfer where account = this
                 + Σ Transfer where to_account = this
```

`Finance Account.current_balance` is a **cache** of this formula. It is
recomputed from `SUM()` (not adjusted incrementally) inside the same database
transaction as every insert, update or delete that touches the account, so it
cannot drift. A weekly scheduler job reconciles all balances as a safety net.

## Credit cards

A credit card is an account of type *Credit Card*. Its balance is normally
**negative** (money owed).

* **Purchase on card** → `Expense` with `account = card`. Counted as spending
  when it happens.
* **Paying the card bill** → `Transfer` from the bank account to the card.
  Bank balance goes down, card balance goes up towards zero. **Not** counted as
  spending, so the purchase is never counted twice.
* **Card refund / cashback** → `Expense` with `is_refund` on the card.
* `available_credit = credit_limit + balance` (balance is negative when owed).

## Totals

* **Total balance (net worth)** = Σ balance of accounts where
  `is_archived = 0` and `include_in_totals = 1`. Card debt reduces it.
* **Income (period)** = Σ Income amounts with `transaction_date` in period.
* **Expenses (period)** = Σ Expense (non-refund) − Σ Expense refunds in period.
* **Savings (period)** = Income − Expenses (may be negative).
* **Savings rate** = Savings ÷ Income × 100, or *not available* when Income = 0.
* Transfers never appear in income, expense, budget or category figures.

## Budgets

* `spent` = net Expenses (refunds subtracted) for the budget's category
  (including its subcategories) — or all expense categories for an overall
  budget — within the budget period.
* `remaining = amount (+ carried forward) − spent`; `utilisation = spent ÷ amount`.
* Carry-forward (if enabled) adds the previous period's unspent amount
  (never a negative carry).
* Alerts fire once per budget, period and threshold (50 %, 80 %, 100 %, over).

## Savings goals

* A goal may be linked to a Finance Account.
* **Linked goal**: a contribution creates a `Transfer` from the source account
  to the linked account (money really moves; no income/expense effect).
* **Unlinked goal**: a contribution is an earmark only; no balance changes.
* `current_amount = Σ contributions − Σ withdrawals` (recomputed, never typed).

## Recurring transactions

* Each occurrence has a deterministic `client_txn_id` of
  `rec:<recurring name>:<YYYY-MM-DD>`. The unique index on
  `(user, client_txn_id)` makes double-posting impossible even if the
  scheduler runs twice.
* Month-end anchoring: a schedule starting on the 31st posts on the last day
  of shorter months.
