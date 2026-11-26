"""Analytics: server-side aggregation for the chosen period."""

import frappe

from expense_tracker.api import ok, require_user
from expense_tracker.services import analytics, cache, periods


@frappe.whitelist(methods=["GET"])
def summary(preset="this_month", from_date=None, to_date=None):
	user = require_user()
	week_start = frappe.db.get_value("Expense Profile", user, "week_start") or "Monday"
	period = periods.resolve(preset, from_date, to_date, week_start)
	key = f"analytics:{period.start}:{period.end}:{frappe.utils.nowdate()}"
	return ok(cache.cached(user, key, lambda: analytics.analytics_summary(user, period, week_start), ttl=900))
