# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

from frappe import _
from frappe.model.document import Document

from expense_tracker.services.ownership import assign_user, get_owned


class ExpenseProfile(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.currency = "INR"  # single-currency v1 (docs/ACCOUNTING.md)
		for field in ("default_account", "last_used_account"):
			if self.get(field):
				get_owned("Finance Account", self.get(field), self.user, label=_("Account"))
