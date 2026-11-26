"""Category endpoints (one level of subcategories)."""

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user

EDITABLE = ("category_name", "category_type", "parent_category", "icon", "color", "sort_order")


def _rows(user, name=None):
	cond = " and c.name = %(name)s" if name else ""
	return frappe.db.sql(
		f"""select c.name, c.category_name, c.category_type, c.parent_category, c.icon, c.color,
			c.is_default, c.is_archived, c.sort_order, c.modified,
			(select count(*) from `tabFinance Transaction` t where t.category = c.name) as txn_count
		from `tabFinance Category` c where c.user = %(user)s{cond}
		order by c.category_type, c.sort_order, c.category_name""",
		{"user": user, "name": name},
		as_dict=True,
	)


def _serialize(r) -> dict:
	return {**r, "modified": str(r.modified), "txn_count": int(r.txn_count)}


@frappe.whitelist(methods=["GET"])
def list(include_archived=0):  # noqa: A001
	user = require_user()
	rows = [_serialize(r) for r in _rows(user)]
	if not frappe.utils.cint(include_archived):
		rows = [r for r in rows if not r["is_archived"]]
	return ok(rows)


@frappe.whitelist(methods=["POST"])
def create(data):
	user = require_user()
	values = pick(parse_dict(data), EDITABLE)
	if "sort_order" not in values:
		values["sort_order"] = (
			frappe.db.sql("select coalesce(max(sort_order), 0) + 1 from `tabFinance Category` where user = %s", user)[0][0]
		)
	doc = frappe.get_doc({"doctype": "Finance Category", **values}).insert()
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def update(name, data):
	user = require_user()
	doc = frappe.get_doc("Finance Category", name)
	doc.check_permission("write")
	doc.update(pick(parse_dict(data), EDITABLE))
	doc.save()
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def set_archived(name, archived=1):
	user = require_user()
	doc = frappe.get_doc("Finance Category", name)
	doc.check_permission("write")
	doc.is_archived = 1 if frappe.utils.cint(archived) else 0
	doc.save()
	# Archiving a parent archives its subcategories too, so they don't linger in pickers.
	if doc.is_archived:
		for child in frappe.get_all("Finance Category", {"parent_category": doc.name, "user": user}, pluck="name"):
			frappe.db.set_value("Finance Category", child, "is_archived", 1)
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	doc = frappe.get_doc("Finance Category", name)
	doc.check_permission("delete")
	doc.delete()
	return ok({"name": name})
