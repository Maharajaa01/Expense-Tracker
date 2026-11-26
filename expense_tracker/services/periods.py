"""Date-range presets shared by the dashboard, transactions and analytics."""

from dataclasses import dataclass
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, get_last_day, getdate, nowdate

PRESETS = ("today", "this_week", "this_month", "last_month", "this_quarter", "this_year", "custom")
MAX_RANGE_DAYS = 366 * 5


@dataclass
class Period:
	preset: str
	start: date
	end: date
	prev_start: date
	prev_end: date

	@property
	def days(self) -> int:
		return (self.end - self.start).days + 1

	def as_dict(self) -> dict:
		return {
			"preset": self.preset,
			"from_date": str(self.start),
			"to_date": str(self.end),
			"prev_from_date": str(self.prev_start),
			"prev_to_date": str(self.prev_end),
			"days": self.days,
		}


def parse_date(value, label="Date") -> date | None:
	if value in (None, ""):
		return None
	try:
		return getdate(value)
	except Exception:
		frappe.throw(_("{0} is not a valid date.").format(_(label)))


def resolve(preset: str | None, from_date=None, to_date=None, week_start: str = "Monday", today=None) -> Period:
	"""Resolve a preset to concrete dates plus the comparable previous period."""
	preset = preset or "this_month"
	if preset not in PRESETS:
		frappe.throw(_("Unknown period."))
	today = getdate(today or nowdate())

	if preset == "today":
		start = end = today
		return Period(preset, start, end, start - timedelta(days=1), end - timedelta(days=1))
	if preset == "this_week":
		offset = (today.weekday() + (1 if week_start == "Sunday" else 0)) % 7
		start = today - timedelta(days=offset)
		end = start + timedelta(days=6)
		return Period(preset, start, end, start - timedelta(days=7), start - timedelta(days=1))
	if preset in ("this_month", "last_month"):
		base = today if preset == "this_month" else getdate(add_months(today, -1))
		start, end = getdate(get_first_day(base)), getdate(get_last_day(base))
		prev = getdate(add_months(start, -1))
		return Period(preset, start, end, prev, getdate(get_last_day(prev)))
	if preset == "this_quarter":
		q_month = 3 * ((today.month - 1) // 3) + 1
		start = date(today.year, q_month, 1)
		end = getdate(get_last_day(add_months(start, 2)))
		prev = getdate(add_months(start, -3))
		return Period(preset, start, end, prev, start - timedelta(days=1))
	if preset == "this_year":
		start, end = date(today.year, 1, 1), date(today.year, 12, 31)
		return Period(preset, start, end, date(today.year - 1, 1, 1), date(today.year - 1, 12, 31))

	start, end = parse_date(from_date, "From date"), parse_date(to_date, "To date")
	if not start or not end:
		frappe.throw(_("Choose both a start and an end date."))
	if end < start:
		frappe.throw(_("The end date must be on or after the start date."))
	if (end - start).days > MAX_RANGE_DAYS:
		frappe.throw(_("Choose a range of five years or less."))
	length = (end - start).days + 1
	return Period(preset, start, end, start - timedelta(days=length), start - timedelta(days=1))
