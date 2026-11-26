# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe import _
from frappe.model.document import Document

from expense_tracker.services import budgets, cache, ledger
from expense_tracker.services.ownership import assign_user
from expense_tracker.services.transactions import clean_text, validate_date, validate_entry


class FinanceTransaction(Document):
	"""One ledger entry. Balances are recomputed server-side; see docs/ACCOUNTING.md."""

	def before_validate(self):
		assign_user(self)
		if not self.client_txn_id:
			self.client_txn_id = str(uuid.uuid4())

	def validate(self):
		validate_entry(self, check_archived=self._accounts_changed())
		validate_date(self.transaction_date)
		self.title = clean_text(self.title, 140) or self._default_title()
		self.notes = clean_text(self.notes, 2000)
		self._validate_client_id_unique()
		# Choosing a category for an auto-created entry takes it off the "To categorise" list.
		before = self.get_doc_before_save()
		if self.needs_review and before and before.category != self.category:
			self.needs_review = 0
		# Lock every affected account (old and new) before the row is written.
		ledger.lock_accounts(self._affected_accounts())

	def on_update(self):
		ledger.recompute_many(self._affected_accounts())
		cache.bump(self.user)
		# Bulk imports evaluate alerts once at the end instead of per row.
		if self._touches_spending() and not frappe.flags.expense_tracker_bulk:
			budgets.evaluate_alerts_safely(self.user)

	def on_trash(self):
		if self.savings_goal and not frappe.flags.expense_tracker_goal_delete:
			frappe.throw(
				_("This transfer belongs to savings goal {0}. Remove the contribution from the goal instead.").format(
					frappe.bold(self.savings_goal)
				)
			)
		ledger.lock_accounts(self._affected_accounts())
		for att in frappe.get_all("Transaction Attachment", {"transaction": self.name}, pluck="name"):
			frappe.delete_doc("Transaction Attachment", att, ignore_permissions=True)

	def after_delete(self):
		ledger.recompute_many([self.account, self.to_account])
		cache.bump(self.user)

	# helpers -----------------------------------------------------------------

	def _touches_spending(self) -> bool:
		before = self.get_doc_before_save()
		return self.transaction_type == "Expense" or bool(before and before.transaction_type == "Expense")

	def _affected_accounts(self) -> set:
		accounts = {self.account, self.to_account}
		before = self.get_doc_before_save()
		if before:
			accounts |= {before.account, before.to_account}
		return {a for a in accounts if a}

	def _accounts_changed(self) -> bool:
		"""Archived accounts can't receive new entries, but old entries stay editable."""
		before = self.get_doc_before_save()
		if self.is_new() or not before:
			return True
		return (before.account, before.to_account) != (self.account, self.to_account)

	def _default_title(self) -> str:
		if self.transaction_type == "Transfer":
			return _("Transfer")
		return frappe.db.get_value("Finance Category", self.category, "category_name") or self.transaction_type

	def _validate_client_id_unique(self):
		existing = frappe.db.get_value(
			"Finance Transaction", {"user": self.user, "client_txn_id": self.client_txn_id}, "name"
		)
		if existing and existing != self.name:
			frappe.throw(_("This transaction was already recorded."), frappe.DuplicateEntryError)


def on_doctype_update():
	frappe.db.add_unique("Finance Transaction", ["user", "client_txn_id"], "unique_user_client_txn")
	# Serves both date-range filters and the list's "newest first" order without a filesort.
	frappe.db.add_index("Finance Transaction", ["user", "transaction_date", "creation"], "user_date_creation_index")
	# account / to_account are indexed via search_index in the JSON.
	frappe.db.add_index("Finance Transaction", ["user", "category", "transaction_date"], "user_category_date_index")
	frappe.db.add_index("Finance Transaction", ["user", "merchant_key"], "user_merchant_index")
