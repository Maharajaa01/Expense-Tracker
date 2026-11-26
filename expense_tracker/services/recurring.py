"""Recurring transactions: posting due occurrences, reminders and upcoming lists.

Duplicate safety: every generated transaction has the deterministic
client_txn_id ``rec:<recurring>:<YYYY-MM-DD>`` and (user, client_txn_id) is a
unique index, so an occurrence can never be posted twice, even if the job
runs twice or two workers race.
"""

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from expense_tracker.services.money import format_inr, to_number
from expense_tracker.services.recurrence import first_on_or_after, occurrence, occurrences_between

MAX_CATCH_UP = 12  # occurrences per template per run (e.g. a year of missed monthly runs)

FIELDS = ["name", "user", "title", "transaction_type", "amount", "account", "to_account", "category", "notes",
          "frequency", "interval", "custom_unit", "start_date", "end_date", "next_run_date", "last_run_date",
          "occurrences_posted", "auto_post", "remind_days_before", "is_active", "modified"]


def client_id(rec_name: str, d) -> str:
	return f"rec:{rec_name}:{getdate(d)}"


def _next_after(rec, d) -> date | None:
	_idx, nxt = first_on_or_after(rec.start_date, add_days(d, 1), rec.frequency, rec.interval, rec.custom_unit)
	if rec.end_date and nxt > getdate(rec.end_date):
		return None
	return nxt


def post_occurrence(rec, on_date) -> tuple[str, bool]:
	"""Create the transaction for one occurrence. Returns (name, created)."""
	cid = client_id(rec.name, on_date)
	existing = frappe.db.get_value("Finance Transaction", {"user": rec.user, "client_txn_id": cid}, "name")
	if existing:
		return existing, False
	doc = frappe.get_doc({
		"doctype": "Finance Transaction",
		"user": rec.user,
		"transaction_type": rec.transaction_type,
		"amount": rec.amount,
		"account": rec.account,
		"to_account": rec.to_account,
		"category": rec.category,
		"title": rec.title,
		"notes": rec.notes,
		"transaction_date": on_date,
		"client_txn_id": cid,
		"source": "Recurring",
		"recurring_transaction": rec.name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name, True


def _advance(rec_name: str, posted_on, posted: bool):
	rec = frappe.get_doc("Recurring Transaction", rec_name)
	nxt = _next_after(rec, posted_on)
	values = {"next_run_date": nxt, "last_run_date": posted_on}
	if posted:
		values["occurrences_posted"] = (rec.occurrences_posted or 0) + 1
	if nxt is None:
		values["is_active"] = 0  # schedule finished
	frappe.db.set_value("Recurring Transaction", rec_name, values)


def process_template(rec, today=None) -> int:
	"""Post every due occurrence (up to MAX_CATCH_UP) of one auto-posting template."""
	today = getdate(today or nowdate())
	posted = 0
	for _attempt in range(MAX_CATCH_UP):
		rec = frappe._dict(frappe.db.get_value("Recurring Transaction", rec.name, FIELDS, as_dict=True))
		if not rec.is_active or not rec.next_run_date or getdate(rec.next_run_date) > today:
			break
		due = getdate(rec.next_run_date)
		frappe.db.savepoint("et_recurring_post")
		try:
			_txn, created = post_occurrence(rec, due)
		except Exception as e:
			frappe.db.rollback(save_point="et_recurring_post")
			_notify(rec.user, "Danger", _("Couldn't add {0}").format(rec.title),
			        _("The payment due on {0} wasn't recorded: {1} Open Recurring payments to fix it.").format(
				        frappe.format(due, "Date"), frappe.utils.strip_html(str(e))),
			        rec.name, f"recur-fail:{rec.name}:{due}")
			frappe.log_error(title=f"Expense Tracker: recurring {rec.name} failed")
			break
		_advance(rec.name, due, created)
		posted += int(created)
	return posted


def post_due(today=None) -> int:
	"""Scheduler entry: post due occurrences for all users. Commits per template."""
	today = getdate(today or nowdate())
	total = 0
	for rec in frappe.get_all("Recurring Transaction",
	                          filters={"is_active": 1, "auto_post": 1, "next_run_date": ("<=", today)},
	                          fields=["name"]):
		total += process_template(rec, today)
		frappe.db.commit()
	return total


def send_reminders(today=None) -> int:
	"""Reminders for upcoming payments, and 'due today' for manual (non auto-post) ones."""
	today = getdate(today or nowdate())
	sent = 0
	for rec in frappe.get_all("Recurring Transaction", filters={"is_active": 1, "next_run_date": ("is", "set")}, fields=FIELDS):
		due = getdate(rec.next_run_date)
		days = (due - today).days
		if not rec.auto_post and days <= 0:
			title = _("{0} is due").format(rec.title) if days == 0 else _("{0} is overdue").format(rec.title)
			key = f"recur-due:{rec.name}:{due}"
		elif 0 < days <= (rec.remind_days_before or 0):
			title = _("{0} due in {1} days").format(rec.title, days) if days > 1 else _("{0} due tomorrow").format(rec.title)
			key = f"recur-remind:{rec.name}:{due}"
		else:
			continue
		if _notify(rec.user, "Warning" if days <= 0 else "Info", title,
		           _("{0} on {1}.").format(format_inr(rec.amount), frappe.format(due, "Date")), rec.name, key):
			sent += 1
	return sent


def _notify(user, severity, title, message, rec_name, key) -> bool:
	if frappe.db.exists("Finance Notification", {"dedup_key": key}):
		return False
	frappe.get_doc({
		"doctype": "Finance Notification", "user": user, "notification_type": "Recurring", "severity": severity,
		"title": title[:140], "message": message, "reference_doctype": "Recurring Transaction",
		"reference_name": rec_name, "dedup_key": key,
	}).insert(ignore_permissions=True)
	return True


def post_now(rec_name: str) -> str:
	"""Record the next occurrence now (e.g. "Mark as paid" for a manual bill)."""
	rec = frappe._dict(frappe.db.get_value("Recurring Transaction", rec_name, FIELDS, as_dict=True))
	if not rec.next_run_date:
		frappe.throw(_("This schedule has no upcoming payment."))
	name, created = post_occurrence(rec, rec.next_run_date)
	_advance(rec.name, rec.next_run_date, created)
	return name


def skip_next(rec_name: str) -> None:
	rec = frappe._dict(frappe.db.get_value("Recurring Transaction", rec_name, FIELDS, as_dict=True))
	if not rec.next_run_date:
		frappe.throw(_("This schedule has no upcoming payment."))
	_advance(rec.name, rec.next_run_date, posted=False)


def upcoming(user: str, days: int = 30, today=None) -> list[dict]:
	"""Occurrences due in the next ``days`` days (including overdue manual ones)."""
	today = getdate(today or nowdate())
	horizon = today + timedelta(days=days)
	out = []
	recs = frappe.get_all("Recurring Transaction", filters={"user": user, "is_active": 1, "next_run_date": ("is", "set")}, fields=FIELDS)
	for rec in recs:
		start = getdate(rec.next_run_date)
		end = min(horizon, getdate(rec.end_date)) if rec.end_date else horizon
		dates = occurrences_between(rec.start_date, start, end, rec.frequency, rec.interval, rec.custom_unit, limit=60)
		for d in dates:
			out.append({
				"recurring": rec.name, "title": rec.title, "transaction_type": rec.transaction_type,
				"amount": to_number(rec.amount), "date": str(d), "overdue": d < today, "auto_post": int(rec.auto_post),
				"category": rec.category, "account": rec.account,
			})
	return sorted(out, key=lambda x: x["date"])


def describe(rec) -> str:
	"""Plain-language schedule, e.g. 'Every month on the 5th'."""
	n = int(rec.interval or 1)
	unit = {"Daily": "day", "Weekly": "week", "Monthly": "month", "Quarterly": "quarter", "Yearly": "year"}.get(rec.frequency)
	if rec.frequency == "Custom":
		unit = {"Days": "day", "Weeks": "week", "Months": "month"}[rec.custom_unit or "Days"]
	return f"Every {unit}" if n == 1 else f"Every {n} {unit}s"
