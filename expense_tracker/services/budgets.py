"""Budget progress, history and alerts (docs/ACCOUNTING.md, "Budgets")."""

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, get_last_day, getdate, nowdate

from expense_tracker.services.money import D, ZERO, format_inr, percent, to_number
from expense_tracker.services.queries import NET_EXPENSE_SQL

THRESHOLDS = (("alert_50", 50), ("alert_80", 80), ("alert_100", 100))


def period_for(budget, ref=None) -> tuple[date, date] | None:
	"""The budget period containing ``ref`` (None if the budget hasn't started or has ended)."""
	ref = getdate(ref or nowdate())
	start = getdate(budget.start_date)
	if budget.period_type == "Custom":
		end = getdate(budget.end_date)
		return (start, end) if start <= ref <= end else None
	if ref < getdate(get_first_day(start)):
		return None
	return getdate(get_first_day(ref)), getdate(get_last_day(ref))


def spent(user: str, category: str | None, start: date, end: date) -> "D":
	"""Net spending in the window; a parent category includes its subcategories."""
	cond, vals = "", [user, start, end]
	if category:
		cond = " and (t.category = %s or c.parent_category = %s)"
		vals += [category, category]
	value = frappe.db.sql(
		f"""select coalesce(sum({NET_EXPENSE_SQL}), 0)
		from `tabFinance Transaction` t
		left join `tabFinance Category` c on c.name = t.category
		where t.user = %s and t.transaction_type = 'Expense' and t.transaction_date between %s and %s{cond}""",
		vals,
	)[0][0]
	return D(value)


def carried(budget, start: date) -> "D":
	"""Unspent amount from the previous month (monthly budgets with carry-forward only).

	One month only and never negative: overspending doesn't shrink next month,
	and unspent money doesn't snowball indefinitely.
	"""
	if budget.period_type != "Monthly" or not budget.carry_forward:
		return ZERO
	prev_start = getdate(add_months(start, -1))
	if prev_start < getdate(get_first_day(budget.start_date)):
		return ZERO
	prev_end = getdate(get_last_day(prev_start))
	return max(D(budget.amount) - spent(budget.user, budget.category, prev_start, prev_end), ZERO)


def level(pct: float | None) -> str:
	if pct is None:
		return "ok"
	if pct > 100:
		return "over"
	if pct >= 100:
		return "100"
	if pct >= 80:
		return "80"
	if pct >= 50:
		return "50"
	return "ok"


def progress(budget, ref=None) -> dict | None:
	window = period_for(budget, ref)
	if not window:
		return None
	start, end = window
	carry = carried(budget, start)
	available = D(budget.amount) + carry
	used = spent(budget.user, budget.category, start, end)
	pct = percent(used, available)
	return {
		"from_date": str(start),
		"to_date": str(end),
		"amount": to_number(budget.amount),
		"carried": to_number(carry),
		"available": to_number(available),
		"spent": to_number(used),
		"remaining": to_number(available - used),
		"percent": pct,
		"level": level(pct),
	}


BUDGET_FIELDS = ["name", "user", "budget_name", "category", "amount", "period_type", "start_date", "end_date",
                 "carry_forward", "is_active", "alert_50", "alert_80", "alert_100", "modified"]


def _serialize(b, prog) -> dict:
	cat = frappe.db.get_value("Finance Category", b.category, ["category_name", "icon", "color"], as_dict=True) if b.category else None
	return {
		"name": b.name,
		"budget_name": b.budget_name,
		"category": b.category,
		"category_name": cat.category_name if cat else None,
		"icon": cat.icon if cat else "chart-pie",
		"color": cat.color if cat else "#10b981",
		"period_type": b.period_type,
		"start_date": str(b.start_date),
		"end_date": str(b.end_date) if b.end_date else None,
		"carry_forward": int(b.carry_forward),
		"is_active": int(b.is_active),
		"alert_50": int(b.alert_50), "alert_80": int(b.alert_80), "alert_100": int(b.alert_100),
		"modified": str(b.modified),
		"progress": prog,
	}


def list_with_progress(user: str, ref=None, include_inactive: bool = False) -> list[dict]:
	filters = {"user": user}
	if not include_inactive:
		filters["is_active"] = 1
	budgets = frappe.get_all("Finance Budget", filters=filters, fields=BUDGET_FIELDS, order_by="category is not null, budget_name")
	return [_serialize(b, progress(b, ref)) for b in budgets]


def history(budget, months: int = 6, ref=None) -> list[dict]:
	"""Per-month progress for the last ``months`` months (monthly budgets)."""
	ref = getdate(ref or nowdate())
	out = []
	for i in range(months - 1, -1, -1):
		month = getdate(add_months(get_first_day(ref), -i))
		p = progress(budget, month)
		if p:
			out.append({"month": str(month), **p})
	return out


def evaluate_alerts(user: str, ref=None) -> int:
	"""Create one notification per budget, period and crossed threshold. Returns count created."""
	created = 0
	for b in frappe.get_all("Finance Budget", filters={"user": user, "is_active": 1}, fields=BUDGET_FIELDS):
		p = progress(b, ref)
		if not p or p["percent"] is None:
			continue
		crossed = [t for field, t in THRESHOLDS if b.get(field) and p["percent"] >= t]
		if p["percent"] > 100:
			crossed.append("over")
		if not crossed:
			continue
		top = crossed[-1]  # only the most severe new alert is shown; lower ones are recorded silently for de-duplication
		for t in crossed:
			key = f"budget:{b.name}:{p['from_date']}:{t}"
			if frappe.db.exists("Finance Notification", {"dedup_key": key}):
				continue
			silent = t != top
			title, severity = _alert_text(b, p, t)
			frappe.get_doc({
				"doctype": "Finance Notification",
				"user": user,
				"notification_type": "Budget",
				"severity": severity,
				"title": title,
				"message": (
					_("{0} of {1} spent, {2} over.").format(format_inr(p["spent"]), format_inr(p["available"]), format_inr(-p["remaining"]))
					if p["remaining"] < 0
					else _("{0} of {1} spent, {2} left.").format(format_inr(p["spent"]), format_inr(p["available"]), format_inr(p["remaining"]))
				),
				"reference_doctype": "Finance Budget",
				"reference_name": b.name,
				"dedup_key": key,
				"is_read": 1 if silent else 0,
				"is_silent": 1 if silent else 0,
			}).insert(ignore_permissions=True)
			created += 1
	return created


def _alert_text(b, p, t):
	name = b.budget_name
	if t == "over":
		return _("{0} is over budget by {1}").format(name, format_inr(-p["remaining"])), "Danger"
	if t == 100:
		return _("{0} budget is used up").format(name), "Danger"
	if t == 80:
		return _("{0} budget is 80% used").format(name), "Warning"
	return _("{0} budget is half used").format(name), "Info"


def evaluate_alerts_safely(user: str) -> None:
	"""Called after money changes. Alert problems are logged, never block a save."""
	try:
		frappe.db.savepoint("et_budget_alerts")
		evaluate_alerts(user)
	except Exception:
		frappe.db.rollback(save_point="et_budget_alerts")
		frappe.log_error(title="Expense Tracker: budget alert evaluation failed")
