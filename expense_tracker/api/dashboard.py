"""Dashboard summary: one cached, server-aggregated payload."""

import frappe

from expense_tracker.api import ok, require_user
from expense_tracker.services import analytics, cache, periods
from expense_tracker.services.queries import list_transactions


@frappe.whitelist(methods=["GET"])
def summary(preset="this_month", from_date=None, to_date=None):
	user = require_user()
	week_start = frappe.db.get_value("Expense Profile", user, "week_start") or "Monday"
	period = periods.resolve(preset, from_date, to_date, week_start)
	key = f"dashboard:{period.start}:{period.end}:{frappe.utils.nowdate()}"
	# Cached per user and data version: any write bumps the version (services/cache.py).
	data = cache.cached(user, key, lambda: analytics.dashboard_summary(user, period, week_start), ttl=900)
	recent = list_transactions(user, {}, page=1, page_size=5)["data"]["rows"]
	return ok({**data, "recent": recent})
