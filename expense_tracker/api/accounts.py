"""Account endpoints. Balances are always computed by the server (services/ledger.py)."""

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.services.money import D, to_number

EDITABLE = ("account_name", "account_type", "account_last4", "opening_balance", "opening_date", "credit_limit", "icon", "color",
            "include_in_totals", "notes", "sort_order")


def _serialize(r) -> dict:
	balance = D(r.current_balance)
	out = {
		"name": r.name,
		"account_name": r.account_name,
		"account_type": r.account_type,
		"account_last4": r.account_last4,
		"opening_balance": to_number(r.opening_balance),
		"opening_date": str(r.opening_date) if r.opening_date else None,
		"balance": to_number(balance),
		"credit_limit": to_number(r.credit_limit),
		"icon": r.icon,
		"color": r.color,
		"include_in_totals": int(r.include_in_totals),
		"is_archived": int(r.is_archived),
		"notes": r.notes,
		"sort_order": r.sort_order,
		"has_transactions": bool(r.get("txn_count")),
		"modified": str(r.modified),
	}
	if r.account_type == "Credit Card":
		out["available_credit"] = to_number(D(r.credit_limit) + balance)
	return out


def _rows(user, name=None):
	cond = " and a.name = %(name)s" if name else ""
	return frappe.db.sql(
		f"""select a.*, (select count(*) from `tabFinance Transaction` t
			where t.account = a.name or t.to_account = a.name) as txn_count
		from `tabFinance Account` a where a.user = %(user)s{cond}
		order by a.is_archived, a.sort_order, a.creation""",
		{"user": user, "name": name},
		as_dict=True,
	)


@frappe.whitelist(methods=["GET"])
def list(include_archived=0):  # noqa: A001
	"""Accounts plus server-computed totals over active, included accounts:
	net worth, assets (positive balances) and liabilities (card dues etc.)."""
	user = require_user()
	raw = _rows(user)
	counted = [D(r.current_balance) for r in raw if not r.is_archived and r.include_in_totals]
	assets = sum((b for b in counted if b > 0), D(0))
	liabilities = sum((-b for b in counted if b < 0), D(0))
	rows = [_serialize(r) for r in raw]
	if not frappe.utils.cint(include_archived):
		rows = [r for r in rows if not r["is_archived"]]
	return ok(rows, {
		"net_worth": to_number(assets - liabilities),
		"assets": to_number(assets),
		"liabilities": to_number(liabilities),
	})


@frappe.whitelist(methods=["GET"])
def get(name):
	user = require_user()
	rows = _rows(user, name)
	if not rows:
		frappe.throw(_("Account not found."), frappe.DoesNotExistError)
	return ok(_serialize(rows[0]))


@frappe.whitelist(methods=["POST"])
def create(data):
	user = require_user()
	doc = frappe.get_doc({"doctype": "Finance Account", **pick(parse_dict(data), EDITABLE)}).insert()
	if not frappe.db.get_value("Expense Profile", user, "default_account"):
		frappe.db.set_value("Expense Profile", user, "default_account", doc.name, update_modified=False)
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def update(name, data):
	user = require_user()
	doc = frappe.get_doc("Finance Account", name)
	doc.check_permission("write")
	doc.update(pick(parse_dict(data), EDITABLE))
	doc.save()
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def set_archived(name, archived=1):
	user = require_user()
	doc = frappe.get_doc("Finance Account", name)
	doc.check_permission("write")
	doc.is_archived = 1 if frappe.utils.cint(archived) else 0
	doc.save()
	return ok(_serialize(_rows(user, doc.name)[0]))


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	doc = frappe.get_doc("Finance Account", name)
	doc.check_permission("delete")
	doc.delete()
	return ok({"name": name})
