"""Account balances. See docs/ACCOUNTING.md for the rules.

Concurrency: before a transaction is written, every affected account row is
locked with ``SELECT … FOR UPDATE`` (in sorted order to avoid deadlocks).
After the write, the balance is recomputed from the ledger with a locking read
so concurrent requests serialise per account and never overwrite each other
with a stale sum.
"""

from decimal import Decimal

import frappe

from expense_tracker.services.money import D

# Two sums instead of "account = X OR to_account = X": each part uses its own
# index (an OR across two columns falls back to a full table scan).
_BALANCE_SQL = """
	select
		(select coalesce(sum(case
			when transaction_type = 'Income' then amount
			when transaction_type = 'Expense' and is_refund = 1 then amount
			when transaction_type = 'Expense' then -amount
			when transaction_type = 'Transfer' then -amount
			else 0 end), 0)
		from `tabFinance Transaction` where account = %(a)s lock in share mode)
		+
		(select coalesce(sum(amount), 0)
		from `tabFinance Transaction` where to_account = %(a)s and transaction_type = 'Transfer' lock in share mode)
"""


def lock_accounts(names) -> None:
	"""Lock account rows for the rest of the DB transaction."""
	for name in sorted({n for n in names if n}):
		frappe.db.sql("select name from `tabFinance Account` where name = %s for update", name)


def ledger_total(account: str) -> Decimal:
	return D(frappe.db.sql(_BALANCE_SQL, {"a": account})[0][0])


def recompute_account_balance(account: str) -> Decimal:
	"""Recompute and store ``current_balance`` for one account."""
	opening = frappe.db.sql(
		"select opening_balance from `tabFinance Account` where name = %s for update", account
	)
	if not opening:
		return D(0)
	balance = D(opening[0][0]) + ledger_total(account)
	frappe.db.set_value("Finance Account", account, "current_balance", balance, update_modified=False)
	return balance


def recompute_many(accounts) -> None:
	for name in sorted({a for a in accounts if a}):
		recompute_account_balance(name)


def reconcile_all() -> int:
	"""Recompute every account balance. Returns the number of corrected accounts."""
	fixed = 0
	for name, stored in frappe.db.sql("select name, current_balance from `tabFinance Account`"):
		if D(stored) != recompute_account_balance(name):
			fixed += 1
	return fixed
