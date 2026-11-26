"""Whitelisted API behaviour, called as a real user."""

from datetime import date

import frappe

from expense_tracker.api import accounts as accounts_api
from expense_tracker.api import boot as boot_api
from expense_tracker.api import categories as categories_api
from expense_tracker.api import dashboard as dashboard_api
from expense_tracker.api import transactions as txn_api
from expense_tracker.services import periods
from expense_tracker.tests.utils import ExpenseTestCase


class APITestCase(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("Bank", opening=10000)
		self.wallet = self.account("Wallet", "Digital Wallet")
		self.food = self.category("Food & Dining")
		self.snacks = self.category("Snacks", parent_category=self.food.name)
		self.fuel = self.category("Fuel")
		self.salary = self.category("Salary", "Income")

	def create(self, ttype="Expense", amount=100, category=None, account=None, **kw):
		data = {"transaction_type": ttype, "amount": amount, "account": (account or self.bank).name,
		        "transaction_date": kw.pop("transaction_date", frappe.utils.nowdate()), **kw}
		if category:
			data["category"] = category.name
		return txn_api.create(data, kw.pop("client_txn_id", None))["data"]


class TestAccess(APITestCase):
	def test_user_without_role_is_refused(self):
		frappe.set_user("Administrator")
		outsider = f"et.outsider.{frappe.generate_hash(length=6)}@example.com"
		frappe.get_doc({"doctype": "User", "email": outsider, "first_name": "Out", "user_type": "Website User",
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			boot_api.get_boot()
		with self.assertRaises(frappe.PermissionError):
			txn_api.list()
		self.assertFalse(frappe.db.exists("Expense Profile", outsider))
		self.assertNotIn("Expense User", frappe.get_roles(outsider))


class TestTransactionAPI(APITestCase):
	def test_create_is_idempotent(self):
		first = self.create(category=self.food, client_txn_id="dev1-0001")
		again = self.create(category=self.food, client_txn_id="dev1-0001", amount=999)
		self.assertFalse(first["duplicate"])
		self.assertTrue(again["duplicate"])
		self.assertEqual(again["transaction"]["name"], first["transaction"]["name"])
		self.assertEqual(again["transaction"]["amount"], 100)
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 1)

	def test_create_ignores_protected_fields(self):
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(self.user)
		res = self.create(category=self.food, user=other, source="Recurring", savings_goal="x", has_attachments=1)
		row = frappe.db.get_value("Finance Transaction", res["transaction"]["name"],
		                          ["user", "source", "savings_goal", "has_attachments"], as_dict=True)
		self.assertEqual(row.user, self.user)
		self.assertEqual(row.source, "Manual")
		self.assertIsNone(row.savings_goal)
		self.assertEqual(row.has_attachments, 0)

	def test_create_remembers_last_account(self):
		self.create(category=self.food, account=self.wallet)
		self.assertEqual(frappe.db.get_value("Expense Profile", self.user, "last_used_account"), self.wallet.name)

	def test_update_detects_conflict(self):
		t = self.create(category=self.food)["transaction"]
		txn_api.update(t["name"], {"amount": 150}, expected_modified=t["modified"])
		with self.assertRaises(frappe.TimestampMismatchError):
			txn_api.update(t["name"], {"amount": 175}, expected_modified=t["modified"])
		self.assertEqual(self.balance(self.bank), 9850)

	def test_update_and_delete(self):
		t = self.create(category=self.food)["transaction"]
		updated = txn_api.update(t["name"], {"amount": 40, "title": "Tea"})["data"]["transaction"]
		self.assertEqual((updated["amount"], updated["title"]), (40, "Tea"))
		txn_api.delete(t["name"])
		self.assertEqual(self.balance(self.bank), 10000)

	def test_cannot_touch_other_users_transaction(self):
		t = self.create(category=self.food)["transaction"]
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		with self.assertRaises(frappe.DoesNotExistError):
			txn_api.get(t["name"])
		with self.assertRaises(frappe.PermissionError):
			txn_api.update(t["name"], {"amount": 1})
		with self.assertRaises(frappe.PermissionError):
			txn_api.delete(t["name"])
		rows = txn_api.list({"account": self.bank.name})["data"]["rows"]
		self.assertEqual(rows, [])


class TestTransactionList(APITestCase):
	def setUp(self):
		super().setUp()
		self.create(category=self.food, amount=200, title="Dinner", transaction_date="2026-03-02")
		self.create(category=self.snacks, amount=50, title="Chips", transaction_date="2026-03-02")
		self.create(category=self.fuel, amount=1500, transaction_date="2026-03-05")
		self.create("Income", 50000, self.salary, title="March salary", transaction_date="2026-03-01")
		self.create("Expense", 30, self.food, is_refund=1, title="Refund", transaction_date="2026-03-03")
		self.create("Transfer", 1000, account=self.bank, to_account=self.wallet.name, transaction_date="2026-03-04")

	def rows(self, **filters):
		return txn_api.list(filters)["data"]["rows"]

	def test_filters(self):
		self.assertEqual(len(self.rows(type="Income")), 1)
		self.assertEqual(len(self.rows(account=self.wallet.name)), 1)  # incoming transfer counts
		self.assertEqual({r["title"] for r in self.rows(category=self.food.name)}, {"Dinner", "Chips", "Refund"})
		self.assertEqual(len(self.rows(category=self.snacks.name)), 1)
		self.assertEqual(len(self.rows(from_date="2026-03-03", to_date="2026-03-04")), 2)

	def test_search(self):
		self.assertEqual([r["title"] for r in self.rows(q="dinn")], ["Dinner"])
		self.assertEqual([r["amount"] for r in self.rows(q="₹1,500")], [1500])
		self.assertEqual(self.rows(q="100%_"), [])  # LIKE wildcards are escaped
		self.assertEqual(len(self.rows(q="snacks")), 1)  # category name

	def test_sort_and_pagination(self):
		res = txn_api.list({}, page=1, page_size=4, sort="amount_desc")
		self.assertEqual(res["data"]["rows"][0]["amount"], 50000)
		self.assertTrue(res["meta"]["has_more"])
		self.assertEqual(res["meta"]["total"], 6)
		page2 = txn_api.list({}, page=2, page_size=4, sort="amount_desc")
		self.assertEqual(len(page2["data"]["rows"]), 2)
		self.assertFalse(page2["meta"]["has_more"])

	def test_day_totals_cover_rows_on_other_pages(self):
		# Page size 1: only one of the two 2 March expenses is on page 1, but the day total includes both.
		res = txn_api.list({"from_date": "2026-03-02", "to_date": "2026-03-02"}, page=1, page_size=1)
		self.assertEqual(res["data"]["day_totals"]["2026-03-02"]["expense"], 250)

	def test_summary_excludes_transfers_and_nets_refunds(self):
		s = txn_api.list({})["data"]["summary"]
		self.assertEqual(s, {"income": 50000, "expense": 1720})

	def test_invalid_filters(self):
		with self.assertRaises(frappe.ValidationError):
			self.rows(type="Bogus")
		with self.assertRaises(frappe.ValidationError):
			self.rows(from_date="not-a-date")

	def test_suggested_categories(self):
		s = txn_api.suggested_categories("Expense")["data"]
		self.assertEqual(set(s["recent"]), {self.food.name, self.snacks.name, self.fuel.name})


class TestDashboard(APITestCase):
	def test_summary_figures(self):
		today = frappe.utils.nowdate()
		self.create("Income", 40000, self.salary)
		self.create(category=self.food, amount=1000)
		self.create(category=self.snacks, amount=500)
		self.create(category=self.food, amount=200, is_refund=1)
		self.create("Transfer", 3000, account=self.bank, to_account=self.wallet.name)
		d = dashboard_api.summary("this_month")["data"]
		self.assertEqual(d["totals"]["income"], 40000)
		self.assertEqual(d["totals"]["expense"], 1300)
		self.assertEqual(d["totals"]["savings"], 38700)
		self.assertEqual(d["totals"]["savings_rate"], 96.8)
		self.assertEqual(d["net_worth"]["total"], 10000 + 40000 - 1300)
		cats = {c["category_name"]: c["amount"] for c in d["categories"]}
		self.assertEqual(cats, {"Food & Dining": 1300})  # Snacks rolls up into Food
		self.assertEqual(sum(p["expense"] for p in d["trend"]["points"]), 1300)
		self.assertTrue(any(p["period"] == today for p in d["trend"]["points"]))
		self.assertEqual(len(d["monthly"]), 6)
		self.assertEqual(len(d["recent"]), 5)

	def test_no_income_means_no_savings_rate(self):
		self.create(category=self.food, amount=100)
		self.assertIsNone(dashboard_api.summary("this_month")["data"]["totals"]["savings_rate"])

	def test_cache_invalidated_by_writes(self):
		first = dashboard_api.summary("this_month")["data"]["totals"]["expense"]
		self.create(category=self.food, amount=123)
		second = dashboard_api.summary("this_month")["data"]["totals"]["expense"]
		self.assertEqual(second - first, 123)

	def test_net_worth_respects_archive_and_include_flags(self):
		accounts_api.update(self.wallet.name, {"include_in_totals": 0, "opening_balance": 500})
		self.assertEqual(dashboard_api.summary("today")["data"]["net_worth"]["total"], 10000)
		accounts_api.set_archived(self.wallet.name, 1)
		self.assertEqual(dashboard_api.summary("today")["data"]["net_worth"]["account_count"], 1 + 1)  # Bank + starter Cash


class TestAccountAndCategoryAPI(APITestCase):
	def test_credit_card_available_credit(self):
		card = accounts_api.create({"account_name": "Card", "account_type": "Credit Card", "credit_limit": 50000})["data"]
		self.create(category=self.food, amount=1200, account=frappe._dict(name=card["name"]))
		row = accounts_api.get(card["name"])["data"]
		self.assertEqual((row["balance"], row["available_credit"]), (-1200, 48800))

	def test_list_totals(self):
		card = accounts_api.create({"account_name": "Card", "account_type": "Credit Card", "credit_limit": 9000})["data"]
		self.create(category=self.food, amount=2500, account=frappe._dict(name=card["name"]))
		meta = accounts_api.list()["meta"]
		self.assertEqual((meta["assets"], meta["liabilities"], meta["net_worth"]), (10000, 2500, 7500))

	def test_account_create_ignores_balance_injection(self):
		row = accounts_api.create({"account_name": "Sneaky", "account_type": "Cash", "current_balance": 1e9})["data"]
		self.assertEqual(row["balance"], 0)

	def test_archive_parent_category_archives_children(self):
		categories_api.set_archived(self.food.name, 1)
		self.assertEqual(frappe.db.get_value("Finance Category", self.snacks.name, "is_archived"), 1)
		names = {c["name"] for c in categories_api.list()["data"]}
		self.assertNotIn(self.snacks.name, names)


class TestPeriods(ExpenseTestCase):
	def test_presets(self):
		p = periods.resolve("this_week", today="2026-11-25")  # Wednesday
		self.assertEqual((p.start, p.end), (date(2026, 11, 23), date(2026, 11, 29)))
		p = periods.resolve("this_week", week_start="Sunday", today="2026-11-25")
		self.assertEqual(p.start, date(2026, 11, 22))
		p = periods.resolve("last_month", today="2026-01-15")
		self.assertEqual((p.start, p.end, p.prev_start), (date(2025, 12, 1), date(2025, 12, 31), date(2025, 11, 1)))
		p = periods.resolve("this_month", today="2026-03-31")
		self.assertEqual((p.prev_start, p.prev_end), (date(2026, 2, 1), date(2026, 2, 28)))

	def test_custom_validation(self):
		p = periods.resolve("custom", "2026-01-01", "2026-01-10")
		self.assertEqual((p.prev_start, p.prev_end), (date(2025, 12, 22), date(2025, 12, 31)))
		for args in (("2026-01-10", "2026-01-01"), (None, "2026-01-01"), ("2010-01-01", "2026-01-01")):
			with self.assertRaises(frappe.ValidationError):
				periods.resolve("custom", *args)
