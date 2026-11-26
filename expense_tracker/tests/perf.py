"""Performance check with a large history. Not part of the normal test suite.

    bench --site <site> execute expense_tracker.tests.perf.run --kwargs "{'n': 50000}"

Seeds ``n`` transactions for a throwaway user inside one DB transaction,
times the heavy read paths, prints EXPLAIN for the key queries, then rolls
everything back (nothing is committed).
"""

import random
import time
import uuid
from datetime import date, timedelta

import frappe

from expense_tracker.services import analytics, csv_io, ledger, periods, queries


def _t(label, fn, repeat=3):
	best = None
	for _ in range(repeat):
		s = time.perf_counter()
		out = fn()
		ms = (time.perf_counter() - s) * 1000
		best = ms if best is None else min(best, ms)
	print(f"  {label:<46} {best:8.1f} ms")
	return out


def run(n: int = 50000):
	frappe.db.rollback()
	real_commit = frappe.db.commit
	frappe.db.commit = lambda *a, **k: None  # never persist anything
	try:
		from expense_tracker.setup.provision import ensure_user_setup

		user = f"et.perf.{frappe.generate_hash(length=6)}@example.com"
		frappe.get_doc({"doctype": "User", "email": user, "first_name": "Perf", "user_type": "Website User",
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
		ensure_user_setup(user)
		accounts = frappe.get_all("Finance Account", {"user": user}, pluck="name")
		for nm in ("Bank", "Card", "Wallet"):
			accounts.append(frappe.get_doc({"doctype": "Finance Account", "user": user, "account_name": nm,
			                                "account_type": "Savings Account"}).insert(ignore_permissions=True).name)
		exp = frappe.get_all("Finance Category", {"user": user, "category_type": "Expense"}, pluck="name")
		inc = frappe.get_all("Finance Category", {"user": user, "category_type": "Income"}, pluck="name")

		print(f"Seeding {n} transactions for {user} (rolled back at the end)…")
		rnd = random.Random(42)
		today = date.today()
		now = frappe.utils.now()
		rows = []
		s = time.perf_counter()
		for i in range(n):
			r = rnd.random()
			ttype = "Income" if r < 0.05 else "Transfer" if r < 0.10 else "Expense"
			acc = rnd.choice(accounts)
			rows.append((
				f"PERF-{uuid.uuid4().hex[:12]}", now, now, user, user, user, ttype,
				today - timedelta(days=rnd.randint(0, 1095)),
				round(rnd.uniform(10, 5000) if ttype != "Income" else rnd.uniform(20000, 90000), 2),
				0, f"Perf {ttype} {i}", acc,
				rnd.choice([a for a in accounts if a != acc]) if ttype == "Transfer" else None,
				None if ttype == "Transfer" else rnd.choice(exp if ttype == "Expense" else inc),
				f"perf-{i}", "Import",
			))
		fields = ["name", "creation", "modified", "owner", "modified_by", "user", "transaction_type", "transaction_date",
		          "amount", "is_refund", "title", "account", "to_account", "category", "client_txn_id", "source"]
		frappe.db.bulk_insert("Finance Transaction", fields, rows, chunk_size=5000)
		print(f"  seeded in {time.perf_counter() - s:.1f} s")

		print("Timings (best of 3):")
		_t("transactions.list page 1 (no filters)", lambda: queries.list_transactions(user, {}, 1, 50))
		_t("transactions.list page 100 (offset 4,950)", lambda: queries.list_transactions(user, {}, 100, 50))
		_t("transactions.list filter: category + year", lambda: queries.list_transactions(
			user, {"category": exp[0], "from_date": str(today - timedelta(days=365)), "to_date": str(today)}, 1, 50))
		_t("transactions.list filter: account", lambda: queries.list_transactions(user, {"account": accounts[1]}, 1, 50))
		_t("transactions.list search 'Expense 4'", lambda: queries.list_transactions(user, {"q": "Expense 4"}, 1, 50))
		_t("transactions.list search amount '1,234.50'", lambda: queries.list_transactions(user, {"q": "1,234.50"}, 1, 50))
		p_month = periods.resolve("this_month")
		p_year = periods.resolve("this_year")
		_t("dashboard summary (this month)", lambda: analytics.dashboard_summary(user, p_month))
		_t("analytics summary (this year)", lambda: analytics.analytics_summary(user, p_year))
		_t("analytics summary (custom 3 years)", lambda: analytics.analytics_summary(
			user, periods.resolve("custom", str(today - timedelta(days=1095)), str(today))))
		_t("recompute one account balance (≈12k rows)", lambda: ledger.recompute_account_balance(accounts[1]))
		_t("CSV export (all 50k)", lambda: csv_io.export(user, {}), repeat=1)
		_t("insert 1 transaction (validate + ledger)", lambda: frappe.get_doc({
			"doctype": "Finance Transaction", "user": user, "transaction_type": "Expense", "amount": 99,
			"account": accounts[1], "category": exp[0], "transaction_date": str(today),
		}).insert(ignore_permissions=True))

		print("List query breakdown (page 1, no filters):")
		conds, vals = queries.build_filters(user, {})
		where = " where " + " and ".join(conds)
		_t("  rows (join + order + limit 51)", lambda: frappe.db.sql(queries._ROW_SELECT + where + " order by t.transaction_date desc, t.creation desc limit 51", vals))
		_t("  count + income/expense sums (all rows)", lambda: frappe.db.sql(
			f"select count(*), sum({queries.INCOME_SQL}), sum({queries.NET_EXPENSE_SQL})" + queries._JOINS + where, vals))
		for row in frappe.db.sql("explain " + queries._ROW_SELECT + where + " order by t.transaction_date desc, t.creation desc limit 51", vals, as_dict=True):
			print(f"    plan: table={row.table} type={row.type} key={row.key} rows≈{row.rows} extra={row.Extra}")
		print("Query plans:")
		for label, sql, vals in (
			("list page", "select name from `tabFinance Transaction` t where t.user=%s order by t.transaction_date desc, t.creation desc limit 51", (user,)),
			("month totals", "select sum(amount) from `tabFinance Transaction` t where t.user=%s and t.transaction_date between %s and %s",
			 (user, p_month.start, p_month.end)),
			("balance part 1", "select sum(amount) from `tabFinance Transaction` where account=%s", (accounts[1],)),
			("balance part 2", "select sum(amount) from `tabFinance Transaction` where to_account=%s and transaction_type='Transfer'", (accounts[1],)),
		):
			plan = frappe.db.sql("explain " + sql, vals, as_dict=True)
			print(f"  {label:<14} " + "; ".join(f"type={p.type} key={p.key} rows≈{p.rows}" for p in plan))
	finally:
		frappe.db.rollback()
		frappe.db.commit = real_commit
		print("Rolled back. Nothing was saved.")
