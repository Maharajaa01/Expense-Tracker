# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from expense_tracker.services import cache, ledger
from expense_tracker.services.money import D, validate_amount
from expense_tracker.services.ownership import assign_user
from expense_tracker.services.transactions import clean_text, validate_style


class FinanceAccount(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.account_name = clean_text(self.account_name, 100)
		if not self.account_name:
			frappe.throw(_("Account name is required."), frappe.MandatoryError)
		validate_style(self)
		self.account_last4 = (self.account_last4 or "").strip() or None
		if self.account_last4 and not (len(self.account_last4) == 4 and self.account_last4.isdigit()):
			frappe.throw(_("Enter exactly the last 4 digits of the account number."))
		# Opening balance may be negative (e.g. a credit card that already has dues).
		self.opening_balance = D(self.opening_balance)
		if self.account_type == "Credit Card":
			self.credit_limit = validate_amount(self.credit_limit or 0, "Credit limit", allow_zero=True)
		else:
			self.credit_limit = 0
		self._validate_unique_name()
		if self.is_new():
			self.current_balance = self.opening_balance

	def on_update(self):
		before = self.get_doc_before_save()
		if not before or D(before.opening_balance) != D(self.opening_balance):
			ledger.recompute_account_balance(self.name)
		cache.bump(self.user)

	def on_trash(self):
		used = frappe.db.sql(
			"select name from `tabFinance Transaction` where account = %(a)s or to_account = %(a)s limit 1",
			{"a": self.name},
		)
		if used:
			frappe.throw(
				_("This account has transactions. Archive it instead of deleting so your history stays correct.")
			)
		for doctype, field in (("Recurring Transaction", "account"), ("Recurring Transaction", "to_account"),
		                       ("Savings Goal", "linked_account")):
			if frappe.db.exists(doctype, {field: self.name}):
				frappe.throw(_("This account is used by a {0}. Remove it there first.").format(_(doctype)))
		for field in ("default_account", "last_used_account"):
			frappe.db.sql(
				f"update `tabExpense Profile` set `{field}` = null where `{field}` = %s", self.name
			)

	def after_delete(self):
		cache.bump(self.user)

	def _validate_unique_name(self):
		clash = frappe.db.sql(
			"""select name from `tabFinance Account`
			where user = %s and lower(account_name) = lower(%s) and is_archived = 0 and name != %s limit 1""",
			(self.user, self.account_name, self.name or ""),
		)
		if clash and not self.is_archived:
			frappe.throw(_("You already have an account named {0}.").format(frappe.bold(self.account_name)))
