"""Balance and accounting-rule tests (docs/ACCOUNTING.md)."""

from decimal import Decimal

import frappe

from expense_tracker.services import ledger
from expense_tracker.tests.utils import ExpenseTestCase


class TestLedger(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("Bank", opening=10000)
		self.food = self.category("Food & Dining")
		self.salary = self.category("Salary", "Income")

	def test_starter_setup(self):
		self.assertEqual(frappe.db.count("Finance Category", {"user": self.user, "category_type": "Expense"}), 16)
		self.assertEqual(frappe.db.count("Finance Category", {"user": self.user, "category_type": "Income"}), 7)
		self.assertTrue(frappe.db.exists("Expense Profile", self.user))
		self.assertIn("Expense User", frappe.get_roles(self.user))  # assigned by the test fixture, not the app

	def test_opening_balance(self):
		self.assertEqual(self.balance(self.bank), Decimal("10000.00"))

	def test_expense_and_income(self):
		self.txn("Expense", 250.50, self.bank, self.food)
		self.txn("Income", 50000, self.bank, self.salary)
		self.assertEqual(self.balance(self.bank), Decimal("59749.50"))

	def test_transfer_moves_money_only(self):
		wallet = self.account("Wallet", "Digital Wallet")
		self.txn("Transfer", 1500, self.bank, to_account=wallet)
		self.assertEqual(self.balance(self.bank), Decimal("8500.00"))
		self.assertEqual(self.balance(wallet), Decimal("1500.00"))

	def test_credit_card_no_double_count(self):
		card = self.account("Card", "Credit Card", credit_limit=50000)
		self.txn("Expense", 3000, card, self.food)  # purchase
		self.assertEqual(self.balance(card), Decimal("-3000.00"))
		self.txn("Transfer", 3000, self.bank, to_account=card)  # bill payment
		self.assertEqual(self.balance(card), Decimal("0.00"))
		self.assertEqual(self.balance(self.bank), Decimal("7000.00"))
		spent = frappe.db.sql(
			"""select sum(amount) from `tabFinance Transaction`
			where user=%s and transaction_type='Expense' and is_refund=0""",
			self.user,
		)[0][0]
		self.assertEqual(Decimal(spent), Decimal("3000"))  # counted once

	def test_refund_increases_balance(self):
		self.txn("Expense", 1000, self.bank, self.food)
		self.txn("Expense", 400, self.bank, self.food, is_refund=1)
		self.assertEqual(self.balance(self.bank), Decimal("9400.00"))

	def test_edit_amount_and_account(self):
		wallet = self.account("Wallet", "Digital Wallet")
		t = self.txn("Expense", 100, self.bank, self.food)
		t.amount = 300
		t.save()
		self.assertEqual(self.balance(self.bank), Decimal("9700.00"))
		t.account = wallet.name
		t.save()
		self.assertEqual(self.balance(self.bank), Decimal("10000.00"))
		self.assertEqual(self.balance(wallet), Decimal("-300.00"))

	def test_change_type_expense_to_transfer(self):
		wallet = self.account("Wallet", "Digital Wallet")
		t = self.txn("Expense", 100, self.bank, self.food)
		t.transaction_type = "Transfer"
		t.to_account = wallet.name
		t.save()
		self.assertIsNone(t.category)
		self.assertEqual(self.balance(self.bank), Decimal("9900.00"))
		self.assertEqual(self.balance(wallet), Decimal("100.00"))

	def test_delete_restores_balance(self):
		t = self.txn("Expense", 999.99, self.bank, self.food)
		frappe.delete_doc("Finance Transaction", t.name)
		self.assertEqual(self.balance(self.bank), Decimal("10000.00"))

	def test_opening_balance_change_recomputes(self):
		self.txn("Expense", 100, self.bank, self.food)
		self.bank.reload()
		self.bank.opening_balance = 500
		self.bank.save()
		self.assertEqual(self.balance(self.bank), Decimal("400.00"))

	def test_decimal_precision(self):
		for _ in range(10):
			self.txn("Expense", 0.1, self.bank, self.food)
		self.txn("Income", 0.2, self.bank, self.salary)
		self.assertEqual(self.balance(self.bank), Decimal("9999.20"))

	def test_large_amounts(self):
		self.txn("Income", "999999999.99", self.bank, self.salary)
		self.assertEqual(self.balance(self.bank), Decimal("1000009999.99"))

	def test_reconcile_fixes_tampered_balance(self):
		self.txn("Expense", 100, self.bank, self.food)
		frappe.db.set_value("Finance Account", self.bank.name, "current_balance", 1)
		frappe.set_user("Administrator")
		self.assertGreaterEqual(ledger.reconcile_all(), 1)
		self.assertEqual(self.balance(self.bank), Decimal("9900.00"))


class TestTransactionValidation(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("Bank")
		self.food = self.category("Food & Dining")
		self.salary = self.category("Salary", "Income")

	def test_invalid_amounts(self):
		for bad in (0, -5, "abc", "10.005", "1e20", "NaN"):
			with self.assertRaises(frappe.ValidationError, msg=f"amount={bad!r}"):
				self.txn("Expense", bad, self.bank, self.food)

	def test_category_type_must_match(self):
		with self.assertRaises(frappe.ValidationError):
			self.txn("Expense", 10, self.bank, self.salary)
		with self.assertRaises(frappe.ValidationError):
			self.txn("Income", 10, self.bank, self.food)

	def test_transfer_rules(self):
		with self.assertRaises(frappe.ValidationError):
			self.txn("Transfer", 10, self.bank, to_account=self.bank)
		with self.assertRaises(frappe.ValidationError):
			self.txn("Transfer", 10, self.bank)
		wallet = self.account("Wallet", "Digital Wallet")
		t = self.txn("Transfer", 10, self.bank, self.food, to_account=wallet, is_refund=1)
		self.assertIsNone(t.category)
		self.assertEqual(t.is_refund, 0)

	def test_expense_requires_category(self):
		with self.assertRaises(frappe.ValidationError):
			self.txn("Expense", 10, self.bank)

	def test_archived_account_rejects_new_entries_but_keeps_history(self):
		t = self.txn("Expense", 10, self.bank, self.food)
		self.bank.reload()
		self.bank.is_archived = 1
		self.bank.save()
		with self.assertRaises(frappe.ValidationError):
			self.txn("Expense", 10, self.bank, self.food)
		t.reload()
		t.notes = "still editable"
		t.save()

	def test_client_txn_id_idempotency(self):
		self.txn("Expense", 10, self.bank, self.food, client_txn_id="abc-123")
		with self.assertRaises(frappe.DuplicateEntryError):
			self.txn("Expense", 10, self.bank, self.food, client_txn_id="abc-123")
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 1)

	def test_unrealistic_date(self):
		with self.assertRaises(frappe.ValidationError):
			self.txn("Expense", 10, self.bank, self.food, transaction_date="2206-01-01")

	def test_default_title_from_category(self):
		t = self.txn("Expense", 10, self.bank, self.food)
		self.assertEqual(t.title, "Food & Dining")

	def test_account_with_transactions_cannot_be_deleted(self):
		self.txn("Expense", 10, self.bank, self.food)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Finance Account", self.bank.name)

	def test_duplicate_account_name(self):
		with self.assertRaises(frappe.ValidationError):
			self.account("bank")
