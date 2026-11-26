"""Receipts, CSV export and CSV import."""

import csv
import io
from decimal import Decimal

import frappe
from frappe.utils import nowdate

from expense_tracker.api import io as io_api
from expense_tracker.services import csv_io, receipts
from expense_tracker.tests.utils import ExpenseTestCase

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
def _pdf() -> bytes:
	"""A real one-page PDF (Frappe validates uploaded PDFs with pypdf)."""
	from pypdf import PdfWriter

	w = PdfWriter()
	w.add_blank_page(width=200, height=200)
	buf = io.BytesIO()
	w.write(buf)
	return buf.getvalue()


PDF = _pdf()


class Base(ExpenseTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.make_user()
		frappe.set_user(self.user)
		self.bank = self.account("HDFC Savings", opening=10000)
		self.card = self.account("ICICI Card", "Credit Card")
		self.food = self.category("Food & Dining")
		self.snacks = self.category("Snacks", parent_category=self.food.name)
		self.salary = self.category("Salary", "Income")


class TestReceipts(Base):
	def test_attach_image_and_pdf(self):
		t = self.txn("Expense", 100, self.bank, self.food)
		a = receipts.attach(self.user, t.name, "lunch.png", PNG)
		b = receipts.attach(self.user, t.name, "../../bill.pdf", PDF)
		self.assertEqual((a["mime_type"], b["mime_type"]), ("image/png", "application/pdf"))
		self.assertEqual(b["file_name"], "bill.pdf")  # path parts stripped
		self.assertTrue(a["file_url"].startswith("/private/files/"))
		self.assertEqual(a["ocr_status"], "Not Processed")  # no extractor installed: nothing invented
		self.assertEqual(frappe.db.get_value("Finance Transaction", t.name, "has_attachments"), 1)
		self.assertEqual(len(receipts.list_for(self.user, t.name)), 2)

	def test_rejects_disguised_and_oversized_files(self):
		t = self.txn("Expense", 100, self.bank, self.food)
		for name, content in (("evil.png", b"<html><script>alert(1)</script>"), ("x.pdf", b"MZ\x90\x00binary"), ("e.png", b"")):
			with self.assertRaises(frappe.ValidationError, msg=name):
				receipts.attach(self.user, t.name, name, content)
		with self.assertRaises(frappe.ValidationError):
			receipts.attach(self.user, t.name, "big.png", PNG + b"\x00" * receipts.MAX_BYTES)

	def test_isolation(self):
		t = self.txn("Expense", 100, self.bank, self.food)
		a = receipts.attach(self.user, t.name, "r.png", PNG)
		file_name = frappe.db.get_value("Transaction Attachment", a["name"], "file")
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		with self.assertRaises(frappe.DoesNotExistError):
			receipts.attach(other, t.name, "r.png", PNG)
		with self.assertRaises(frappe.DoesNotExistError):
			receipts.list_for(other, t.name)
		self.assertFalse(frappe.get_doc("File", file_name).has_permission("read"))

	def test_deleting_transaction_removes_receipts_and_files(self):
		t = self.txn("Expense", 100, self.bank, self.food)
		a = receipts.attach(self.user, t.name, "r.png", PNG)
		file_name = frappe.db.get_value("Transaction Attachment", a["name"], "file")
		frappe.delete_doc("Finance Transaction", t.name)
		self.assertFalse(frappe.db.exists("Transaction Attachment", a["name"]))
		self.assertFalse(frappe.db.exists("File", file_name))

	def test_removing_last_receipt_clears_flag(self):
		t = self.txn("Expense", 100, self.bank, self.food)
		a = receipts.attach(self.user, t.name, "r.png", PNG)
		frappe.delete_doc("Transaction Attachment", a["name"])
		self.assertEqual(frappe.db.get_value("Finance Transaction", t.name, "has_attachments"), 0)


class TestExport(Base):
	def test_export_rows_and_escaping(self):
		self.txn("Expense", 250.5, self.bank, self.snacks, title="=HYPERLINK(\"http://x\")", transaction_date="2026-03-02")
		self.txn("Income", 50000, self.bank, self.salary, transaction_date="2026-03-01")
		self.txn("Transfer", 1000, self.bank, to_account=self.card, transaction_date="2026-03-03")
		_, content = csv_io.export(self.user, {})
		self.assertTrue(content.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM for Excel
		rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
		self.assertEqual(rows[0], csv_io.EXPORT_COLUMNS)
		self.assertEqual([r[0] for r in rows[1:]], ["2026-03-01", "2026-03-02", "2026-03-03"])
		snack = rows[2]
		self.assertEqual((snack[2], snack[3], snack[4]), ("250.50", "Food & Dining", "Snacks"))
		self.assertTrue(snack[7].startswith("'="))  # formula neutralised
		self.assertEqual((rows[3][5], rows[3][6]), ("HDFC Savings", "ICICI Card"))

	def test_export_respects_filters_and_isolation(self):
		self.txn("Expense", 10, self.bank, self.food)
		self.txn("Income", 20, self.bank, self.salary)
		_, content = csv_io.export(self.user, {"type": "Income"})
		self.assertEqual(len(content.decode("utf-8-sig").strip().splitlines()), 2)
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		_, content = csv_io.export(other, {})
		self.assertEqual(len(content.decode("utf-8-sig").strip().splitlines()), 1)  # header only

	def test_api_returns_download(self):
		io_api.export_csv()
		self.assertEqual(frappe.response["type"], "download")
		self.assertTrue(frappe.response["filename"].endswith(".csv"))


class TestImport(Base):
	def test_parsers(self):
		self.assertEqual(csv_io.parse_amount("₹1,23,456.50"), Decimal("123456.50"))
		self.assertEqual(csv_io.parse_amount("(250.00)"), Decimal("-250.00"))
		self.assertEqual(csv_io.parse_amount("Rs. 99"), Decimal("99"))
		self.assertEqual(csv_io.parse_amount("1,200.00 Dr"), Decimal("-1200.00"))
		self.assertIsNone(csv_io.parse_amount("abc"))
		self.assertEqual(str(csv_io.parse_date("05/03/2026")), "2026-03-05")  # day first (India)
		self.assertEqual(str(csv_io.parse_date("5 Mar 2026")), "2026-03-05")
		self.assertEqual(str(csv_io.parse_date("2026-03-05")), "2026-03-05")
		self.assertIsNone(csv_io.parse_date("13/13/2026"))

	def test_round_trip_with_own_export(self):
		self.txn("Expense", 250.5, self.bank, self.snacks, title="Chips", transaction_date="2026-03-02")
		self.txn("Transfer", 1000, self.bank, to_account=self.card, transaction_date="2026-03-03")
		_, content = csv_io.export(self.user, {})
		text = content.decode("utf-8-sig")
		frappe.db.delete("Finance Transaction", {"user": self.user})
		res = csv_io.commit(self.user, text, {})
		self.assertEqual((res["imported"], res["failed"]), (2, 0))
		chips = frappe.get_all("Finance Transaction", {"user": self.user, "title": "Chips"}, ["category", "source"])[0]
		self.assertEqual((chips.category, chips.source), (self.snacks.name, "Import"))

	def test_bank_statement_format(self):
		text = (
			"Txn Date,Narration,Withdrawal Amt,Deposit Amt\n"
			"01/03/2026,SALARY MAR,,\"85,000.00\"\n"
			"02/03/2026,SWIGGY ORDER,450.00,\n"
		)
		prev = csv_io.analyse(self.user, text, {"default_account": self.bank.name})
		self.assertEqual(prev["summary"]["error"], 0, prev["rows"])
		self.assertEqual([(r["transaction_type"], r["amount"]) for r in prev["rows"]], [("Income", 85000.0), ("Expense", 450.0)])
		self.assertEqual(prev["columns"]["title"], "Narration")

	def test_errors_are_reported_per_row(self):
		text = "Date,Amount,Category,Account\n2026-13-45,100,Food & Dining,HDFC Savings\n2026-03-01,abc,Food & Dining,HDFC Savings\n2026-03-01,100,Nope,HDFC Savings\n2026-03-01,100,Food & Dining,Ghost\n2026-03-01,-100,Food & Dining,HDFC Savings\n"
		rows = csv_io.analyse(self.user, text, {})["rows"]
		self.assertEqual([r["status"] for r in rows], ["error", "error", "error", "error", "ok"])
		self.assertIn("Category 'Nope' not found", rows[2]["errors"][0])
		self.assertEqual(rows[4]["transaction_type"], "Expense")  # negative amount = expense

	def test_missing_header_is_explained(self):
		with self.assertRaises(frappe.ValidationError):
			csv_io.analyse(self.user, "Foo,Bar\n1,2\n", {})

	def test_create_missing_categories(self):
		text = "Date,Amount,Category,Subcategory,Account\n2026-03-01,100,Pets,Vet,HDFC Savings\n2026-03-02,50,Pets,Vet,HDFC Savings\n"
		res = csv_io.commit(self.user, text, {"create_missing_categories": 1})
		self.assertEqual(res["imported"], 2)
		vet = frappe.get_all("Finance Category", {"user": self.user, "category_name": "Vet"}, ["parent_category"])
		self.assertEqual(len(vet), 1)  # created once, reused
		self.assertEqual(frappe.db.get_value("Finance Category", vet[0].parent_category, "category_name"), "Pets")

	def test_reimporting_same_file_is_idempotent(self):
		text = "Date,Amount,Category,Account\n2026-03-01,100,Food & Dining,HDFC Savings\n2026-03-01,100,Food & Dining,HDFC Savings\n"
		first = csv_io.commit(self.user, text, {"include_duplicates": 1})
		self.assertEqual(first["imported"], 2)  # two real coffees on the same day are both kept
		again = csv_io.commit(self.user, text, {"include_duplicates": 1})
		self.assertEqual(again["imported"], 0)
		self.assertEqual({r["status"] for r in again["rows"]}, {"imported"})
		self.assertEqual(frappe.db.count("Finance Transaction", {"user": self.user}), 2)
		self.assertEqual(self.balance(self.bank), 9800)

	def test_possible_duplicates_skipped_by_default(self):
		self.txn("Expense", 100, self.bank, self.food, transaction_date="2026-03-01")
		text = "Date,Amount,Category,Account\n2026-03-01,100,Food & Dining,HDFC Savings\n"
		self.assertEqual(csv_io.analyse(self.user, text, {})["rows"][0]["status"], "duplicate")
		self.assertEqual(csv_io.commit(self.user, text, {})["imported"], 0)
		self.assertEqual(csv_io.commit(self.user, text, {"include_duplicates": 1})["imported"], 1)

	def test_cannot_import_into_other_users_accounts(self):
		frappe.set_user("Administrator")
		other = self.make_user()
		frappe.set_user(other)
		text = "Date,Amount,Category,Account\n2026-03-01,100,Food & Dining,HDFC Savings\n"
		self.assertEqual(csv_io.analyse(other, text, {})["rows"][0]["status"], "error")  # not their account
		with self.assertRaises(frappe.ValidationError):
			csv_io.analyse(other, text, {"default_account": self.bank.name})

	def test_limits(self):
		big = "Date,Amount\n" + "2026-03-01,1\n" * (csv_io.MAX_ROWS + 1)
		with self.assertRaises(frappe.ValidationError):
			csv_io.analyse(self.user, big, {"default_account": self.bank.name})


def fake_extractor(file_doc):
	return {"merchant": "Test Cafe", "total": "420.00", "date": "2026-03-02"}


def broken_extractor(file_doc):
	raise RuntimeError("model unavailable")


class TestExtractorHook(Base):
	"""The OCR extension point: suggestions are stored, never applied."""

	def _patched(self, paths):
		from unittest.mock import patch

		real = frappe.get_hooks

		def get_hooks(name=None, *a, **kw):
			if name == "expense_tracker_receipt_extractors":
				return paths
			return real(name, *a, **kw)

		return patch("frappe.get_hooks", side_effect=get_hooks)

	def test_extractor_result_is_a_suggestion_only(self):
		t = self.txn("Expense", 100, self.bank, self.food, title="Original")
		with self._patched(["expense_tracker.tests.test_phase7.fake_extractor"]), \
			__import__("unittest.mock").mock.patch("frappe.enqueue") as enqueue:
			a = receipts.attach(self.user, t.name, "r.png", PNG)
			self.assertEqual(frappe.db.get_value("Transaction Attachment", a["name"], "ocr_status"), "Queued")
			enqueue.assert_called_once()
			receipts.extract(a["name"])
		att = frappe.get_doc("Transaction Attachment", a["name"])
		self.assertEqual(att.ocr_status, "Done")
		self.assertEqual(frappe.parse_json(att.extracted_data)["merchant"], "Test Cafe")
		t.reload()
		self.assertEqual((t.title, float(t.amount)), ("Original", 100.0))  # nothing applied automatically

	def test_failing_extractor_is_marked_failed_and_logged(self):
		from unittest.mock import patch

		t = self.txn("Expense", 100, self.bank, self.food)
		with self._patched(["expense_tracker.tests.test_phase7.broken_extractor"]), patch("frappe.enqueue"), \
			patch("frappe.log_error") as log_error:
			a = receipts.attach(self.user, t.name, "r.png", PNG)
			receipts.extract(a["name"])
		self.assertEqual(frappe.db.get_value("Transaction Attachment", a["name"], "ocr_status"), "Failed")
		log_error.assert_called_once()

	def test_no_extractor_means_nothing_queued(self):
		from unittest.mock import patch

		t = self.txn("Expense", 100, self.bank, self.food)
		with self._patched([]), patch("frappe.enqueue") as enqueue:
			receipts.attach(self.user, t.name, "r.png", PNG)
		enqueue.assert_not_called()
