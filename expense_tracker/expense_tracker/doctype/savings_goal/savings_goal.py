# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from expense_tracker.services import cache
from expense_tracker.services.money import D, validate_amount
from expense_tracker.services.ownership import assign_user, get_owned
from expense_tracker.services.transactions import clean_text, validate_style


class SavingsGoal(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.goal_name = clean_text(self.goal_name, 100)
		validate_style(self)
		self.target_amount = validate_amount(self.target_amount, "Target amount")
		if self.linked_account:
			get_owned("Finance Account", self.linked_account, self.user, label=_("Account"))
		if self.target_date and self.start_date and getdate(self.target_date) < getdate(self.start_date):
			frappe.throw(_("Target date must be after the start date."))
		total = D(0)
		for row in self.contributions:
			row.amount = validate_amount(row.amount)
			if row.source_account:
				get_owned("Finance Account", row.source_account, self.user, label=_("Account"))
			total += row.amount if row.kind == "Contribution" else -row.amount
		if total < 0:
			frappe.throw(_("Withdrawals cannot exceed the amount saved."))
		self.current_amount = total
		if self.status != "Archived":
			self.status = "Achieved" if total >= D(self.target_amount) else "Active"

	def on_update(self):
		cache.bump(self.user)

	def after_delete(self):
		cache.bump(self.user)
