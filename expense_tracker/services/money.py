"""Decimal-safe money helpers. Never use float arithmetic for amounts."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import frappe
from frappe import _

PRECISION = 2
QUANT = Decimal("0.01")
ZERO = Decimal("0.00")
# Upper bound well inside DECIMAL(21,9) and JS Number's exact-integer range.
MAX_AMOUNT = Decimal("999999999999.99")


def D(value) -> Decimal:
	"""Convert any numeric-ish value to a Decimal rounded to 2 places.

	Floats are converted through ``str`` so ``0.1`` becomes ``Decimal('0.1')``
	rather than its binary approximation.
	"""
	if value is None or value == "":
		return ZERO
	if isinstance(value, Decimal):
		d = value
	else:
		try:
			d = Decimal(str(value).strip())
		except (InvalidOperation, ValueError):
			frappe.throw(_("Invalid amount: {0}").format(frappe.bold(value)), frappe.ValidationError)
	if not d.is_finite():
		frappe.throw(_("Invalid amount: {0}").format(frappe.bold(value)), frappe.ValidationError)
	return d.quantize(QUANT, rounding=ROUND_HALF_UP)


def validate_amount(value, label: str = "Amount", allow_zero: bool = False) -> Decimal:
	"""Validate a user-entered positive amount with at most 2 decimal places."""
	if value is None or value == "":
		frappe.throw(_("{0} is required.").format(_(label)), frappe.MandatoryError)
	try:
		raw = value if isinstance(value, Decimal) else Decimal(str(value).strip())
	except (InvalidOperation, ValueError):
		frappe.throw(_("{0} must be a number.").format(_(label)))
	if not raw.is_finite():
		frappe.throw(_("{0} must be a number.").format(_(label)))
	if raw != raw.quantize(QUANT, rounding=ROUND_HALF_UP):
		frappe.throw(_("{0} can have at most 2 decimal places.").format(_(label)))
	amount = D(raw)
	if amount < 0 or (amount == 0 and not allow_zero):
		frappe.throw(_("{0} must be greater than zero.").format(_(label)))
	if amount > MAX_AMOUNT:
		frappe.throw(_("{0} is too large.").format(_(label)))
	return amount


def to_number(value) -> float:
	"""Serialise a money value for JSON. Safe: values are ≤ 1e12 with 2 decimals."""
	return float(D(value))


def percent(part, whole) -> float | None:
	"""``part / whole * 100`` rounded to 1 place, or ``None`` if ``whole`` is 0."""
	whole = D(whole)
	if whole == 0:
		return None
	return float((D(part) / whole * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def percent_change(current, previous) -> float | None:
	"""Change from ``previous`` to ``current`` in %, or ``None`` when there is no base."""
	previous = D(previous)
	if previous == 0:
		return None
	return float(((D(current) - previous) / abs(previous) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def format_inr(value, paise: bool | None = None) -> str:
	"""Indian-grouped rupees for server-written text (insights, notifications).

	``format_inr(123456.5)`` → ``"₹1,23,456.50"``. Paise are shown only when
	non-zero unless ``paise`` is given.
	"""
	d = D(value)
	sign = "−" if d < 0 else ""
	d = abs(d)
	whole, frac = divmod(d, 1)
	digits = str(int(whole))
	if len(digits) > 3:
		head, tail = digits[:-3], digits[-3:]
		groups = []
		while len(head) > 2:
			groups.insert(0, head[-2:])
			head = head[:-2]
		if head:
			groups.insert(0, head)
		digits = ",".join([*groups, tail])
	show_paise = paise if paise is not None else frac != 0
	return f"{sign}₹{digits}" + (f".{int(frac * 100):02d}" if show_paise else "")
