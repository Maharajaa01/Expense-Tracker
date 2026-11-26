"""Shared fixtures for Expense Tracker tests.

Every test runs inside a DB transaction that is rolled back in ``tearDown``,
so tests are safe on a shared site. Users get random ``@example.com`` emails.
"""

import unittest

import frappe

from expense_tracker.setup.provision import ensure_user_setup


class ExpenseTestCase(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		frappe.local.flags.commit = False

	# fixtures -----------------------------------------------------------------

	def make_user(self, prefix="et.test") -> str:
		email = f"{prefix}.{frappe.generate_hash(length=8)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Test",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("Expense User")
		ensure_user_setup(email)
		return email

	def account(self, name="Bank", account_type="Savings Account", opening=0, **kw):
		return frappe.get_doc(
			{"doctype": "Finance Account", "account_name": name, "account_type": account_type,
			 "opening_balance": opening, **kw}
		).insert()

	def category(self, name, ctype="Expense", **kw):
		existing = frappe.db.get_value(
			"Finance Category",
			{"user": frappe.session.user, "category_name": name, "category_type": ctype},
			"name",
		)
		if existing:
			return frappe.get_doc("Finance Category", existing)
		return frappe.get_doc(
			{"doctype": "Finance Category", "category_name": name, "category_type": ctype, **kw}
		).insert()

	def txn(self, ttype, amount, account, category=None, to_account=None, **kw):
		return frappe.get_doc(
			{
				"doctype": "Finance Transaction",
				"transaction_type": ttype,
				"amount": amount,
				"account": getattr(account, "name", account),
				"to_account": getattr(to_account, "name", to_account),
				"category": getattr(category, "name", category),
				"transaction_date": kw.pop("transaction_date", frappe.utils.nowdate()),
				**kw,
			}
		).insert()

	def balance(self, account):
		from expense_tracker.services.money import D

		return D(frappe.db.get_value("Finance Account", getattr(account, "name", account), "current_balance"))
