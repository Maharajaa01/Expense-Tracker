# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from expense_tracker.services import cache
from expense_tracker.services.ownership import assign_user, get_owned
from expense_tracker.services.transactions import clean_text, validate_style


class FinanceCategory(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.category_name = clean_text(self.category_name, 100)
		if not self.category_name:
			frappe.throw(_("Category name is required."), frappe.MandatoryError)
		validate_style(self)
		self._validate_parent()
		self._validate_type_change()
		self._validate_unique_name()

	def on_update(self):
		cache.bump(self.user)

	def on_trash(self):
		for doctype in ("Finance Transaction", "Finance Budget", "Recurring Transaction"):
			if frappe.db.exists(doctype, {"category": self.name}):
				frappe.throw(_("This category is in use. Archive it instead of deleting."))
		if frappe.db.exists("Finance Category", {"parent_category": self.name}):
			frappe.throw(_("Delete or move its subcategories first."))

	def _validate_parent(self):
		if not self.parent_category:
			return
		if self.parent_category == self.name:
			frappe.throw(_("A category cannot be its own parent."))
		parent = get_owned(
			"Finance Category", self.parent_category, self.user,
			("category_type", "parent_category"), _("Parent category"),
		)
		if parent.parent_category:
			frappe.throw(_("Subcategories can only be one level deep."))
		if parent.category_type != self.category_type:
			frappe.throw(_("A subcategory must have the same type as its parent."))
		if not self.is_new() and frappe.db.exists("Finance Category", {"parent_category": self.name}):
			frappe.throw(_("This category has subcategories, so it cannot become a subcategory."))

	def _validate_type_change(self):
		before = self.get_doc_before_save()
		if before and before.category_type != self.category_type:
			if frappe.db.exists("Finance Transaction", {"category": self.name}):
				frappe.throw(_("Cannot change the type of a category that already has transactions."))

	def _validate_unique_name(self):
		clash = frappe.db.sql(
			"""select name from `tabFinance Category`
			where user = %s and category_type = %s and lower(category_name) = lower(%s)
			and ifnull(parent_category, '') = %s and is_archived = 0 and name != %s limit 1""",
			(self.user, self.category_type, self.category_name, self.parent_category or "", self.name or ""),
		)
		if clash and not self.is_archived:
			frappe.throw(_("Category {0} already exists.").format(frappe.bold(self.category_name)))

