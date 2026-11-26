"""Budgets, recurring transactions, savings goals, insights and analytics."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_months, get_first_day, nowdate

from expense_tracker.api import analytics as analytics_api
from expense_tracker.api import budgets as budgets_api
from expense_tracker.api import goals as goals_api
from expense_tracker.api import notifications as notifications_api
from expense_tracker.api import recurring as recurring_api
from expense_tracker.services import budgets, insights, recurring
from expense_tracker.services.money import format_inr
from expense_tracker.tests.utils import ExpenseTestCase


class Base(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("Bank", opening=100000)
		self.food = self.category("Food & Dining")
		self.snacks = self.category("Snacks", parent_category=self.food.name)
		self.shopping = self.category("Shopping")
		self.salary = self.category("Salary", "Income")

	def budget(self, amount=1000, category=None, **kw):
		return budgets_api.create({"budget_name": kw.pop("budget_name", "Food"), "amount": amount,
		                           "category": getattr(category, "name", category),
		                           "start_date": kw.pop("start_date", str(get_first_day(nowdate()))), **kw})["data"]


class TestBudgets(Base):
	def test_progress_includes_subcategories_and_refunds(self):
		b = self.budget(1000, self.food)
		self.txn("Expense", 300, self.bank, self.food)
		self.txn("Expense", 200, self.bank, self.snacks)
		self.txn("Expense", 100, self.bank, self.food, is_refund=1)
		self.txn("Expense", 999, self.bank, self.shopping)  # other category
		p = budgets_api.list()["data"][0]["progress"]
		self.assertEqual((p["spent"], p["remaining"], p["percent"], p["level"]), (400, 600, 40.0, "ok"))

	def test_overall_budget_counts_all_spending(self):
		self.budget(1000, budget_name="Everything")
		self.txn("Expense", 300, self.bank, self.food)
		self.txn("Expense", 900, self.bank, self.shopping)
		self.txn("Income", 5000, self.bank, self.salary)
		p = budgets_api.list()["data"][0]["progress"]
		self.assertEqual((p["spent"], p["remaining"], p["level"]), (1200, -200, "over"))

	def test_one_active_monthly_budget_per_category(self):
		self.budget(1000, self.food)
		with self.assertRaises(frappe.ValidationError):
			self.budget(500, self.food, budget_name="Food again")

	def test_income_category_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.budget(500, self.salary)

	def test_carry_forward(self):
		this_month = get_first_day(nowdate())
		last_month = add_months(this_month, -1)
		b = self.budget(1000, self.food, carry_forward=1, start_date=str(last_month))
		self.txn("Expense", 700, self.bank, self.food, transaction_date=str(last_month))
		p = budgets_api.list()["data"][0]["progress"]
		self.assertEqual((p["carried"], p["available"]), (300, 1300))

	def test_overspend_does_not_carry_negative(self):
		this_month = get_first_day(nowdate())
		last_month = add_months(this_month, -1)
		self.budget(1000, self.food, carry_forward=1, start_date=str(last_month))
		self.txn("Expense", 1500, self.bank, self.food, transaction_date=str(last_month))
		self.assertEqual(budgets_api.list()["data"][0]["progress"]["carried"], 0)

	def test_custom_period(self):
		start = str(add_days(nowdate(), -5))
		end = str(add_days(nowdate(), 5))
		self.budget(2000, self.shopping, budget_name="Trip", period_type="Custom", start_date=start, end_date=end)
		self.txn("Expense", 500, self.bank, self.shopping, transaction_date=str(add_days(nowdate(), -10)))  # before
		self.txn("Expense", 800, self.bank, self.shopping)
		self.assertEqual(budgets_api.list()["data"][0]["progress"]["spent"], 800)

	def test_alerts_fire_once_per_threshold(self):
		self.budget(1000, self.food)
		self.txn("Expense", 550, self.bank, self.food)
		self.txn("Expense", 10, self.bank, self.food)  # still 56 %: no new alert
		self.txn("Expense", 300, self.bank, self.food)  # 86 %
		self.txn("Expense", 200, self.bank, self.food)  # 106 %: 100 % and over
		notes = frappe.get_all("Finance Notification", {"user": self.user, "notification_type": "Budget"},
		                       pluck="dedup_key")
		levels = sorted(k.rsplit(":", 1)[1] for k in notes)
		self.assertEqual(levels, ["100", "50", "80", "over"])
		self.assertEqual(budgets.evaluate_alerts(self.user), 0)  # nothing new
		listed = notifications_api.list()["data"]
		# 50 % and 80 % were each shown when crossed; 100 % was passed in the same save as "over",
		# so only "over" is shown for that step (100 % is kept silently for de-duplication).
		titles = [n["title"] for n in listed]
		self.assertEqual(len(titles), 3, titles)
		over = next(n for n in listed if "over budget" in n["title"])
		self.assertIn("₹60 over", over["message"])

	def test_budget_with_alerts_can_be_deleted(self):
		b = self.budget(100, self.food)
		self.txn("Expense", 150, self.bank, self.food)
		self.assertTrue(frappe.db.exists("Finance Notification", {"reference_name": b["name"]}))
		budgets_api.delete(b["name"])
		self.assertFalse(frappe.db.exists("Finance Budget", b["name"]))

	def test_history(self):
		b = self.budget(1000, self.food, start_date=str(add_months(get_first_day(nowdate()), -2)))
		self.txn("Expense", 400, self.bank, self.food, transaction_date=str(add_months(nowdate(), -1)))
		h = budgets_api.history(b["name"], 3)["data"]["history"]
		self.assertEqual([x["spent"] for x in h], [0, 400, 0])


class TestRecurring(Base):
	def rec(self, **kw):
		data = {"title": "Rent", "transaction_type": "Expense", "amount": 15000, "account": self.bank.name,
		        "category": self.food.name, "frequency": "Monthly", "start_date": nowdate(), **kw}
		return recurring_api.create(data)["data"]

	def test_post_due_is_idempotent(self):
		r = self.rec()
		self.assertEqual(r["next_run_date"], nowdate())
		frappe.set_user("Administrator")
		self.assertEqual(recurring.process_template(frappe._dict(name=r["name"])), 1)
		self.assertEqual(recurring.process_template(frappe._dict(name=r["name"])), 0)  # second run
		# Even if next_run_date were wound back, the same occurrence can't post twice.
		frappe.db.set_value("Recurring Transaction", r["name"], "next_run_date", nowdate())
		recurring.process_template(frappe._dict(name=r["name"]))
		n = frappe.db.count("Finance Transaction", {"recurring_transaction": r["name"]})
		self.assertEqual(n, 1)
		row = frappe.db.get_value("Recurring Transaction", r["name"], ["next_run_date", "occurrences_posted"], as_dict=True)
		self.assertEqual(str(row.next_run_date), str(add_months(nowdate(), 1)))
		self.assertEqual(self.balance(self.bank), 85000)

	def test_catch_up_missed_runs_is_capped(self):
		r = self.rec(frequency="Daily")
		start = add_days(nowdate(), -20)
		frappe.db.set_value("Recurring Transaction", r["name"], {"start_date": start, "next_run_date": start})
		frappe.set_user("Administrator")
		posted = recurring.process_template(frappe._dict(name=r["name"]))
		self.assertEqual(posted, recurring.MAX_CATCH_UP)

	def test_month_end_schedule(self):
		r = self.rec(start_date="2026-01-31")
		frappe.db.set_value("Recurring Transaction", r["name"], "next_run_date", "2026-01-31")
		frappe.set_user("Administrator")
		recurring.process_template(frappe._dict(name=r["name"]), today="2026-03-31")
		dates = sorted(str(d) for d in frappe.get_all("Finance Transaction", {"recurring_transaction": r["name"]}, pluck="transaction_date"))
		self.assertEqual(dates, ["2026-01-31", "2026-02-28", "2026-03-31"])

	def test_end_date_finishes_schedule(self):
		r = self.rec(frequency="Daily", end_date=nowdate())
		frappe.set_user("Administrator")
		recurring.process_template(frappe._dict(name=r["name"]))
		row = frappe.db.get_value("Recurring Transaction", r["name"], ["is_active", "next_run_date"], as_dict=True)
		self.assertEqual((row.is_active, row.next_run_date), (0, None))

	def test_failure_creates_notification_not_silence(self):
		r = self.rec()
		self.bank.reload()
		self.bank.is_archived = 1
		self.bank.save()
		frappe.set_user("Administrator")
		# Error Log rows outlive the test rollback, so assert the call instead of writing one.
		with patch("frappe.log_error") as log_error:
			self.assertEqual(recurring.process_template(frappe._dict(name=r["name"])), 0)
		log_error.assert_called_once()
		self.assertTrue(frappe.db.exists("Finance Notification", {"user": self.user, "dedup_key": f"recur-fail:{r['name']}:{nowdate()}"}))
		self.assertEqual(str(frappe.db.get_value("Recurring Transaction", r["name"], "next_run_date")), nowdate())

	def test_manual_mark_paid_and_skip(self):
		r = self.rec(auto_post=0, start_date=str(add_days(nowdate(), 2)), remind_days_before=3)
		frappe.set_user("Administrator")
		self.assertEqual(recurring.send_reminders(), 1)
		self.assertEqual(recurring.send_reminders(), 0)  # deduplicated
		frappe.set_user(self.user)
		res = recurring_api.post_now(r["name"])["data"]
		self.assertEqual(res["transaction"]["source"], "Recurring")
		skipped = recurring_api.skip_next(r["name"])["data"]
		self.assertEqual(skipped["next_run_date"], str(add_months(add_days(nowdate(), 2), 2)))

	def test_upcoming(self):
		self.rec(title="Netflix", amount=649, frequency="Weekly", start_date=str(add_days(nowdate(), 1)))
		up = recurring_api.upcoming(14)["data"]
		self.assertEqual(len(up), 2)
		self.assertEqual(up[0]["title"], "Netflix")

	def test_delete_keeps_posted_history(self):
		r = self.rec()
		frappe.set_user("Administrator")
		recurring.process_template(frappe._dict(name=r["name"]))
		frappe.set_user(self.user)
		recurring_api.delete(r["name"])
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user, "source": "Recurring"}), 1)


class TestGoals(Base):
	def test_linked_goal_moves_money(self):
		vault = self.account("Savings vault", "Savings Account")
		g = goals_api.create({"goal_name": "Bike", "target_amount": 60000, "linked_account": vault.name})["data"]
		g = goals_api.contribute(g["name"], 10000, source_account=self.bank.name)["data"]
		self.assertEqual((g["current_amount"], g["remaining"], g["percent"]), (10000, 50000, 16.7))
		self.assertEqual((self.balance(self.bank), self.balance(vault)), (90000, 10000))
		g = goals_api.contribute(g["name"], 2000, kind="Withdrawal", source_account=self.bank.name)["data"]
		self.assertEqual((self.balance(self.bank), self.balance(vault)), (92000, 8000))
		# Goal transfers are not spending or income.
		self.assertEqual(analytics_api.summary("this_month")["data"]["totals"]["expense"], 0)

	def test_goal_transfer_cannot_be_deleted_directly(self):
		vault = self.account("Vault", "Savings Account")
		g = goals_api.create({"goal_name": "Trip", "target_amount": 5000, "linked_account": vault.name})["data"]
		g = goals_api.contribute(g["name"], 1000, source_account=self.bank.name)["data"]
		txn = g["contributions"][0]["transaction"]
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Finance Transaction", txn)
		g = goals_api.remove_contribution(g["name"], g["contributions"][0]["name"])["data"]
		self.assertFalse(frappe.db.exists("Finance Transaction", txn))
		self.assertEqual((g["current_amount"], self.balance(self.bank)), (0, 100000))

	def test_unlinked_goal_is_earmark_only(self):
		g = goals_api.create({"goal_name": "Emergency fund", "target_amount": 3000})["data"]
		g = goals_api.contribute(g["name"], 3000)["data"]
		self.assertEqual((g["status"], self.balance(self.bank)), ("Achieved", 100000))

	def test_withdraw_more_than_saved(self):
		g = goals_api.create({"goal_name": "Laptop", "target_amount": 80000})["data"]
		goals_api.contribute(g["name"], 1000)
		with self.assertRaises(frappe.ValidationError):
			goals_api.contribute(g["name"], 2000, kind="Withdrawal")

	def test_monthly_needed(self):
		g = goals_api.create({"goal_name": "Phone", "target_amount": 12000, "target_date": str(add_months(nowdate(), 6))})["data"]
		self.assertTrue(1900 <= g["monthly_needed"] <= 2100)


class TestInsightsAndAnalytics(Base):
	def test_format_inr(self):
		self.assertEqual(format_inr(1234567.5), "₹12,34,567.50")
		self.assertEqual(format_inr(2500), "₹2,500")
		self.assertEqual(format_inr(-999), "−₹999")

	def test_insight_rules(self):
		cur = [{"category": "f", "category_name": "Food", "icon": "utensils", "amount": 1180, "share": 59.0}]
		prev = [{"category": "f", "category_name": "Food", "icon": "utensils", "amount": 1000, "share": 50.0}]
		out = insights.generate({"income": 8000, "expense": 2000}, {"income": 8000, "expense": 4500}, cur, prev)
		texts = " ".join(i["text"] for i in out)
		self.assertIn("largest expense category is Food", texts)
		self.assertIn("spent ₹2,500 less than last month", texts)
		self.assertIn("food spending increased by 18%", texts)
		self.assertIn("saved 75% of your income", texts)

	def test_no_insights_from_noise(self):
		cur = [{"category": "f", "category_name": "Food", "icon": "utensils", "amount": 100, "share": 100.0}]
		prev = [{"category": "f", "category_name": "Food", "icon": "utensils", "amount": 20, "share": 100.0}]
		out = insights.generate({"income": 0, "expense": 100}, {"income": 0, "expense": 20}, cur, prev)
		kinds = {i["kind"] for i in out}
		self.assertNotIn("category_change", kinds)  # ₹20 base is below the threshold
		self.assertNotIn("savings", kinds)          # no income, no rate

	def test_no_data_no_insights(self):
		data = analytics_api.summary("this_month")["data"]
		self.assertEqual(data["insights"], [])
		self.assertEqual(data["totals"]["expense"], 0)

	def test_analytics_summary(self):
		self.txn("Income", 50000, self.bank, self.salary)
		self.txn("Expense", 1200, self.bank, self.food)
		self.budget(1000, self.food)
		d = analytics_api.summary("this_month")["data"]
		self.assertEqual(len(d["monthly"]), 12)
		self.assertEqual(d["savings"][-1]["savings"], 48800)
		self.assertEqual(d["comparison"][0]["current"], 1200)
		self.assertEqual(d["budgets"][0]["progress"]["level"], "over")
		self.assertTrue(any(i["kind"] == "budgets_over" for i in d["insights"]))
		for preset in ("today", "this_week", "this_quarter", "this_year"):
			analytics_api.summary(preset)


class TestPhase5Isolation(Base):
	def test_other_user_cannot_touch_phase5_records(self):
		b = self.budget(1000, self.food)
		g = goals_api.create({"goal_name": "Mine", "target_amount": 100})["data"]
		r = recurring_api.create({"title": "Gym", "transaction_type": "Expense", "amount": 1000, "account": self.bank.name,
		                          "category": self.food.name, "frequency": "Monthly", "start_date": nowdate()})["data"]
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		self.assertEqual(budgets_api.list()["data"], [])
		self.assertEqual(goals_api.list()["data"], [])
		self.assertEqual(recurring_api.list()["data"], [])
		for fn, args in ((budgets_api.update, (b["name"], {"amount": 1})), (goals_api.contribute, (g["name"], 5)),
		                 (recurring_api.post_now, (r["name"],)), (recurring_api.delete, (r["name"],)),
		                 (goals_api.delete, (g["name"],))):
			with self.assertRaises(frappe.PermissionError, msg=fn.__name__):
				fn(*args)
		with self.assertRaises(frappe.DoesNotExistError):
			recurring_api.create({"title": "x", "transaction_type": "Expense", "amount": 1, "account": self.bank.name,
			                      "category": self.food.name, "frequency": "Monthly", "start_date": nowdate()})
