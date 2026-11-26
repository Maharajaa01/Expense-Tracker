"""Validation rules shared by Finance Transaction and Recurring Transaction."""

import re

import frappe
from frappe import _
from frappe.utils import add_years, getdate, nowdate

from expense_tracker.services.money import validate_amount
from expense_tracker.services.ownership import get_owned

TYPES = ("Expense", "Income", "Transfer")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
ICON_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_entry(doc, check_archived: bool = True) -> None:
	"""Validate type/amount/account/category consistency for ``doc``.

	``doc`` must have: user, transaction_type, amount, account, to_account,
	category and (optionally) is_refund.
	"""
	if doc.transaction_type not in TYPES:
		frappe.throw(_("Invalid transaction type."))

	doc.amount = validate_amount(doc.amount)

	account = get_owned("Finance Account", doc.account, doc.user, ("is_archived",), _("Account"))
	if not account:
		frappe.throw(_("Please choose an account."), frappe.MandatoryError)
	if check_archived and account.is_archived:
		frappe.throw(_("Account {0} is archived.").format(frappe.bold(doc.account)))

	if doc.transaction_type == "Transfer":
		if not doc.to_account:
			frappe.throw(_("Please choose the account to transfer to."), frappe.MandatoryError)
		if doc.to_account == doc.account:
			frappe.throw(_("Cannot transfer to the same account."))
		to_acc = get_owned("Finance Account", doc.to_account, doc.user, ("is_archived",), _("Account"))
		if check_archived and to_acc.is_archived:
			frappe.throw(_("Account {0} is archived.").format(frappe.bold(doc.to_account)))
		# Transfers never carry a category and are never refunds.
		doc.category = None
		if doc.meta.has_field("is_refund"):
			doc.is_refund = 0
		return

	doc.to_account = None
	if not doc.category:
		frappe.throw(_("Please choose a category."), frappe.MandatoryError)
	category = get_owned(
		"Finance Category", doc.category, doc.user, ("category_type", "is_archived"), _("Category")
	)
	if category.category_type != doc.transaction_type:
		frappe.throw(
			_("Category {0} is an {1} category and cannot be used for {2}.").format(
				frappe.bold(doc.category), category.category_type.lower(), doc.transaction_type.lower()
			)
		)
	if doc.meta.has_field("is_refund") and doc.transaction_type != "Expense":
		doc.is_refund = 0


def validate_date(value, label: str = "Date") -> None:
	"""Reject obviously wrong dates (typos like year 2206 or 1926)."""
	d = getdate(value)
	if d.year < 1970 or d > getdate(add_years(nowdate(), 5)):
		frappe.throw(_("{0} {1} looks incorrect.").format(_(label), frappe.format(d, "Date")))


def validate_style(doc) -> None:
	"""Validate icon/color fields used by accounts, categories and goals."""
	if doc.get("color") and not HEX_COLOR.match(doc.color):
		frappe.throw(_("Colour must be a hex value like #10b981."))
	if doc.get("icon") and not ICON_SLUG.match(doc.icon):
		frappe.throw(_("Invalid icon name."))


def clean_text(value: str | None, max_len: int) -> str | None:
	if value is None:
		return None
	value = " ".join(str(value).split()) if max_len <= 140 else str(value).strip()
	return value[:max_len] or None
