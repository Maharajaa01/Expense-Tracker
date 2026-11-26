"""Public, whitelisted API surface of the Expense Tracker app.

Every endpoint in this package:

* runs as ``frappe.session.user`` – no endpoint accepts a ``user`` argument;
* delegates business rules to ``expense_tracker.services``;
* returns the envelope produced by :func:`ok` so the frontend can handle every
  response the same way. Errors are raised as normal Frappe exceptions (so
  transactions roll back) and are normalised by the frontend client.
"""

from typing import Any

import frappe
from frappe import _


def ok(data: Any = None, meta: dict | None = None) -> dict:
	"""Standard success envelope: ``{"ok": true, "data": ..., "meta": {...}}``."""
	out: dict[str, Any] = {"ok": True, "data": data}
	if meta is not None:
		out["meta"] = meta
	return out


ROLE = "Expense User"


def require_login() -> str:
	"""Return the session user, refusing Guest access explicitly."""
	user = frappe.session.user
	if not user or user == "Guest":
		raise frappe.PermissionError(_("Please log in to continue."))
	return user


def require_user() -> str:
	"""Return the session user if they may use the app.

	Access is granted only through the "Expense User" role, which an
	administrator assigns (the app never assigns it itself).
	"""
	user = require_login()
	if ROLE not in frappe.get_roles(user):
		raise frappe.PermissionError(
			_("You don't have access to Expense Tracker. Ask your administrator for the Expense User role.")
		)
	return user


def parse_dict(value) -> dict:
	"""Accept a dict or a JSON string from the client; anything else is an error."""
	value = frappe.parse_json(value) if isinstance(value, str) else value
	if value is None:
		return {}
	if not isinstance(value, dict):
		frappe.throw(_("Invalid request."))
	return value


def pick(data: dict, allowed) -> dict:
	"""Keep only whitelisted keys (never let a client set user, balances etc.)."""
	return {k: data[k] for k in allowed if k in data}
