"""Row-level isolation: a user only ever sees and touches their own records.

Wired in hooks.py for every DocType in ``USER_DOCTYPES``. Administrator is the
only exception (needed by the scheduler and for support from the console).
System Managers are deliberately *not* exempt: personal finances stay private.
"""

import frappe

from expense_tracker.services.ownership import SUPERUSER, USER_DOCTYPES


def get_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if user == SUPERUSER or doctype not in USER_DOCTYPES:
		return ""
	return f"`tab{doctype}`.`user` = {frappe.db.escape(user)}"


def has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if user == SUPERUSER:
		return True
	owner = doc.get("user")
	if not owner:
		# Unsaved document: allowed; the controller stamps doc.user = session user.
		return doc.is_new() if hasattr(doc, "is_new") else False
	return owner == user
