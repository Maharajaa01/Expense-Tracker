"""Bank alert emails: parsing, posting, de-duplication, learning, mailbox access."""

from datetime import date, datetime
from decimal import Decimal
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import frappe

from expense_tracker.api import alerts as alerts_api
from expense_tracker.api import transactions as txn_api
from expense_tracker.services.bank_alerts import ingest, mailbox, parser
from expense_tracker.services.bank_alerts.mailbox import Message
from expense_tracker.tests.utils import ExpenseTestCase

AXIS_DEBIT = "Dear Customer, INR 450.00 has been debited from your A/c no. XX1234 on 24-11-2026 at 10:15:30 IST towards UPI/P2M/432112345678/SWIGGY. Available balance INR 12,345.00."
AXIS_CREDIT = "Your A/c XX1234 has been credited with INR 85,000.00 on 01-11-2026 by NEFT from DREAMTECH SOLUTIONS. Ref No AXNF12345678901."
KTK_DEBIT = "Dear Customer, Rs.1,200.00 debited from A/c XXXX5678 on 23-Nov-26 to VPA bescom@ybl UPI Ref No 512398765432."
KTK_CREDIT = "Your a/c no. XXXXXXXX5678 is credited by Rs. 2,500.00 on 22/11/2026 from ravi.kumar@okaxis (UPI Ref No. 512312341234)."


class TestParser(ExpenseTestCase):
	def test_debits_and_credits(self):
		cases = [
			(AXIS_DEBIT, "debit", "450.00", "1234", "432112345678", "SWIGGY", "Axis Bank"),
			(AXIS_CREDIT, "credit", "85000.00", "1234", "AXNF12345678901", "DREAMTECH SOLUTIONS", "Axis Bank"),
			(KTK_DEBIT, "debit", "1200.00", "5678", "512398765432", "bescom@ybl", "Karnataka Bank"),
			(KTK_CREDIT, "credit", "2500.00", "5678", "512312341234", "ravi.kumar@okaxis", "Karnataka Bank"),
		]
		for body, direction, amount, last4, ref, merchant, bank in cases:
			sender = "alerts@axisbank.com" if bank == "Axis Bank" else "alerts@ktkbank.com"
			r = parser.parse(sender, "Transaction alert", body)
			self.assertIsNotNone(r, body)
			self.assertEqual((r.direction, r.amount, r.account_last4, r.reference, r.merchant, r.bank),
			                 (direction, Decimal(amount), last4, ref, merchant, bank), body)

	def test_dates_are_day_first(self):
		self.assertEqual(parser.parse("x@axisbank.com", "", AXIS_DEBIT).txn_date, date(2026, 11, 24))
		self.assertEqual(parser.parse("x@ktkbank.com", "", KTK_DEBIT).txn_date, date(2026, 11, 23))
		self.assertEqual(parser.parse("x@ktkbank.com", "", KTK_CREDIT).txn_date, date(2026, 11, 22))

	def test_non_transactions_are_ignored(self):
		for body in (
			"OTP for transaction of INR 999.00 at AMAZON is 123456. Do not share.",
			"RAVI has requested money INR 500.00 from you on UPI.",
			"Your UPI transaction of Rs.300.00 has failed.",
			"Your EMI of INR 5,000.00 will be debited on 05-12-2026 from A/c XX1234.",
			"Your credit card statement is ready. Minimum amount due INR 1,200.00.",
			"Get a pre-approved loan of Rs 5,00,000 today!",
			"Your balance in A/c XX1234 is INR 10,000.00.",
		):
			self.assertIsNone(parser.parse("alerts@axisbank.com", "", body), body)

	def test_masking(self):
		self.assertEqual(parser.mask("A/c XXXXXXXX5678 ref 512312341234"), "A/c XXXXXXXX5678 ref XXXXXXXX1234")


def msg(body, sender="alerts@axisbank.com", mid=None, subject="Transaction alert", received=None):
	return Message(uid=1, message_id=mid or f"<{frappe.generate_hash(length=10)}@mail>", sender=sender, subject=subject,
	               body=body, received=received or datetime(2026, 11, 24, 10, 0))


class TestIngest(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.axis = self.account("Axis Savings", opening=10000, account_last4="1234")
		self.ktk = self.account("Karnataka Salary", opening=0, account_last4="5678")
		self.food = self.category("Food & Dining")

	def test_debit_posts_uncategorised_and_updates_balance(self):
		r = ingest.process_message(self.user, msg(AXIS_DEBIT))
		self.assertEqual(r["status"], "Posted")
		t = frappe.get_doc("Finance Transaction", r["transaction"])
		cat = frappe.db.get_value("Finance Category", t.category, "category_name")
		self.assertEqual((t.transaction_type, float(t.amount), t.account, cat, t.needs_review, t.source),
		                 ("Expense", 450.0, self.axis.name, "Uncategorised", 1, "Bank Alert"))
		self.assertEqual((t.title, t.merchant_key, t.bank_reference, str(t.transaction_date)), ("SWIGGY", "swiggy", "432112345678", "2026-11-24"))
		self.assertEqual(self.balance(self.axis), 9550)

	def test_credit_posts_income(self):
		r = ingest.process_message(self.user, msg(KTK_CREDIT, sender="alerts@ktkbank.com"))
		t = frappe.get_doc("Finance Transaction", r["transaction"])
		self.assertEqual((t.transaction_type, t.account), ("Income", self.ktk.name))
		self.assertEqual(frappe.db.get_value("Finance Category", t.category, "category_name"), "Uncategorised income")
		self.assertEqual(self.balance(self.ktk), 2500)

	def test_same_payment_twice_is_recorded_once(self):
		self.assertEqual(ingest.process_message(self.user, msg(AXIS_DEBIT))["status"], "Posted")
		# Same alert again (e.g. a forwarded copy with a different Message-ID)
		self.assertEqual(ingest.process_message(self.user, msg(AXIS_DEBIT))["status"], "Duplicate")
		# Same email seen twice is skipped without a new log row
		m = msg(AXIS_CREDIT, mid="<same@mail>")
		ingest.process_message(self.user, m)
		self.assertEqual(ingest.process_message(self.user, m)["status"], "Seen")
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user, "source": "Bank Alert"}), 2)

	def test_unknown_account_is_not_guessed(self):
		r = ingest.process_message(self.user, msg(AXIS_DEBIT.replace("XX1234", "XX9999")))
		self.assertEqual(r["status"], "Needs Account")
		self.assertIn("9999", frappe.db.get_value("Bank Alert", r["name"], "note"))
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 0)

	def test_category_is_remembered_after_user_chooses_it(self):
		first = ingest.process_message(self.user, msg(AXIS_DEBIT))
		txn_api.update(first["transaction"], {"category": self.food.name})  # user categorises
		self.assertEqual(frappe.db.get_value("Finance Transaction", first["transaction"], "needs_review"), 0)
		second = ingest.process_message(self.user, msg(AXIS_DEBIT.replace("432112345678", "432112349999").replace("450.00", "320.00")))
		t = frappe.get_doc("Finance Transaction", second["transaction"])
		self.assertEqual((t.category, t.needs_review), (self.food.name, 0))

	def test_to_categorise_list(self):
		ingest.process_message(self.user, msg(AXIS_DEBIT))
		ingest.process_message(self.user, msg(KTK_DEBIT, sender="alerts@ktkbank.com"))
		rows = txn_api.list({"needs_review": 1})["data"]["rows"]
		self.assertEqual(len(rows), 2)
		self.assertTrue(all(r["needs_review"] for r in rows))

	def test_other_senders_and_noise_are_ignored(self):
		self.assertEqual(ingest.process_message(self.user, msg(AXIS_DEBIT, sender="promo@shop.com"))["status"], "Ignored")
		self.assertEqual(ingest.process_message(self.user, msg("Your OTP is 123456 for INR 10.00"))["status"], "Ignored")
		r = ingest.process_message(self.user, msg("Dear customer, please update your KYC details."))
		self.assertEqual(r["status"], "Unrecognised")
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 0)

	def test_future_dates_are_clamped_to_today(self):
		r = ingest.process_message(self.user, msg(AXIS_DEBIT.replace("24-11-2026", "24-11-2030")))
		self.assertEqual(str(frappe.db.get_value("Finance Transaction", r["transaction"], "transaction_date")), frappe.utils.nowdate())

	def test_account_digits_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.account("Bad", account_last4="12a4")

	def test_isolation_and_password_never_returned(self):
		alerts_api.save_settings({"email": "me.alerts@gmail.com", "app_password": "abcd efgh ijkl mnop", "enabled": 1})
		s = alerts_api.get_settings()["data"]
		self.assertTrue(s["has_password"])
		self.assertNotIn("abcd", frappe.as_json(s))
		self.assertEqual(s["since"], frappe.utils.nowdate())  # no surprise import of old mail
		r = ingest.process_message(self.user, msg(AXIS_DEBIT))
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		self.assertEqual(alerts_api.log()["data"], [])
		self.assertFalse(alerts_api.get_settings()["data"]["has_password"])
		self.assertFalse(frappe.has_permission("Finance Transaction", "read", r["transaction"]))


class FakeIMAP:
	"""Minimal stand-in for imaplib.IMAP4_SSL."""

	def __init__(self, messages, fail_login=False):
		self.messages = messages  # {uid: bytes}
		self.fail_login = fail_login
		self.calls = []

	def login(self, user, pw):
		self.calls.append(("login", user, pw))
		if self.fail_login:
			import imaplib

			raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")
		return "OK", []

	def select(self, box, readonly=False):
		self.calls.append(("select", box, readonly))
		return "OK", [b"1"]

	def response(self, code):
		return code, [b"777"]

	def uid(self, cmd, *args):
		self.calls.append(("uid", cmd, *args))
		if cmd == "search":
			crit = args[-1]
			uids = sorted(self.messages)
			if crit.startswith("UID"):
				lo = int(crit.split()[1].split(":")[0])
				uids = [u for u in uids if u >= lo]
			return "OK", [" ".join(map(str, uids)).encode()]
		uid = int(args[0])
		return "OK", [(f"{uid} (BODY[] ".encode(), self.messages[uid]), b")"]

	def logout(self):
		self.calls.append(("logout",))


def raw_email(body, mid, sender="alerts@axisbank.com"):
	m = EmailMessage()
	m["From"], m["Subject"], m["Message-ID"], m["Date"] = f"Axis Bank <{sender}>", "Debit alert", mid, "Tue, 24 Nov 2026 10:15:00 +0530"
	m.set_content(body)
	return m.as_bytes()


class TestMailbox(ExpenseTestCase):
	def test_reads_read_only_without_marking_and_resumes(self):
		fake = FakeIMAP({5: raw_email(AXIS_DEBIT, "<a@x>"), 6: raw_email(AXIS_CREDIT, "<b@x>")})
		with patch("imaplib.IMAP4_SSL", return_value=fake):
			msgs, last, validity = mailbox.fetch_new("me@gmail.com", "abcd efgh", 0, None, date(2026, 11, 1))
		self.assertEqual(([m.message_id for m in msgs], last, validity), (["a@x", "b@x"], 6, "777"))
		self.assertIn(("select", "INBOX", True), fake.calls)  # read-only
		self.assertIn(("login", "me@gmail.com", "abcdefgh"), fake.calls)  # spaces from Google's display removed
		fetches = [c for c in fake.calls if c[:2] == ("uid", "fetch")]
		self.assertTrue(fetches and all(c[-1] == "(BODY.PEEK[])" for c in fetches))  # never marks as read
		self.assertIn("SINCE 01-Nov-2026", [c[-1] for c in fake.calls if c[:2] == ("uid", "search")])

		fake2 = FakeIMAP({5: raw_email(AXIS_DEBIT, "<a@x>"), 6: raw_email(AXIS_CREDIT, "<b@x>"), 7: raw_email(KTK_DEBIT, "<c@x>")})
		with patch("imaplib.IMAP4_SSL", return_value=fake2):
			msgs, last, _ = mailbox.fetch_new("me@gmail.com", "pw", 6, "777", None)
		self.assertEqual(([m.message_id for m in msgs], last), (["c@x"], 7))

	def test_bad_password_gives_a_clear_error(self):
		with patch("imaplib.IMAP4_SSL", return_value=FakeIMAP({}, fail_login=True)):
			with self.assertRaises(mailbox.MailboxError) as ctx:
				mailbox.fetch_new("me@gmail.com", "wrong", 0, None, None)
		self.assertIn("App Password", str(ctx.exception))

	def test_check_user_end_to_end_with_fake_mailbox(self):
		user = self.make_user()
		frappe.set_user(user)
		acc = self.account("Axis Savings", opening=1000, account_last4="1234")
		alerts_api.save_settings({"email": "me.alerts@gmail.com", "app_password": "pw", "enabled": 1})
		fake = FakeIMAP({1: raw_email(AXIS_DEBIT, "<1@x>"), 2: raw_email("Your OTP is 1234 for INR 5.00", "<2@x>")})
		with patch("imaplib.IMAP4_SSL", return_value=fake):
			res = alerts_api.check_now()["data"]
		self.assertEqual((res["checked"], res["results"]["Posted"], res["results"]["Ignored"]), (2, 1, 1))
		self.assertEqual(self.balance(acc), 550)
		self.assertEqual(frappe.db.get_value("Expense Profile", user, "alerts_last_uid"), 2)
		with patch("imaplib.IMAP4_SSL", return_value=FakeIMAP({}, fail_login=True)), patch("frappe.log_error"):
			res = alerts_api.check_now()["data"]
		self.assertFalse(res["ok"])
		self.assertTrue(frappe.db.exists("Finance Notification", {"user": user, "title": "Couldn't read your bank alert emails"}))
