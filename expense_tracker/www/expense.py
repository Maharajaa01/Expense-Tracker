"""Serves the Vue SPA at ``/expense`` (and ``/expense/*`` via website_route_rules)."""

import frappe

from expense_tracker.api.boot import get_boot_data

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(
			frappe.request.path if frappe.request else "/expense"
		)
		raise frappe.Redirect

	# Raises PermissionError (Frappe's 403 page) for users without the
	# "Expense User" role. Boot values are injected into window.* by the
	# frappe-ui jinjaBootData plugin.
	context.boot = get_boot_data()
	context.no_cache = 1
	return context
