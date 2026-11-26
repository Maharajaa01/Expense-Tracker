"""Receipt endpoints. Files are private and only reachable through the owner's transaction."""

import frappe
from frappe import _

from expense_tracker.api import ok, require_user
from expense_tracker.services import receipts


@frappe.whitelist(methods=["POST"])
def upload(transaction):
	"""Multipart upload: form field ``file`` plus ``transaction``."""
	user = require_user()
	f = frappe.request.files.get("file") if frappe.request and frappe.request.files else None
	if not f:
		frappe.throw(_("Choose a file to attach."))
	content = f.stream.read(receipts.MAX_BYTES + 1)
	return ok(receipts.attach(user, transaction, f.filename, content))


@frappe.whitelist(methods=["GET"])
def list(transaction):  # noqa: A001
	return ok(receipts.list_for(require_user(), transaction))


@frappe.whitelist(methods=["POST"])
def delete(name):
	require_user()
	doc = frappe.get_doc("Transaction Attachment", name)
	doc.check_permission("delete")
	doc.delete()
	return ok({"name": name})
