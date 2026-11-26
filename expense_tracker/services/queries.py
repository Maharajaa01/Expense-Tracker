"""Read queries for transaction lists. Every query is scoped to one user."""

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _

from expense_tracker.services.money import to_number
from expense_tracker.services.periods import parse_date

SORTS = {
	"date_desc": "t.transaction_date desc, t.creation desc",
	"date_asc": "t.transaction_date asc, t.creation asc",
	"amount_desc": "t.amount desc, t.transaction_date desc",
	"amount_asc": "t.amount asc, t.transaction_date desc",
}
TYPES = ("Expense", "Income", "Transfer")
MAX_PAGE_SIZE = 100

# STRAIGHT_JOIN keeps `t` as the driving table: otherwise MariaDB starts from the
# (tiny) accounts table and sorts every matching row in a temporary table
# before applying LIMIT (≈270 ms at 50k rows vs a few ms walking the index).
_ROW_SELECT = """
	select straight_join t.name, t.transaction_type, t.transaction_date, t.amount, t.is_refund, t.title, t.notes,
		t.account, a.account_name, t.to_account, ta.account_name as to_account_name,
		t.category, c.category_name, c.icon as category_icon, c.color as category_color,
		c.parent_category, t.has_attachments, t.source, t.savings_goal, t.client_txn_id, t.modified,
		t.needs_review, t.bank_reference
	from `tabFinance Transaction` t
	join `tabFinance Account` a on a.name = t.account
	left join `tabFinance Account` ta on ta.name = t.to_account
	left join `tabFinance Category` c on c.name = t.category
"""

# Net spending: refunds count negative (docs/ACCOUNTING.md).
NET_EXPENSE_SQL = (
	"case when t.transaction_type = 'Expense' and t.is_refund = 0 then t.amount "
	"when t.transaction_type = 'Expense' and t.is_refund = 1 then -t.amount else 0 end"
)
INCOME_SQL = "case when t.transaction_type = 'Income' then t.amount else 0 end"


def serialize_row(r) -> dict:
	r = dict(r)
	r["amount"] = to_number(r["amount"])
	r["transaction_date"] = str(r["transaction_date"])
	r["modified"] = str(r["modified"])
	return r


def get_row(user: str, name: str) -> dict:
	rows = frappe.db.sql(_ROW_SELECT + " where t.user = %s and t.name = %s", (user, name), as_dict=True)
	if not rows:
		frappe.throw(_("Transaction not found."), frappe.DoesNotExistError)
	return serialize_row(rows[0])


def _escape_like(s: str) -> str:
	return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_filters(user: str, f: dict) -> tuple[list[str], dict]:
	"""Translate client filters into SQL. Unknown keys are ignored; values are bound params."""
	conds, vals = ["t.user = %(user)s"], {"user": user}
	if f.get("type"):
		if f["type"] not in TYPES:
			frappe.throw(_("Invalid transaction type filter."))
		conds.append("t.transaction_type = %(type)s")
		vals["type"] = f["type"]
	if f.get("account"):
		conds.append("(t.account = %(account)s or t.to_account = %(account)s)")
		vals["account"] = str(f["account"])
	if f.get("category"):
		# A parent category includes its subcategories.
		conds.append("(t.category = %(category)s or c.parent_category = %(category)s)")
		vals["category"] = str(f["category"])
	if f.get("needs_review"):
		conds.append("t.needs_review = 1")
	if d := parse_date(f.get("from_date"), "From date"):
		conds.append("t.transaction_date >= %(from_date)s")
		vals["from_date"] = d
	if d := parse_date(f.get("to_date"), "To date"):
		conds.append("t.transaction_date <= %(to_date)s")
		vals["to_date"] = d
	q = (f.get("q") or "").strip()[:100]
	if q:
		parts = ["t.title like %(q)s", "t.notes like %(q)s", "c.category_name like %(q)s"]
		vals["q"] = f"%{_escape_like(q)}%"
		# Typing "250" or "₹1,250" also matches that exact amount.
		try:
			amount = Decimal(q.replace(",", "").lstrip("₹").strip())
			if amount.is_finite() and amount > 0:
				vals["q_amount"] = amount
				parts.append("t.amount = %(q_amount)s")
		except InvalidOperation:
			pass
		conds.append("(" + " or ".join(parts) + ")")
	return conds, vals


_JOINS = """
	from `tabFinance Transaction` t
	left join `tabFinance Category` c on c.name = t.category
"""


def list_transactions(user: str, filters: dict, page: int = 1, page_size: int = 50, sort: str = "date_desc") -> dict:
	page = max(int(page or 1), 1)
	page_size = min(max(int(page_size or 50), 1), MAX_PAGE_SIZE)
	order = SORTS.get(sort) or SORTS["date_desc"]
	conds, vals = build_filters(user, filters)
	where = " where " + " and ".join(conds)
	vals.update(limit=page_size + 1, offset=(page - 1) * page_size)

	rows = frappe.db.sql(
		_ROW_SELECT + where + f" order by {order} limit %(limit)s offset %(offset)s", vals, as_dict=True
	)
	has_more = len(rows) > page_size
	rows = [serialize_row(r) for r in rows[:page_size]]

	# Daily totals for the days on this page, computed over *all* matching rows
	# so a day split across pages still shows its full total.
	day_totals = {}
	dates = sorted({r["transaction_date"] for r in rows})
	if dates:
		dvals = {**vals, "dates": tuple(dates)}
		for d, income, expense in frappe.db.sql(
			f"select t.transaction_date, sum({INCOME_SQL}), sum({NET_EXPENSE_SQL})"
			+ _JOINS + where + " and t.transaction_date in %(dates)s group by t.transaction_date",
			dvals,
		):
			day_totals[str(d)] = {"income": to_number(income), "expense": to_number(expense)}

	out = {"rows": rows, "day_totals": day_totals}
	meta = {"page": page, "page_size": page_size, "has_more": has_more}
	if page == 1:
		count, income, expense = frappe.db.sql(
			f"select count(*), coalesce(sum({INCOME_SQL}), 0), coalesce(sum({NET_EXPENSE_SQL}), 0)" + _JOINS + where,
			vals,
		)[0]
		meta["total"] = int(count)
		out["summary"] = {"income": to_number(income), "expense": to_number(expense)}
	return {"data": out, "meta": meta}


def suggested_categories(user: str, ttype: str, limit: int = 8) -> dict:
	"""Recently and frequently used categories for Quick Add."""
	if ttype not in ("Expense", "Income"):
		return {"recent": [], "frequent": []}
	recent = frappe.db.sql(
		"""select t.category from `tabFinance Transaction` t
		join `tabFinance Category` c on c.name = t.category and c.is_archived = 0
		where t.user = %s and t.transaction_type = %s and t.category is not null
		group by t.category order by max(t.creation) desc limit %s""",
		(user, ttype, limit),
		pluck=True,
	)
	frequent = frappe.db.sql(
		"""select t.category from `tabFinance Transaction` t
		join `tabFinance Category` c on c.name = t.category and c.is_archived = 0
		where t.user = %s and t.transaction_type = %s and t.category is not null
		and t.transaction_date >= date_sub(curdate(), interval 90 day)
		group by t.category order by count(*) desc limit %s""",
		(user, ttype, limit),
		pluck=True,
	)
	return {"recent": recent, "frequent": frequent}
