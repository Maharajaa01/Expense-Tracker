"""Recurring transaction endpoints."""

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.services import queries, recurring
from expense_tracker.services.money import to_number

EDITABLE = ("title", "transaction_type", "amount", "account", "to_account", "category", "notes", "frequency",
            "interval", "custom_unit", "start_date", "end_date", "auto_post", "remind_days_before", "is_active")


def _serialize(r) -> dict:
	names = {}
	for field, dt, col in (("account", "Finance Account", "account_name"), ("to_account", "Finance Account", "account_name"),
	                       ("category", "Finance Category", "category_name")):
		if r.get(field):
			names[f"{field}_name"] = frappe.db.get_value(dt, r[field], col)
	cat = frappe.db.get_value("Finance Category", r.category, ["icon", "color"], as_dict=True) if r.category else None
	return {
		**{k: r.get(k) for k in recurring.FIELDS if k not in ("user",)},
		**names,
		"amount": to_number(r.amount),
		"start_date": str(r.start_date),
		"end_date": str(r.end_date) if r.end_date else None,
		"next_run_date": str(r.next_run_date) if r.next_run_date else None,
		"last_run_date": str(r.last_run_date) if r.last_run_date else None,
		"modified": str(r.modified),
		"schedule": recurring.describe(r),
		"category_icon": cat.icon if cat else None,
		"category_color": cat.color if cat else None,
	}


def _get(user, name):
	row = frappe.db.get_value("Recurring Transaction", {"name": name, "user": user}, recurring.FIELDS, as_dict=True)
	if not row:
		frappe.throw(_("Recurring payment not found."), frappe.DoesNotExistError)
	return _serialize(row)


@frappe.whitelist(methods=["GET"])
def list(include_inactive=1):  # noqa: A001
	user = require_user()
	filters = {"user": user}
	if not frappe.utils.cint(include_inactive):
		filters["is_active"] = 1
	rows = frappe.get_all("Recurring Transaction", filters=filters, fields=recurring.FIELDS,
	                      order_by="is_active desc, next_run_date is null, next_run_date asc")
	return ok([_serialize(r) for r in rows])


@frappe.whitelist(methods=["GET"])
def upcoming(days=30):
	user = require_user()
	return ok(recurring.upcoming(user, min(max(frappe.utils.cint(days) or 30, 1), 366)))


@frappe.whitelist(methods=["POST"])
def create(data):
	user = require_user()
	doc = frappe.get_doc({"doctype": "Recurring Transaction", **pick(parse_dict(data), EDITABLE)}).insert()
	return ok(_get(user, doc.name))


@frappe.whitelist(methods=["POST"])
def update(name, data):
	user = require_user()
	doc = frappe.get_doc("Recurring Transaction", name)
	doc.check_permission("write")
	doc.update(pick(parse_dict(data), EDITABLE))
	doc.save()
	return ok(_get(user, doc.name))


@frappe.whitelist(methods=["POST"])
def post_now(name):
	"""Record the next payment now ("Mark as paid")."""
	user = require_user()
	doc = frappe.get_doc("Recurring Transaction", name)
	doc.check_permission("write")
	txn = recurring.post_now(name)
	return ok({"recurring": _get(user, name), "transaction": queries.get_row(user, txn)})


@frappe.whitelist(methods=["POST"])
def skip_next(name):
	user = require_user()
	doc = frappe.get_doc("Recurring Transaction", name)
	doc.check_permission("write")
	recurring.skip_next(name)
	return ok(_get(user, name))


@frappe.whitelist(methods=["POST"])
def delete(name):
	"""Delete the schedule. Transactions it already created stay (they are real history)."""
	require_user()
	doc = frappe.get_doc("Recurring Transaction", name)
	doc.check_permission("delete")
	frappe.db.sql("update `tabFinance Transaction` set recurring_transaction = null where recurring_transaction = %s", name)
	doc.delete()
	return ok({"name": name})
