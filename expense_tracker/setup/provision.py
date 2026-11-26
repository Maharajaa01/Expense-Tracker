"""Idempotent per-user setup: profile, default categories, starter account."""

import frappe

from expense_tracker.setup.defaults import EXPENSE_CATEGORIES, INCOME_CATEGORIES, STARTER_ACCOUNT

ROLE = "Expense User"


def ensure_role() -> None:
	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc(
			{"doctype": "Role", "role_name": ROLE, "desk_access": 0, "is_custom": 0}
		).insert(ignore_permissions=True)


def ensure_user_setup(user: str) -> str:
	"""Make ``user`` ready to use the app. Safe to call on every boot.

	Returns the Expense Profile name. Fast path is a single indexed lookup.
	Seeds data only: access itself comes from the "Expense User" role, which
	an administrator assigns (never this function).
	"""
	if frappe.db.exists("Expense Profile", user):
		return user

	# Seed records as the user so ownership stamping applies normally.
	for order, (name, icon, color) in enumerate(EXPENSE_CATEGORIES):
		_category(user, name, "Expense", icon, color, order)
	for order, (name, icon, color) in enumerate(INCOME_CATEGORIES):
		_category(user, name, "Income", icon, color, order)

	account = frappe.get_doc({"doctype": "Finance Account", "user": user, **STARTER_ACCOUNT})
	account.insert(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "Expense Profile",
			"user": user,
			"default_account": account.name,
			"last_used_account": account.name,
		}
	).insert(ignore_permissions=True)
	# Boot runs on GET requests, which Frappe rolls back by default.
	frappe.local.flags.commit = True
	return user


def _category(user, name, ctype, icon, color, order):
	frappe.get_doc(
		{
			"doctype": "Finance Category",
			"user": user,
			"category_name": name,
			"category_type": ctype,
			"icon": icon,
			"color": color,
			"is_default": 1,
			"sort_order": order,
		}
	).insert(ignore_permissions=True)


def after_install():
	ensure_role()
