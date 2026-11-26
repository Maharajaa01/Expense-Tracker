"""Per-user preferences."""

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user

EDITABLE = ("theme", "week_start", "default_account")


@frappe.whitelist(methods=["POST"])
def update(data):
	user = require_user()
	doc = frappe.get_doc("Expense Profile", user)
	doc.check_permission("write")
	values = pick(parse_dict(data), EDITABLE)
	if "theme" in values and values["theme"] not in ("System", "Light", "Dark"):
		frappe.throw(_("Invalid theme."))
	if "week_start" in values and values["week_start"] not in ("Monday", "Sunday"):
		frappe.throw(_("Invalid week start."))
	doc.update(values)
	doc.save()
	return ok({k: doc.get(k) for k in ("theme", "week_start", "default_account", "last_used_account")})
