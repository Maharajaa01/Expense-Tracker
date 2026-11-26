"""Savings goal contributions (docs/ACCOUNTING.md, "Savings goals")."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

from expense_tracker.services.money import D, ZERO, percent, to_number, validate_amount
from expense_tracker.services.ownership import get_owned


def contribute(user: str, goal_name: str, amount, kind: str = "Contribution", on_date=None,
               source_account: str | None = None, note: str | None = None) -> dict:
	"""Add a contribution or withdrawal.

	Linked goal + a different source account: money really moves, as a Transfer
	(source → goal account for contributions, the reverse for withdrawals).
	Otherwise the entry is an earmark and no balance changes.
	"""
	if kind not in ("Contribution", "Withdrawal"):
		frappe.throw(_("Invalid contribution type."))
	goal = frappe.get_doc("Savings Goal", goal_name)
	goal.check_permission("write")
	amount = validate_amount(amount)
	on_date = getdate(on_date or nowdate())
	if source_account:
		get_owned("Finance Account", source_account, user, label=_("Account"))

	txn_name = None
	if goal.linked_account and source_account and source_account != goal.linked_account:
		src, dst = (source_account, goal.linked_account) if kind == "Contribution" else (goal.linked_account, source_account)
		txn = frappe.get_doc({
			"doctype": "Finance Transaction",
			"transaction_type": "Transfer",
			"amount": amount,
			"account": src,
			"to_account": dst,
			"transaction_date": on_date,
			"title": (_("Saved for {0}") if kind == "Contribution" else _("Withdrawn from {0}")).format(goal.goal_name),
			"notes": note,
			"source": "Goal",
			"savings_goal": goal.name,
		})
		txn.insert()
		txn_name = txn.name

	goal.append("contributions", {
		"contribution_date": on_date, "kind": kind, "amount": amount,
		"source_account": source_account, "transaction": txn_name, "note": (note or "")[:140] or None,
	})
	goal.save()
	return serialize(goal)


def remove_contribution(user: str, goal_name: str, row_name: str) -> dict:
	goal = frappe.get_doc("Savings Goal", goal_name)
	goal.check_permission("write")
	row = next((r for r in goal.contributions if r.name == row_name), None)
	if not row:
		frappe.throw(_("Contribution not found."), frappe.DoesNotExistError)
	txn = row.transaction
	goal.remove(row)
	goal.save()
	if txn and frappe.db.exists("Finance Transaction", txn):
		frappe.flags.expense_tracker_goal_delete = True
		try:
			frappe.delete_doc("Finance Transaction", txn)
		finally:
			frappe.flags.expense_tracker_goal_delete = False
	return serialize(goal)


def delete_goal(goal_name: str) -> None:
	goal = frappe.get_doc("Savings Goal", goal_name)
	goal.check_permission("delete")
	if any(r.transaction for r in goal.contributions):
		frappe.throw(_("This goal has transfers between your accounts. Archive it instead, or remove those contributions first."))
	goal.delete()


def serialize(goal) -> dict:
	saved = D(goal.current_amount)
	target = D(goal.target_amount)
	remaining = max(target - saved, ZERO)
	monthly = None
	days_left = None
	if goal.target_date and remaining > 0:
		days_left = date_diff(goal.target_date, nowdate())
		if days_left > 0:
			months = max(days_left / 30.44, 1)
			monthly = to_number(remaining / D(months))
	account_name = frappe.db.get_value("Finance Account", goal.linked_account, "account_name") if goal.linked_account else None
	return {
		"name": goal.name,
		"goal_name": goal.goal_name,
		"target_amount": to_number(target),
		"current_amount": to_number(saved),
		"remaining": to_number(remaining),
		"percent": percent(saved, target),
		"start_date": str(goal.start_date) if goal.start_date else None,
		"target_date": str(goal.target_date) if goal.target_date else None,
		"days_left": days_left,
		"monthly_needed": monthly,
		"linked_account": goal.linked_account,
		"linked_account_name": account_name,
		"icon": goal.icon,
		"color": goal.color,
		"status": goal.status,
		"modified": str(goal.modified),
		"contributions": [
			{"name": r.name, "date": str(r.contribution_date), "kind": r.kind, "amount": to_number(r.amount),
			 "source_account": r.source_account, "transaction": r.transaction, "note": r.note}
			for r in sorted(goal.contributions, key=lambda r: (str(r.contribution_date), r.idx), reverse=True)
		],
	}


def list_goals(user: str, include_archived: bool = False) -> list[dict]:
	filters = {"user": user}
	if not include_archived:
		filters["status"] = ("!=", "Archived")
	names = frappe.get_all("Savings Goal", filters=filters, pluck="name", order_by="status asc, target_date is null, target_date asc, creation asc")
	return [serialize(frappe.get_doc("Savings Goal", n)) for n in names]
