"""Boot payload consumed by the SPA shell (``/expense``)."""

import frappe

import expense_tracker
from expense_tracker.api import ok, require_user
from expense_tracker.setup.provision import ensure_user_setup


def get_boot_data() -> dict:
	"""Data the SPA needs before its first render. Never contains secrets."""
	user = require_user()
	ensure_user_setup(user)
	profile = frappe.db.get_value(
		"Expense Profile", user, ["default_account", "last_used_account", "theme", "week_start"], as_dict=True
	)
	user_doc = frappe.db.get_value(
		"User", user, ["full_name", "first_name", "user_image", "time_zone"], as_dict=True
	)
	return {
		"user": {
			"name": user,
			"full_name": user_doc.full_name if user_doc else user,
			"first_name": (user_doc.first_name if user_doc else None) or user,
			"image": user_doc.user_image if user_doc else None,
			"time_zone": (user_doc.time_zone if user_doc else None) or frappe.utils.get_system_timezone(),
		},
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"app_version": expense_tracker.__version__,
		"currency": "INR",
		"profile": profile,
		"server_date": frappe.utils.nowdate(),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_boot():
	"""Refresh boot data (used in Vite dev mode and after re-login)."""
	return ok(get_boot_data())
