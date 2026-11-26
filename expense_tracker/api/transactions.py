"""Transaction endpoints: list, get, create (idempotent), update (conflict-aware), delete."""

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.services import queries

EDITABLE = ("transaction_type", "amount", "transaction_date", "title", "notes", "account", "to_account",
            "category", "is_refund")


@frappe.whitelist(methods=["GET"])
def list(filters=None, page=1, page_size=50, sort="date_desc"):  # noqa: A001 – API name
	user = require_user()
	result = queries.list_transactions(user, parse_dict(filters), page, page_size, sort)
	return ok(result["data"], result["meta"])


@frappe.whitelist(methods=["GET"])
def get(name):
	return ok(queries.get_row(require_user(), name))


@frappe.whitelist(methods=["POST"])
def create(data, client_txn_id=None):
	"""Create a transaction. Retrying with the same ``client_txn_id`` returns the
	original record instead of creating a duplicate (offline sync, double taps)."""
	user = require_user()
	values = pick(parse_dict(data), EDITABLE)
	client_txn_id = (client_txn_id or "").strip()[:64] or None

	if client_txn_id and (existing := _by_client_id(user, client_txn_id)):
		return ok({"transaction": queries.get_row(user, existing), "duplicate": True})

	doc = frappe.get_doc({"doctype": "Finance Transaction", **values, "client_txn_id": client_txn_id,
	                      "source": "Manual"})
	frappe.db.savepoint("et_create_txn")
	try:
		doc.insert()
	except frappe.DuplicateEntryError:
		# Lost a race with a concurrent retry of the same request.
		frappe.db.rollback(save_point="et_create_txn")
		if client_txn_id and (existing := _by_client_id(user, client_txn_id)):
			return ok({"transaction": queries.get_row(user, existing), "duplicate": True})
		raise
	_remember_account(user, doc.account)
	return ok({"transaction": queries.get_row(user, doc.name), "duplicate": False})


@frappe.whitelist(methods=["POST"])
def update(name, data, expected_modified=None):
	"""Update a transaction. If ``expected_modified`` is given and the record changed
	since (e.g. edited on another device), raise a conflict instead of overwriting."""
	user = require_user()
	doc = frappe.get_doc("Finance Transaction", name)
	doc.check_permission("write")
	if expected_modified and str(doc.modified) != str(expected_modified):
		frappe.throw(
			_("This transaction was changed on another device. Reload it to see the latest version."),
			frappe.TimestampMismatchError,
		)
	if doc.savings_goal:
		frappe.throw(_("This transfer belongs to a savings goal. Edit it from the goal instead."))
	doc.update(pick(parse_dict(data), EDITABLE))
	doc.save()
	return ok({"transaction": queries.get_row(user, doc.name)})


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	doc = frappe.get_doc("Finance Transaction", name)
	doc.check_permission("delete")
	doc.delete()
	return ok({"name": name})


@frappe.whitelist(methods=["GET"])
def suggested_categories(transaction_type="Expense"):
	return ok(queries.suggested_categories(require_user(), transaction_type))


def _by_client_id(user, client_txn_id):
	return frappe.db.get_value("Finance Transaction", {"user": user, "client_txn_id": client_txn_id}, "name")


def _remember_account(user, account):
	frappe.db.set_value("Expense Profile", user, "last_used_account", account, update_modified=False)
