# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from expense_tracker.services import budgets, cache
from expense_tracker.services.money import validate_amount
from expense_tracker.services.ownership import assign_user, get_owned
from expense_tracker.services.transactions import clean_text


class FinanceBudget(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.budget_name = clean_text(self.budget_name, 100)
		self.amount = validate_amount(self.amount, "Budget amount")
		if self.category:
			cat = get_owned("Finance Category", self.category, self.user, ("category_type",), _("Category"))
			if cat.category_type != "Expense":
				frappe.throw(_("Budgets can only be set on expense categories."))
		if self.period_type == "Custom":
			if not self.end_date or getdate(self.end_date) < getdate(self.start_date):
				frappe.throw(_("End date must be on or after the start date."))
			self.carry_forward = 0
		else:
			self.end_date = None
		if self.is_active and self.period_type == "Monthly":
			clash = frappe.db.get_value(
				"Finance Budget",
				{
					"user": self.user,
					"category": self.category or ("is", "not set"),
					"period_type": "Monthly",
					"is_active": 1,
					"name": ("!=", self.name or ""),
				},
				"budget_name",
			)
			if clash:
				frappe.throw(_("An active monthly budget already exists for this category: {0}.").format(
					frappe.bold(clash)))

	def on_update(self):
		cache.bump(self.user)
		budgets.evaluate_alerts_safely(self.user)

	def after_delete(self):
		cache.bump(self.user)
