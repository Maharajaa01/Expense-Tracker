"""Scheduler entry points (wired in hooks.py)."""

import frappe

from expense_tracker.services import budgets, ledger, recurring


def daily():
	"""Post due recurring transactions, send reminders, re-check budgets for the new day/month."""
	_run("post recurring", recurring.post_due)
	_run("recurring reminders", recurring.send_reminders)
	for user in frappe.get_all("Finance Budget", filters={"is_active": 1}, pluck="user", distinct=True):
		_run(f"budget alerts for {user}", lambda u=user: budgets.evaluate_alerts(u))


def bank_alerts():
	"""Every 10 minutes: read new bank alert emails for users who enabled it."""
	from expense_tracker.services.bank_alerts import ingest

	_run("bank alert emails", ingest.check_all)


def weekly():
	"""Safety net: recompute every stored balance from the ledger."""
	_run("reconcile balances", ledger.reconcile_all)


def _run(label, fn):
	"""Run one job; on failure log it and continue with the next (never silently)."""
	try:
		result = fn()
		frappe.db.commit()
		return result
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"Expense Tracker scheduler: {label} failed")
