"""Receipt attachments, plus the extension point for future OCR.

Security: only images and PDFs are accepted, verified by their leading bytes
(not the file name or the browser's content type), at most MAX_BYTES, and
always stored as private files attached to the transaction, so Frappe's file
download checks the transaction's (per-user) permission.

OCR: no extraction is performed here. Apps can register extractors with the
``expense_tracker_receipt_extractors`` hook (see docs/AI.md). Until one is
installed, attachments stay ``ocr_status = "Not Processed"`` and nothing is
ever invented.
"""

import os
import re

import frappe
from frappe import _

from expense_tracker.services.ownership import get_owned

MAX_BYTES = 10 * 1024 * 1024
MAX_PER_TRANSACTION = 10

# (mime, extension, magic-byte check)
SIGNATURES = (
	("image/jpeg", "jpg", lambda b: b[:3] == b"\xff\xd8\xff"),
	("image/png", "png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
	("image/webp", "webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
	("image/heic", "heic", lambda b: b[4:8] == b"ftyp" and b[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"hevc")),
	("application/pdf", "pdf", lambda b: b[:5] == b"%PDF-"),
)


def sniff(content: bytes) -> tuple[str, str] | None:
	for mime, ext, check in SIGNATURES:
		if check(content[:16]):
			return mime, ext
	return None


def _safe_name(name: str, ext: str) -> str:
	base = os.path.splitext(os.path.basename(name or "receipt"))[0]
	base = re.sub(r"[^\w\- ]+", "", base).strip()[:60] or "receipt"
	return f"{base}.{ext}"


def attach(user: str, transaction: str, filename: str, content: bytes) -> dict:
	get_owned("Finance Transaction", transaction, user, label=_("Transaction"))
	if not content:
		frappe.throw(_("The file is empty."))
	if len(content) > MAX_BYTES:
		frappe.throw(_("Receipts can be at most {0} MB.").format(MAX_BYTES // (1024 * 1024)))
	kind = sniff(content)
	if not kind:
		frappe.throw(_("Only photos (JPG, PNG, WebP, HEIC) and PDF files can be attached."))
	if frappe.db.count("Transaction Attachment", {"transaction": transaction}) >= MAX_PER_TRANSACTION:
		frappe.throw(_("A transaction can have at most {0} receipts.").format(MAX_PER_TRANSACTION))
	mime, ext = kind

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": _safe_name(filename, ext),
		"content": content,
		"is_private": 1,
		"attached_to_doctype": "Finance Transaction",
		"attached_to_name": transaction,
	})
	file_doc.save()
	att = frappe.get_doc({
		"doctype": "Transaction Attachment",
		"transaction": transaction,
		"file": file_doc.name,
		"mime_type": mime,
	}).insert()
	run_extractors(att)
	return serialize(att)


def serialize(att) -> dict:
	return {
		"name": att.name,
		"transaction": att.transaction,
		"file_name": att.file_name,
		"file_url": att.file_url,
		"mime_type": att.mime_type,
		"file_size": att.file_size,
		"ocr_status": att.ocr_status,
		"extracted_data": frappe.parse_json(att.extracted_data) if att.extracted_data else None,
		"creation": str(att.creation),
	}


def list_for(user: str, transaction: str) -> list[dict]:
	get_owned("Finance Transaction", transaction, user, label=_("Transaction"))
	names = frappe.get_all("Transaction Attachment", {"transaction": transaction, "user": user}, pluck="name", order_by="creation asc")
	return [serialize(frappe.get_doc("Transaction Attachment", n)) for n in names]


def run_extractors(att) -> None:
	"""Queue registered OCR extractors (none ship with this app)."""
	extractors = frappe.get_hooks("expense_tracker_receipt_extractors") or []
	if not extractors:
		return
	frappe.db.set_value("Transaction Attachment", att.name, "ocr_status", "Queued", update_modified=False)
	frappe.enqueue("expense_tracker.services.receipts.extract", attachment=att.name, queue="short", enqueue_after_commit=True)


def extract(attachment: str) -> None:
	"""Background job: run the first extractor that returns data.

	An extractor is ``fn(file_doc) -> dict | None`` returning suggestions such
	as {"merchant", "date", "total", "currency", "line_items"}. The result is
	only stored on the attachment as a suggestion; it is never applied to the
	transaction without the user confirming it.
	"""
	att = frappe.get_doc("Transaction Attachment", attachment)
	file_doc = frappe.get_doc("File", att.file)
	try:
		for path in frappe.get_hooks("expense_tracker_receipt_extractors") or []:
			data = frappe.get_attr(path)(file_doc)
			if data:
				att.db_set({"ocr_status": "Done", "extracted_data": frappe.as_json(data)})
				return
		att.db_set("ocr_status", "Failed")
	except Exception:
		att.db_set("ocr_status", "Failed")
		frappe.log_error(title=f"Expense Tracker: receipt extraction failed for {attachment}")
