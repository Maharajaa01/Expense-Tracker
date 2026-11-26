"""Plain-language insights generated only from calculated figures.

Each rule has a minimum-data threshold so the app never makes claims from
noise (e.g. "+400%" on a ₹20 base). No insight is invented: if no rule
applies, the list is empty.
"""

from frappe import _

from expense_tracker.services.money import D, format_inr

MIN_CATEGORY_BASE = D(500)  # previous-period spend needed before quoting a % change
MIN_CHANGE_PCT = 10
MIN_TOTAL_DIFF = D(100)


def generate(totals: dict, previous: dict, categories: list[dict], prev_categories: list[dict],
             budgets: list[dict] | None = None, prev_label: str = "last month", limit: int = 5) -> list[dict]:
	out: list[dict] = []
	spent, prev_spent = D(totals["expense"]), D(previous["expense"])
	income = D(totals["income"])

	# Largest category
	if categories and spent > 0:
		top = categories[0]
		out.append({
			"kind": "top_category", "tone": "neutral", "icon": top["icon"] or "tag",
			"text": _("Your largest expense category is {0}, at {1} ({2}% of spending).").format(
				top["category_name"], format_inr(top["amount"]), round(top["share"] or 0)),
		})

	# Total spending vs previous period
	diff = spent - prev_spent
	if prev_spent > 0 and abs(diff) >= MIN_TOTAL_DIFF:
		out.append({
			"kind": "total_change", "tone": "good" if diff < 0 else "warning",
			"icon": "trending-up" if diff > 0 else "arrow-down-left",
			"text": (_("You spent {0} less than {1}.") if diff < 0 else _("You spent {0} more than {1}.")).format(
				format_inr(abs(diff)), prev_label),
		})

	# Biggest category movement
	prev_map = {c["category"]: D(c["amount"]) for c in prev_categories}
	moves = []
	for c in categories:
		base = prev_map.get(c["category"], D(0))
		if base >= MIN_CATEGORY_BASE:
			pct = (D(c["amount"]) - base) / base * 100
			if abs(pct) >= MIN_CHANGE_PCT:
				moves.append((abs(pct), pct, c))
	if moves:
		_abs, pct, c = max(moves, key=lambda m: m[0])
		out.append({
			"kind": "category_change", "tone": "warning" if pct > 0 else "good", "icon": c["icon"] or "tag",
			"text": (_("Your {0} spending increased by {1}% compared with {2}.") if pct > 0
			         else _("Your {0} spending dropped by {1}% compared with {2}.")).format(
				c["category_name"].lower() if c["category_name"].isascii() else c["category_name"], round(abs(pct)), prev_label),
		})

	# Savings rate
	if income > 0:
		rate = round((income - spent) / income * 100)
		if rate >= 0:
			out.append({"kind": "savings", "tone": "good" if rate >= 20 else "neutral", "icon": "piggy-bank",
			            "text": _("You have saved {0}% of your income.").format(rate)})
		else:
			out.append({"kind": "savings", "tone": "warning", "icon": "triangle-alert",
			            "text": _("You spent {0} more than you earned.").format(format_inr(spent - income))})

	# Budgets
	over = [b for b in (budgets or []) if b.get("progress") and b["progress"]["level"] == "over"]
	if over:
		out.append({"kind": "budgets_over", "tone": "warning", "icon": "chart-pie",
		            "text": (_("{0} is over budget.").format(over[0]["budget_name"]) if len(over) == 1
		                     else _("{0} budgets are over their limit.").format(len(over)))})
	return out[:limit]
