"""CSV export and two-step import (preview, then commit).

Import is stateless: the client sends the file text to ``preview`` (nothing is
written) and again to ``commit``. Each row gets the client transaction ID
``imp:<file hash>:<row number>``, so importing the same file twice never
creates duplicates. Rows that look like existing transactions are flagged as
"possible duplicate" and skipped unless the user includes them.
"""

import csv
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _

from expense_tracker.services import budgets, cache
from expense_tracker.services.money import D, MAX_AMOUNT
from expense_tracker.services.queries import build_filters

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
EXPORT_COLUMNS = ["Date", "Type", "Amount", "Category", "Subcategory", "Account", "To Account", "Description", "Notes", "Refund"]

HEADERS = {
	"date": ("date", "transaction date", "txn date", "value date", "posting date"),
	"type": ("type", "transaction type", "txn type"),
	"amount": ("amount", "value", "amount (inr)", "amount(inr)", "inr"),
	"debit": ("debit", "withdrawal", "withdrawal amt", "withdrawal amount", "dr", "debit amount"),
	"credit": ("credit", "deposit", "deposit amt", "deposit amount", "cr", "credit amount"),
	"drcr": ("dr/cr", "cr/dr", "debit/credit"),
	"category": ("category",),
	"subcategory": ("subcategory", "sub category", "sub-category"),
	"account": ("account", "from account", "paid from"),
	"to_account": ("to account", "transfer to"),
	"title": ("description", "title", "narration", "particulars", "details", "remarks", "merchant", "payee"),
	"notes": ("notes", "note", "memo", "comment"),
	"refund": ("refund", "is refund"),
}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d-%b-%Y",
                "%d %B %Y", "%d-%b-%y", "%d %b %y")
TYPES = {"expense": "Expense", "income": "Income", "transfer": "Transfer", "debit": "Expense", "credit": "Income",
         "dr": "Expense", "cr": "Income"}


# ----- export ------------------------------------------------------------------------

def _cell(value) -> str:
	"""Neutralise spreadsheet formulas (CSV injection)."""
	s = "" if value is None else str(value)
	return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def export(user: str, filters: dict) -> tuple[str, bytes]:
	conds, vals = build_filters(user, filters)
	rows = frappe.db.sql(
		f"""select t.transaction_date, t.transaction_type, t.amount, t.is_refund, t.title, t.notes,
			a.account_name, ta.account_name as to_account_name,
			c.category_name, c.parent_category, pc.category_name as parent_name
		from `tabFinance Transaction` t
		join `tabFinance Account` a on a.name = t.account
		left join `tabFinance Account` ta on ta.name = t.to_account
		left join `tabFinance Category` c on c.name = t.category
		left join `tabFinance Category` pc on pc.name = c.parent_category
		where {" and ".join(conds)}
		order by t.transaction_date asc, t.creation asc""",
		vals, as_dict=True,
	)
	buf = io.StringIO()
	w = csv.writer(buf)
	w.writerow(EXPORT_COLUMNS)
	for r in rows:
		category, sub = (r.parent_name, r.category_name) if r.parent_category else (r.category_name, "")
		w.writerow([
			str(r.transaction_date), r.transaction_type, f"{D(r.amount):.2f}", _cell(category), _cell(sub),
			_cell(r.account_name), _cell(r.to_account_name), _cell(r.title), _cell(r.notes), "Yes" if r.is_refund else "",
		])
	name = f"transactions-{frappe.utils.nowdate()}.csv"
	# BOM so Excel opens UTF-8 (₹, names in Indian scripts) correctly.
	return name, buf.getvalue().encode("utf-8-sig")


# ----- import ------------------------------------------------------------------------

def _norm(s: str) -> str:
	return re.sub(r"\s+", " ", (s or "").strip().lower())


def _map_headers(header: list[str]) -> dict[str, int]:
	mapping = {}
	for i, h in enumerate(header):
		key = _norm(h).replace("_", " ")
		for field, names in HEADERS.items():
			if key in names and field not in mapping:
				mapping[field] = i
	return mapping


def parse_date(raw: str) -> date | None:
	s = (raw or "").strip()
	for fmt in DATE_FORMATS:
		try:
			return datetime.strptime(s, fmt).date()
		except ValueError:
			continue
	return None


def parse_amount(raw: str) -> Decimal | None:
	s = (raw or "").strip()
	if not s:
		return None
	neg = s.startswith("(") and s.endswith(")") or s.startswith("-")
	suffix = re.search(r"\b(dr|cr)\.?$", s, re.I)
	s = re.sub(r"(?i)(₹|rs\.?|inr|\(|\)|,|\s|\bdr\.?$|\bcr\.?$)", "", s).lstrip("-+")
	try:
		d = Decimal(s)
	except InvalidOperation:
		return None
	if not d.is_finite():
		return None
	if suffix and suffix.group(1).lower() == "dr":
		neg = True
	return -d if neg else d


def read_rows(text: str) -> tuple[list[str], list[list[str]]]:
	if len(text.encode("utf-8")) > MAX_BYTES:
		frappe.throw(_("The file is too large (max 2 MB)."))
	text = text.lstrip("﻿")
	try:
		dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
	except csv.Error:
		dialect = csv.excel
	reader = list(csv.reader(io.StringIO(text), dialect))
	reader = [r for r in reader if any(c.strip() for c in r)]
	if not reader:
		frappe.throw(_("The file is empty."))
	header, rows = reader[0], reader[1:]
	if len(rows) > MAX_ROWS:
		frappe.throw(_("Import up to {0} rows at a time; this file has {1}.").format(MAX_ROWS, len(rows)))
	return header, rows


def _lookups(user):
	accounts = {_norm(a.account_name): a.name for a in frappe.get_all(
		"Finance Account", {"user": user, "is_archived": 0}, ["name", "account_name"])}
	cats = frappe.get_all("Finance Category", {"user": user, "is_archived": 0},
	                      ["name", "category_name", "category_type", "parent_category"])
	by_id = {c.name: c for c in cats}
	top = {(c.category_type, _norm(c.category_name)): c.name for c in cats if not c.parent_category}
	sub = {(c.category_type, _norm(by_id[c.parent_category].category_name) if c.parent_category in by_id else "",
	        _norm(c.category_name)): c.name for c in cats if c.parent_category}
	any_sub = {}
	for (t, _p, n), name in sub.items():
		any_sub.setdefault((t, n), name)
	return accounts, top, sub, any_sub


def analyse(user: str, text: str, options: dict) -> dict:
	"""Parse and validate. Writes nothing."""
	header, raw_rows = read_rows(text)
	cols = _map_headers(header)
	if "date" not in cols:
		frappe.throw(_("Couldn't find a Date column. Expected a header like Date or Transaction Date."))
	if not ({"amount"} <= cols.keys() or {"debit", "credit"} & cols.keys()):
		frappe.throw(_("Couldn't find an Amount column (or Debit/Credit columns)."))

	accounts, top, sub, any_sub = _lookups(user)
	default_account = options.get("default_account")
	if default_account and default_account not in accounts.values():
		frappe.throw(_("Choose one of your active accounts as the default account."))
	create_missing = bool(options.get("create_missing_categories"))
	default_type = options.get("default_type") if options.get("default_type") in ("Expense", "Income") else "Expense"
	file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
	new_categories: dict[tuple[str, str], str] = {}

	def get(row, field):
		i = cols.get(field)
		return row[i].strip() if i is not None and i < len(row) else ""

	out = []
	for n, row in enumerate(raw_rows, start=2):  # row 1 is the header
		errors, r = [], {"row": n, "client_txn_id": f"imp:{file_hash}:{n}"}
		d = parse_date(get(row, "date"))
		if not d:
			errors.append(_("Unrecognised date '{0}' (use YYYY-MM-DD or DD/MM/YYYY)").format(get(row, "date")))
		amount = parse_amount(get(row, "amount")) if "amount" in cols else None
		side = None  # "debit" / "credit" when the statement says which column the money is in
		if amount is None and ({"debit", "credit"} & cols.keys()):
			dr, cr = parse_amount(get(row, "debit")), parse_amount(get(row, "credit"))
			if dr:
				amount, side = -abs(dr), "debit"
			elif cr:
				amount, side = abs(cr), "credit"
		drcr = _norm(get(row, "drcr"))
		if amount is not None and drcr in ("dr", "debit"):
			amount = -abs(amount)
		ttype = TYPES.get(_norm(get(row, "type")))
		if get(row, "type") and not ttype:
			errors.append(_("Unknown type '{0}' (use Expense, Income or Transfer)").format(get(row, "type")))
		if amount is None or amount == 0:
			errors.append(_("Missing or invalid amount '{0}'").format(get(row, "amount") or get(row, "debit") or get(row, "credit")))
		else:
			if not ttype:
				# Debit/credit columns state the direction; otherwise a minus sign means spending.
				ttype = "Income" if side == "credit" else "Expense" if amount < 0 else default_type
			amount = abs(amount)
			if amount != amount.quantize(Decimal("0.01")) or amount > MAX_AMOUNT:
				errors.append(_("Amount {0} is not valid").format(amount))
		ttype = ttype or default_type

		acc_name = get(row, "account")
		account = accounts.get(_norm(acc_name)) if acc_name else default_account
		if acc_name and not account:
			errors.append(_("Account '{0}' not found").format(acc_name))
		elif not account:
			errors.append(_("No account; choose a default account"))
		to_account = None
		if ttype == "Transfer":
			to_name = get(row, "to_account")
			to_account = accounts.get(_norm(to_name))
			if not to_account:
				errors.append(_("Transfer needs a valid To Account") if not to_name else _("Account '{0}' not found").format(to_name))
			elif to_account == account:
				errors.append(_("Transfer to the same account"))

		category = None
		cat_name, sub_name = get(row, "category"), get(row, "subcategory")
		if ttype != "Transfer":
			if "›" in cat_name and not sub_name:
				cat_name, sub_name = (p.strip() for p in cat_name.split("›", 1))
			if not cat_name and not sub_name:
				cat_name = "Other" if ttype == "Expense" else "Other Income"
			if sub_name:
				category = sub.get((ttype, _norm(cat_name), _norm(sub_name)))
			else:
				category = top.get((ttype, _norm(cat_name))) or any_sub.get((ttype, _norm(cat_name)))
			if not category:
				label = f"{cat_name} › {sub_name}" if sub_name else cat_name
				if create_missing:
					key = (ttype, label)
					new_categories.setdefault(key, label)
					category = f"new:{ttype}:{label}"
				else:
					errors.append(_("Category '{0}' not found ({1})").format(label, ttype.lower()))

		r.update({
			"transaction_date": str(d) if d else get(row, "date"),
			"transaction_type": ttype,
			"amount": float(amount) if amount is not None else None,
			"account": account,
			"to_account": to_account,
			"category": category,
			"title": get(row, "title")[:140] or None,
			"notes": get(row, "notes")[:2000] or None,
			"is_refund": 1 if ttype == "Expense" and _norm(get(row, "refund")) in ("yes", "y", "true", "1") else 0,
			"errors": errors,
			"status": "error" if errors else "ok",
		})
		out.append(r)

	_flag_existing(user, out)
	return {
		"columns": {k: header[i] for k, i in cols.items()},
		"rows": out,
		"new_categories": [{"type": t, "name": n} for (t, n) in new_categories],
		"summary": {s: sum(1 for r in out if r["status"] == s) for s in ("ok", "error", "duplicate", "imported")},
	}


def _flag_existing(user, rows):
	"""Mark rows already imported (same file) or matching an existing transaction."""
	ids = [r["client_txn_id"] for r in rows]
	done = set(frappe.get_all("Finance Transaction", {"user": user, "client_txn_id": ("in", ids)}, pluck="client_txn_id")) if ids else set()
	for r in rows:
		if r["status"] != "ok":
			continue
		if r["client_txn_id"] in done:
			r["status"] = "imported"
			continue
		match = frappe.db.sql(
			"""select name from `tabFinance Transaction` where user=%s and transaction_date=%s and amount=%s
			and transaction_type=%s and account=%s limit 1""",
			(user, r["transaction_date"], r["amount"], r["transaction_type"], r["account"]),
		)
		if match:
			r["status"] = "duplicate"


def commit(user: str, text: str, options: dict) -> dict:
	result = analyse(user, text, options)
	include_dupes = bool(options.get("include_duplicates"))
	created_cats: dict[str, str] = {}
	imported = skipped = failed = 0
	frappe.flags.expense_tracker_bulk = True  # budget alerts evaluated once at the end
	try:
		for r in result["rows"]:
			if r["status"] == "error" or r["status"] == "imported" or (r["status"] == "duplicate" and not include_dupes):
				skipped += 1
				continue
			frappe.db.savepoint("et_import_row")
			try:
				category = r["category"]
				if category and category.startswith("new:"):
					category = created_cats.get(category) or _create_category(user, category, created_cats)
				frappe.get_doc({
					"doctype": "Finance Transaction",
					"transaction_type": r["transaction_type"], "amount": r["amount"],
					"transaction_date": r["transaction_date"], "account": r["account"], "to_account": r["to_account"],
					"category": category, "title": r["title"], "notes": r["notes"], "is_refund": r["is_refund"],
					"client_txn_id": r["client_txn_id"], "source": "Import",
				}).insert()
				r["status"] = "imported"
				imported += 1
			except Exception as e:
				frappe.db.rollback(save_point="et_import_row")
				frappe.clear_messages()
				r["status"], r["errors"] = "error", [frappe.utils.strip_html(str(e))]
				failed += 1
	finally:
		frappe.flags.expense_tracker_bulk = False
	if imported:
		cache.bump(user)
		budgets.evaluate_alerts_safely(user)
	return {"imported": imported, "skipped": skipped, "failed": failed, "rows": result["rows"]}


def _create_category(user, key, created):
	_, ttype, label = key.split(":", 2)
	parent_name, _sep, child = label.partition(" › ")
	parent = frappe.db.get_value("Finance Category", {"user": user, "category_type": ttype, "category_name": parent_name,
	                                                   "parent_category": ("is", "not set"), "is_archived": 0}, "name")
	if not parent:
		parent = frappe.get_doc({"doctype": "Finance Category", "category_name": parent_name, "category_type": ttype,
		                         "icon": "tag", "color": "#64748b"}).insert().name
	name = parent
	if child:
		name = frappe.get_doc({"doctype": "Finance Category", "category_name": child, "category_type": ttype,
		                       "parent_category": parent, "icon": "tag", "color": "#64748b"}).insert().name
	created[key] = name
	return name
