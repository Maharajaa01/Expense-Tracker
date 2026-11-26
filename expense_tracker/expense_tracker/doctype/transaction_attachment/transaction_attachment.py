# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from expense_tracker.services.ownership import assign_user, get_owned


class TransactionAttachment(Document):
	"""Links an uploaded File to a transaction.

	OCR fields are reserved for a future extraction pipeline; nothing here
	reads or fabricates them.
	"""

	def before_validate(self):
		assign_user(self)

	def validate(self):
		get_owned("Finance Transaction", self.transaction, self.user, label=_("Transaction"))
		f = frappe.db.get_value(
			"File", self.file, ["owner", "file_url", "file_name", "file_size", "is_private"], as_dict=True
		)
		if not f or (f.owner != self.user and frappe.session.user != "Administrator"):
			frappe.throw(_("File not found."), frappe.DoesNotExistError)
		if not f.is_private:
			frappe.throw(_("Receipts must be stored as private files."))
		self.file_url, self.file_name, self.file_size = f.file_url, f.file_name, f.file_size

	def after_insert(self):
		frappe.db.set_value("Finance Transaction", self.transaction, "has_attachments", 1, update_modified=False)

	def after_delete(self):
		# The file goes after this row is gone (while the row exists it still links to the file).
		if self.file and frappe.db.exists("File", self.file):
			frappe.delete_doc("File", self.file, ignore_permissions=True)
		remaining = frappe.db.count("Transaction Attachment", {"transaction": self.transaction})
		if frappe.db.exists("Finance Transaction", self.transaction):
			frappe.db.set_value(
				"Finance Transaction", self.transaction, "has_attachments", int(remaining > 0),
				update_modified=False,
			)
