"""Row-level ownership checks shared by controllers and APIs."""

import frappe
from frappe import _

# DocTypes whose rows belong to exactly one user via the `user` field.
USER_DOCTYPES = (
	"Expense Profile",
	"Finance Account",
	"Finance Category",
	"Finance Transaction",
	"Finance Budget",
	"Recurring Transaction",
	"Savings Goal",
	"Transaction Attachment",
	"Finance Notification",
	"Offline Sync Log",
	"Bank Alert",
)

# Only Administrator (used by the scheduler) may act on another user's data.
SUPERUSER = "Administrator"


def assign_user(doc) -> None:
	"""Stamp ``doc.user`` on new documents.

	Regular users always own what they create – any ``user`` value sent by the
	client is overwritten. Administrator (scheduler, installers, tests) must
	set ``user`` explicitly.
	"""
	session_user = frappe.session.user
	if doc.is_new():
		if session_user != SUPERUSER or not doc.get("user"):
			doc.user = session_user
	if not doc.get("user") or doc.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)


def get_owned(doctype: str, name: str | None, user: str, fields=("name",), label: str | None = None):
	"""Fetch ``fields`` of a record that must belong to ``user``.

	Raises ``DoesNotExistError`` for both missing and foreign records so the
	API never reveals whether another user's record exists.
	"""
	if not name:
		return None
	row = frappe.db.get_value(doctype, name, ["user", *fields], as_dict=True)
	if not row or row.user != user:
		frappe.throw(
			_("{0} {1} not found.").format(_(label or doctype), frappe.bold(name)), frappe.DoesNotExistError
		)
	return row
