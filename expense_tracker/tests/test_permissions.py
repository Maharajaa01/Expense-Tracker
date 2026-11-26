"""Data isolation: one user can never read or modify another user's records."""

import frappe

from expense_tracker.tests.utils import ExpenseTestCase


class TestIsolation(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.alice = self.make_user("et.alice")
		self.bob = self.make_user("et.bob")
		frappe.set_user(self.alice)
		self.a_bank = self.account("Alice Bank", opening=1000)
		self.a_food = self.category("Food & Dining")
		self.a_txn = self.txn("Expense", 100, self.a_bank, self.a_food)
		frappe.set_user(self.bob)
		self.b_food = self.category("Food & Dining")

	def test_list_queries_are_scoped(self):
		for doctype in ("Finance Account", "Finance Category", "Finance Transaction", "Expense Profile"):
			users = set(frappe.get_list(doctype, pluck="user", limit_page_length=0))
			self.assertTrue(users <= {self.bob}, doctype)
			self.assertNotIn(self.alice, users, doctype)
		# Bob's own rows are visible.
		self.assertIn(self.bob, set(frappe.get_list("Finance Account", pluck="user")))

	def test_cannot_read_foreign_doc(self):
		doc = frappe.get_doc("Finance Transaction", self.a_txn.name)
		self.assertFalse(doc.has_permission("read"))
		with self.assertRaises(frappe.PermissionError):
			doc.check_permission("read")
		self.assertFalse(frappe.has_permission("Finance Account", "read", self.a_bank.name))

	def test_cannot_modify_or_delete_foreign_doc(self):
		doc = frappe.get_doc("Finance Transaction", self.a_txn.name)
		doc.amount = 1
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Finance Transaction", self.a_txn.name)

	def test_cannot_post_against_foreign_account(self):
		with self.assertRaises(frappe.DoesNotExistError):
			self.txn("Expense", 5, self.a_bank.name, self.b_food)
		frappe.set_user("Administrator")
		self.assertEqual(self.balance(self.a_bank), 900)

	def test_cannot_use_foreign_category(self):
		b_bank = self.account("Bob Bank")
		with self.assertRaises(frappe.DoesNotExistError):
			self.txn("Expense", 5, b_bank, self.a_food.name)

	def test_cannot_create_records_for_another_user(self):
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{"doctype": "Finance Account", "account_name": "Sneaky", "account_type": "Cash",
				 "user": self.alice}
			).insert()

	def test_foreign_parent_category_rejected(self):
		with self.assertRaises(frappe.DoesNotExistError):
			self.category("Snacks", parent_category=self.a_food.name)

	def test_system_manager_is_not_exempt(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.bob).add_roles("System Manager")
		frappe.set_user(self.bob)
		self.assertNotIn(self.alice, set(frappe.get_list("Finance Transaction", pluck="user")))

	def test_administrator_can_see_all(self):
		frappe.set_user("Administrator")
		users = set(frappe.get_all("Finance Transaction", pluck="user", filters={"user": ("in", [self.alice])}))
		self.assertEqual(users, {self.alice})
		self.assertTrue(frappe.has_permission("Finance Transaction", "read", self.a_txn.name))
