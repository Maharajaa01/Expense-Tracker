"""Budget endpoints."""

import frappe

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.services import budgets
from expense_tracker.services.periods import parse_date

EDITABLE = ("budget_name", "category", "amount", "period_type", "start_date", "end_date", "carry_forward",
            "is_active", "alert_50", "alert_80", "alert_100")


@frappe.whitelist(methods=["GET"])
def list(month=None, include_inactive=0):  # noqa: A001
	"""Budgets with progress for the month containing ``month`` (default: today)."""
	user = require_user()
	ref = parse_date(month, "Month")
	return ok(budgets.list_with_progress(user, ref, bool(frappe.utils.cint(include_inactive))))


def _one(user, name, ref=None):
	row = next((b for b in budgets.list_with_progress(user, ref, True) if b["name"] == name), None)
	if not row:
		frappe.throw(frappe._("Budget not found."), frappe.DoesNotExistError)
	return row


@frappe.whitelist(methods=["GET"])
def history(name, months=6):
	user = require_user()
	doc = frappe.get_doc("Finance Budget", name)
	doc.check_permission("read")
	months = min(max(frappe.utils.cint(months) or 6, 1), 24)
	return ok({"budget": _one(user, name), "history": budgets.history(doc, months)})


@frappe.whitelist(methods=["POST"])
def create(data):
	user = require_user()
	doc = frappe.get_doc({"doctype": "Finance Budget", **pick(parse_dict(data), EDITABLE)}).insert()
	return ok(_one(user, doc.name))


@frappe.whitelist(methods=["POST"])
def update(name, data):
	user = require_user()
	doc = frappe.get_doc("Finance Budget", name)
	doc.check_permission("write")
	doc.update(pick(parse_dict(data), EDITABLE))
	doc.save()
	return ok(_one(user, doc.name))


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	doc = frappe.get_doc("Finance Budget", name)
	doc.check_permission("delete")
	doc.delete()
	return ok({"name": name})
