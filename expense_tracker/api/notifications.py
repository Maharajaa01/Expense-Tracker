"""In-app notifications (budget alerts, recurring reminders, sync problems)."""

import frappe

from expense_tracker.api import ok, require_user


@frappe.whitelist(methods=["GET"])
def list(limit=30, unread_only=0):  # noqa: A001
	user = require_user()
	filters = {"user": user, "is_silent": 0}
	if frappe.utils.cint(unread_only):
		filters["is_read"] = 0
	rows = frappe.get_all(
		"Finance Notification", filters=filters, order_by="creation desc",
		fields=["name", "notification_type", "severity", "title", "message", "reference_doctype", "reference_name",
		        "is_read", "creation"],
		limit_page_length=min(max(frappe.utils.cint(limit) or 30, 1), 100),
	)
	for r in rows:
		r["creation"] = str(r["creation"])
	unread = frappe.db.count("Finance Notification", {"user": user, "is_read": 0, "is_silent": 0})
	return ok(rows, {"unread": unread})


@frappe.whitelist(methods=["POST"])
def mark_read(name=None, all=0):  # noqa: A002
	user = require_user()
	if frappe.utils.cint(all):
		frappe.db.sql("update `tabFinance Notification` set is_read = 1 where user = %s and is_read = 0", user)
	elif name:
		doc = frappe.get_doc("Finance Notification", name)
		doc.check_permission("write")
		doc.db_set("is_read", 1)
	return ok({"unread": frappe.db.count("Finance Notification", {"user": user, "is_read": 0, "is_silent": 0})})
