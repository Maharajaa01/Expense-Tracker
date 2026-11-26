"""Server-side aggregation for the dashboard and analytics (docs/ACCOUNTING.md)."""

from datetime import date, timedelta

import frappe
from frappe.utils import add_months, get_first_day, getdate

from expense_tracker.services.money import D, ZERO, percent, percent_change, to_number
from expense_tracker.services.periods import Period
from expense_tracker.services.queries import INCOME_SQL, NET_EXPENSE_SQL


def totals(user: str, start: date, end: date) -> dict:
	income, expense = frappe.db.sql(
		f"""select coalesce(sum({INCOME_SQL}), 0), coalesce(sum({NET_EXPENSE_SQL}), 0)
		from `tabFinance Transaction` t
		where t.user = %s and t.transaction_date between %s and %s""",
		(user, start, end),
	)[0]
	income, expense = D(income), D(expense)
	savings = income - expense
	return {
		"income": to_number(income),
		"expense": to_number(expense),
		"savings": to_number(savings),
		# None when there is no income: a rate would be meaningless.
		"savings_rate": percent(savings, income),
	}


def net_worth(user: str) -> dict:
	rows = frappe.db.sql(
		"""select name, account_name, account_type, current_balance, credit_limit, icon, color, include_in_totals
		from `tabFinance Account` where user = %s and is_archived = 0
		order by sort_order, creation""",
		user,
		as_dict=True,
	)
	total = sum((D(r.current_balance) for r in rows if r.include_in_totals), ZERO)
	return {
		"total": to_number(total),
		"account_count": len(rows),
		"accounts": [
			{
				"name": r.name,
				"account_name": r.account_name,
				"account_type": r.account_type,
				"balance": to_number(r.current_balance),
				"icon": r.icon,
				"color": r.color,
			}
			for r in rows
		],
	}


def by_category(user: str, start: date, end: date, ttype: str = "Expense", limit: int | None = None) -> list[dict]:
	"""Totals per top-level category (subcategories roll up into their parent)."""
	amount_sql = NET_EXPENSE_SQL if ttype == "Expense" else INCOME_SQL
	rows = frappe.db.sql(
		f"""select coalesce(c.parent_category, c.name) as cat, sum({amount_sql}) as amount, count(*) as cnt
		from `tabFinance Transaction` t
		join `tabFinance Category` c on c.name = t.category
		where t.user = %s and t.transaction_type = %s and t.transaction_date between %s and %s
		group by cat having amount <> 0 order by amount desc""",
		(user, ttype, start, end),
		as_dict=True,
	)
	if not rows:
		return []
	meta = {
		r.name: r
		for r in frappe.get_all(
			"Finance Category",
			filters={"name": ("in", [r.cat for r in rows]), "user": user},
			fields=["name", "category_name", "icon", "color"],
		)
	}
	total = sum((D(r.amount) for r in rows if D(r.amount) > 0), ZERO)
	out = []
	for r in rows:
		m = meta.get(r.cat)
		if not m:
			continue
		out.append(
			{
				"category": r.cat,
				"category_name": m.category_name,
				"icon": m.icon,
				"color": m.color,
				"amount": to_number(r.amount),
				"count": int(r.cnt),
				"share": percent(max(D(r.amount), ZERO), total),
			}
		)
	return out[:limit] if limit else out


def _bucket_start(d: date, granularity: str, week_start: str) -> date:
	if granularity == "day":
		return d
	if granularity == "week":
		offset = (d.weekday() + (1 if week_start == "Sunday" else 0)) % 7
		return d - timedelta(days=offset)
	return d.replace(day=1)


def series(user: str, start: date, end: date, granularity: str = "day", week_start: str = "Monday") -> list[dict]:
	"""Income and net spending per day/week/month, with empty buckets filled with 0."""
	if granularity not in ("day", "week", "month"):
		granularity = "day"
	raw = frappe.db.sql(
		f"""select t.transaction_date, sum({INCOME_SQL}), sum({NET_EXPENSE_SQL})
		from `tabFinance Transaction` t
		where t.user = %s and t.transaction_date between %s and %s
		group by t.transaction_date""",
		(user, start, end),
	)
	buckets: dict[date, list] = {}
	cur = _bucket_start(start, granularity, week_start)
	while cur <= end:
		buckets[cur] = [ZERO, ZERO]
		if granularity == "day":
			cur += timedelta(days=1)
		elif granularity == "week":
			cur += timedelta(days=7)
		else:
			cur = getdate(add_months(cur, 1))
	for d, inc, exp in raw:
		b = buckets.setdefault(_bucket_start(getdate(d), granularity, week_start), [ZERO, ZERO])
		b[0] += D(inc)
		b[1] += D(exp)
	return [
		{"period": str(k), "income": to_number(v[0]), "expense": to_number(v[1])}
		for k, v in sorted(buckets.items())
	]


def monthly_income_expense(user: str, months: int = 6, today=None) -> list[dict]:
	end_month = getdate(get_first_day(today or frappe.utils.nowdate()))
	start = getdate(add_months(end_month, -(months - 1)))
	end = getdate(frappe.utils.get_last_day(end_month))
	return series(user, start, end, "month")


def granularity_for(period: Period) -> str:
	return "day" if period.days <= 62 else "week" if period.days <= 370 else "month"


PREV_LABEL = {"today": "yesterday", "this_week": "last week", "this_month": "last month",
              "last_month": "the month before", "this_quarter": "last quarter", "this_year": "last year"}


def savings_trend(user: str, months: int = 12) -> list[dict]:
	out = []
	for p in monthly_income_expense(user, months):
		inc, exp = D(p["income"]), D(p["expense"])
		out.append({**p, "savings": to_number(inc - exp), "rate": percent(inc - exp, inc)})
	return out


def category_comparison(current: list[dict], previous: list[dict], limit: int = 8) -> list[dict]:
	"""Per category: this period vs previous (union of both, largest first)."""
	prev = {c["category"]: c for c in previous}
	cur = {c["category"]: c for c in current}
	keys = sorted(set(cur) | set(prev), key=lambda k: -max(cur.get(k, {}).get("amount", 0), prev.get(k, {}).get("amount", 0)))
	out = []
	for k in keys[:limit]:
		meta = cur.get(k) or prev.get(k)
		a, b = cur.get(k, {}).get("amount", 0), prev.get(k, {}).get("amount", 0)
		out.append({"category": k, "category_name": meta["category_name"], "icon": meta["icon"], "color": meta["color"],
		            "current": a, "previous": b, "change": percent_change(a, b)})
	return out


def analytics_summary(user: str, period: Period, week_start: str = "Monday") -> dict:
	from expense_tracker.services import budgets, insights

	current = totals(user, period.start, period.end)
	previous = totals(user, period.prev_start, period.prev_end)
	cats = by_category(user, period.start, period.end, "Expense")
	prev_cats = by_category(user, period.prev_start, period.prev_end, "Expense")
	budget_rows = budgets.list_with_progress(user, period.end if period.end < getdate(frappe.utils.nowdate()) else None)
	g = granularity_for(period)
	return {
		"period": period.as_dict(),
		"totals": current,
		"previous": previous,
		"change": {"income": percent_change(current["income"], previous["income"]),
		           "expense": percent_change(current["expense"], previous["expense"])},
		"categories": cats,
		"income_categories": by_category(user, period.start, period.end, "Income"),
		"comparison": category_comparison(cats, prev_cats),
		"trend": {"granularity": g, "points": series(user, period.start, period.end, g, week_start)},
		"daily": series(user, period.start, period.end, "day") if period.days <= 93 else None,
		"monthly": monthly_income_expense(user, 12),
		"savings": savings_trend(user, 12),
		"budgets": [b for b in budget_rows if b["progress"]],
		"insights": insights.generate(current, previous, cats, prev_cats, budget_rows,
		                              PREV_LABEL.get(period.preset, "the previous period")),
	}


def dashboard_summary(user: str, period: Period, week_start: str = "Monday") -> dict:
	from expense_tracker.services import budgets, goals, insights, recurring

	granularity = granularity_for(period)
	current = totals(user, period.start, period.end)
	previous = totals(user, period.prev_start, period.prev_end)
	cats = by_category(user, period.start, period.end, "Expense")
	budget_rows = budgets.list_with_progress(user)
	return {
		"period": period.as_dict(),
		"totals": current,
		"previous": previous,
		"change": {
			"income": percent_change(current["income"], previous["income"]),
			"expense": percent_change(current["expense"], previous["expense"]),
		},
		"net_worth": net_worth(user),
		"categories": cats,
		"trend": {"granularity": granularity, "points": series(user, period.start, period.end, granularity, week_start)},
		"monthly": monthly_income_expense(user, 6),
		# Budgets at 80 %+ of this month's allowance.
		"budget_alerts": [b for b in budget_rows if b["progress"] and b["progress"]["level"] in ("80", "100", "over")],
		"budgets_count": len(budget_rows),
		"to_categorise": frappe.db.count("Finance Transaction", {"user": user, "needs_review": 1}),
		"upcoming": recurring.upcoming(user, 7)[:5],
		"goals": goals.list_goals(user)[:3],
		"insights": insights.generate(
			current, previous, cats, by_category(user, period.prev_start, period.prev_end, "Expense"), budget_rows,
			PREV_LABEL.get(period.preset, "the previous period"), limit=3),
	}
