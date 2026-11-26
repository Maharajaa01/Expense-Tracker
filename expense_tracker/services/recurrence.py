"""Pure date maths for recurring schedules (no DB access).

Occurrences are always computed from the *anchor* (start date) rather than by
adding to the previous date, so a schedule starting on Jan 31 yields
Feb 28/29, Mar 31, Apr 30 … instead of drifting to the 28th forever.
"""

from datetime import date, timedelta

from frappe.utils import add_months, getdate

MONTHS_PER = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}
MAX_ITERATIONS = 100_000


def _step(frequency: str, interval: int, unit: str | None) -> tuple[str, int]:
	interval = max(int(interval or 1), 1)
	if frequency == "Daily":
		return "days", interval
	if frequency == "Weekly":
		return "days", 7 * interval
	if frequency in MONTHS_PER:
		return "months", MONTHS_PER[frequency] * interval
	if frequency == "Custom":
		return {"Days": ("days", interval), "Weeks": ("days", 7 * interval), "Months": ("months", interval)}[
			unit or "Days"
		]
	raise ValueError(f"Unknown frequency {frequency!r}")


def occurrence(anchor, n: int, frequency: str, interval: int = 1, unit: str | None = None) -> date:
	"""The ``n``-th occurrence (0-based) of a schedule starting at ``anchor``."""
	anchor = getdate(anchor)
	kind, size = _step(frequency, interval, unit)
	if kind == "days":
		return anchor + timedelta(days=size * n)
	return getdate(add_months(anchor, size * n))


def first_on_or_after(anchor, target, frequency, interval=1, unit=None) -> tuple[int, date]:
	"""Index and date of the first occurrence on or after ``target``."""
	anchor, target = getdate(anchor), getdate(target)
	if target <= anchor:
		return 0, anchor
	kind, size = _step(frequency, interval, unit)
	# Jump close to the target, then walk (handles month-length differences).
	if kind == "days":
		n = max((target - anchor).days // size - 1, 0)
	else:
		months = (target.year - anchor.year) * 12 + target.month - anchor.month
		n = max(months // size - 1, 0)
	for _step_i in range(MAX_ITERATIONS):
		d = occurrence(anchor, n, frequency, interval, unit)
		if d >= target:
			return n, d
		n += 1
	raise RuntimeError("Recurrence did not converge")


def occurrences_between(anchor, start, end, frequency, interval=1, unit=None, limit=1000) -> list[date]:
	"""All occurrences with ``start <= date <= end`` (capped by ``limit``)."""
	n, d = first_on_or_after(anchor, start, frequency, interval, unit)
	end = getdate(end)
	out = []
	while d <= end and len(out) < limit:
		out.append(d)
		n += 1
		d = occurrence(anchor, n, frequency, interval, unit)
	return out
