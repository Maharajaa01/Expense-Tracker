"""Savings goal endpoints."""

import frappe

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.services import goals

EDITABLE = ("goal_name", "target_amount", "start_date", "target_date", "linked_account", "icon", "color", "status")


@frappe.whitelist(methods=["GET"])
def list(include_archived=0):  # noqa: A001
	return ok(goals.list_goals(require_user(), bool(frappe.utils.cint(include_archived))))


@frappe.whitelist(methods=["POST"])
def create(data):
	require_user()
	doc = frappe.get_doc({"doctype": "Savings Goal", **pick(parse_dict(data), EDITABLE)}).insert()
	return ok(goals.serialize(doc))


@frappe.whitelist(methods=["POST"])
def update(name, data):
	require_user()
	doc = frappe.get_doc("Savings Goal", name)
	doc.check_permission("write")
	values = pick(parse_dict(data), EDITABLE)
	if "linked_account" in values and values["linked_account"] != doc.linked_account and any(r.transaction for r in doc.contributions):
		frappe.throw(frappe._("This goal already has transfers into its account. Its linked account can't be changed."))
	doc.update(values)
	doc.save()
	return ok(goals.serialize(doc))


@frappe.whitelist(methods=["POST"])
def contribute(name, amount, kind="Contribution", date=None, source_account=None, note=None):
	user = require_user()
	return ok(goals.contribute(user, name, amount, kind, date, source_account, note))


@frappe.whitelist(methods=["POST"])
def remove_contribution(name, row):
	user = require_user()
	return ok(goals.remove_contribution(user, name, row))


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	goals.delete_goal(name)
	return ok({"name": name})
