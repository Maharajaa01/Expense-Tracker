"""Offline sync: idempotency, conflicts, isolation and partial failure."""

import frappe
from frappe.utils import nowdate

from expense_tracker.api import sync as sync_api
from expense_tracker.api import transactions as txn_api
from expense_tracker.pwa import manifest
from expense_tracker.tests.utils import ExpenseTestCase


class TestSync(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("Bank", opening=1000)
		self.food = self.category("Food & Dining")

	def create_op(self, cid, amount=100, **data):
		return {"op": "create", "client_txn_id": cid, "data": {
			"transaction_type": "Expense", "amount": amount, "account": self.bank.name, "category": self.food.name,
			"transaction_date": nowdate(), **data}}

	def push(self, *ops):
		return sync_api.push(list(ops), device_id="phone-1")["data"]

	def test_create_is_idempotent_across_replays(self):
		first = self.push(self.create_op("off-1"), self.create_op("off-2", 50))
		self.assertEqual([r["status"] for r in first], ["applied", "applied"])
		replay = self.push(self.create_op("off-1"), self.create_op("off-2", 50))
		self.assertEqual([r["status"] for r in replay], ["duplicate", "duplicate"])
		self.assertEqual(replay[0]["transaction"]["name"], first[0]["transaction"]["name"])
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 2)
		self.assertEqual(self.balance(self.bank), 850)
		self.assertEqual(frappe.db.get_value("Finance Transaction", first[0]["transaction"]["name"], "source"), "Sync")

	def test_online_create_then_offline_replay_is_duplicate(self):
		txn_api.create(self.create_op("same-id")["data"], "same-id")
		self.assertEqual(self.push(self.create_op("same-id"))[0]["status"], "duplicate")

	def test_bad_op_does_not_block_others(self):
		res = self.push(self.create_op("ok-1"), self.create_op("bad-1", amount=-5), self.create_op("ok-2"),
		                {"op": "explode", "client_txn_id": "x"})
		self.assertEqual([r["status"] for r in res], ["applied", "rejected", "applied", "rejected"])
		self.assertIn("greater than zero", res[1]["message"])
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 2)

	def test_update_conflict_and_force(self):
		t = self.push(self.create_op("c-1"))[0]["transaction"]
		txn_api.update(t["name"], {"amount": 120})  # edited on another device
		res = self.push({"op": "update", "client_txn_id": "c-1:e1", "name": t["name"], "expected_modified": t["modified"],
		                 "data": {"amount": 90}})[0]
		self.assertEqual((res["status"], res["reason"], res["transaction"]["amount"]), ("conflict", "changed", 120))
		forced = self.push({"op": "update", "client_txn_id": "c-1:e2", "name": t["name"], "force": True,
		                    "expected_modified": t["modified"], "data": {"amount": 90}})[0]
		self.assertEqual((forced["status"], forced["transaction"]["amount"]), ("applied", 90))

	def test_update_of_deleted_record_is_conflict(self):
		t = self.push(self.create_op("d-1"))[0]["transaction"]
		txn_api.delete(t["name"])
		res = self.push({"op": "update", "client_txn_id": "d-1:e", "name": t["name"], "data": {"amount": 5}})[0]
		self.assertEqual((res["status"], res["reason"]), ("conflict", "deleted"))

	def test_delete_is_idempotent(self):
		t = self.push(self.create_op("del-1"))[0]["transaction"]
		op = {"op": "delete", "client_txn_id": "del-1:x", "name": t["name"]}
		self.assertEqual(self.push(op)[0]["status"], "applied")
		self.assertEqual(self.push(op)[0]["status"], "applied")
		self.assertEqual(self.balance(self.bank), 1000)

	def test_cannot_touch_other_users_records(self):
		t = self.push(self.create_op("iso-1"))[0]["transaction"]
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		res = self.push({"op": "update", "client_txn_id": "iso-1:e", "name": t["name"], "data": {"amount": 1}},
		                {"op": "delete", "client_txn_id": "iso-1:d", "name": t["name"]})
		self.assertEqual(res[0]["status"], "conflict")  # looks deleted: existence isn't revealed
		self.assertEqual(res[1]["status"], "applied")   # no-op for this user
		self.assertTrue(frappe.db.exists("Finance Transaction", t["name"]))
		# Same client id from another user is a different transaction, not a duplicate.
		other_bank = self.account("Other bank")
		other_food = self.category("Food & Dining")
		op = self.create_op("iso-1")
		op["data"].update(account=other_bank.name, category=other_food.name)
		self.assertEqual(self.push(op)[0]["status"], "applied")
		# And one user's offline op cannot use another user's account.
		bad = self.create_op("iso-2")
		self.assertEqual(self.push(bad)[0]["status"], "rejected")

	def test_ops_are_logged(self):
		self.push(self.create_op("log-1"), self.create_op("log-bad", amount=0))
		logs = {r.client_txn_id: r.status for r in frappe.get_all("Offline Sync Log", {"user": self.user}, ["client_txn_id", "status"])}
		self.assertEqual(logs, {"log-1": "Applied", "log-bad": "Failed"})

	def test_batch_limits(self):
		with self.assertRaises(frappe.ValidationError):
			sync_api.push([self.create_op(f"b{i}") for i in range(51)])
		with self.assertRaises(frappe.ValidationError):
			sync_api.push({"not": "a list"})

	def test_manifest(self):
		m = manifest()
		self.assertEqual((m["scope"], m["start_url"], m["display"]), ("/expense", "/expense", "standalone"))
		self.assertTrue(any(i["purpose"] == "maskable" for i in m["icons"]))
