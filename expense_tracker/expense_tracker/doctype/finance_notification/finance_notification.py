# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from expense_tracker.services.ownership import assign_user


class FinanceNotification(Document):
	def before_validate(self):
		assign_user(self)


def on_doctype_update():
	import frappe

	frappe.db.add_index("Finance Notification", ["user", "is_read"], "user_read_index")
