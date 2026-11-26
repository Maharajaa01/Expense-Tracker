# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from expense_tracker.services.ownership import assign_user


class BankAlert(Document):
	"""One processed bank alert email: parsed fields and the outcome, never the email itself."""

	def before_validate(self):
		assign_user(self)


def on_doctype_update():
	frappe.db.add_unique("Bank Alert", ["user", "message_id"], "unique_user_message")
