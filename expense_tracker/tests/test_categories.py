import frappe

from expense_tracker.tests.utils import ExpenseTestCase


class TestCategories(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.food = self.category("Food & Dining")

	def test_subcategory(self):
		sub = self.category("Snacks", parent_category=self.food.name)
		self.assertEqual(sub.parent_category, self.food.name)

	def test_only_one_level(self):
		sub = self.category("Snacks", parent_category=self.food.name)
		with self.assertRaises(frappe.ValidationError):
			self.category("Chips", parent_category=sub.name)

	def test_parent_type_must_match(self):
		with self.assertRaises(frappe.ValidationError):
			self.category("Bonus", "Income", parent_category=self.food.name)

	def test_in_use_category_cannot_be_deleted(self):
		bank = self.account("Bank")
		self.txn("Expense", 10, bank, self.food)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Finance Category", self.food.name)

	def test_type_change_blocked_when_used(self):
		bank = self.account("Bank")
		self.txn("Expense", 10, bank, self.food)
		self.food.reload()
		self.food.category_type = "Income"
		with self.assertRaises(frappe.ValidationError):
			self.food.save()

	def test_invalid_style(self):
		with self.assertRaises(frappe.ValidationError):
			self.category("Bad", color="red")
		with self.assertRaises(frappe.ValidationError):
			self.category("Bad2", icon="<script>")
