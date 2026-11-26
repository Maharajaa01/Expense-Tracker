"""Turn alert emails into transactions (docs/BANK_ALERTS.md).

* Debit → Expense, credit → Income, posted immediately so balances are right.
* Category: the one last used for the same payee, else "Uncategorised" with
  ``needs_review = 1`` so it appears in the "To categorise" list.
* Duplicates: the bank reference becomes the client transaction ID
  (``bank:<ref>``), so the same payment can never be posted twice.
* Every email produces one Bank Alert log row (parsed fields only).
"""

import hashlib
import re

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate

from expense_tracker.services.bank_alerts import mailbox, parser
from expense_tracker.services.money import to_number

# Only messages from these sender domains are read at all.
BANK_SENDER_DOMAINS = ("axisbank.com", "axis.bank.in", "axisbank.co.in", "ktkbank.com", "karnatakabank.com", "karnatakabank.co.in")
UNCATEGORISED = {"Expense": ("Uncategorised", "inbox", "#94a3b8"), "Income": ("Uncategorised income", "inbox", "#94a3b8")}


def is_bank_sender(sender: str, subject: str, body: str) -> bool:
	domain = (sender or "").rsplit("@", 1)[-1]
	if any(domain == d or domain.endswith("." + d) for d in BANK_SENDER_DOMAINS):
		return True
	# Gmail auto-forwarding keeps the bank as sender; manual forwards ("Fwd:") carry it in the body.
	return bool(re.search(r"From:.{0,80}@(?:" + "|".join(re.escape(d) for d in BANK_SENDER_DOMAINS) + r")\b", body or "", re.I | re.S))


def uncategorised(user: str, ttype: str) -> str:
	name, icon, color = UNCATEGORISED[ttype]
	existing = frappe.db.get_value("Finance Category", {"user": user, "category_type": ttype, "category_name": name}, "name")
	if existing:
		frappe.db.set_value("Finance Category", existing, "is_archived", 0, update_modified=False)
		return existing
	return frappe.get_doc({
		"doctype": "Finance Category", "user": user, "category_name": name, "category_type": ttype,
		"icon": icon, "color": color, "is_default": 1, "sort_order": 999,
	}).insert(ignore_permissions=True).name


def remembered_category(user: str, key: str | None, ttype: str) -> str | None:
	"""Category the user last chose for this payee (ignores still-uncategorised entries)."""
	if not key:
		return None
	rows = frappe.db.sql(
		"""select t.category from `tabFinance Transaction` t
		join `tabFinance Category` c on c.name = t.category and c.is_archived = 0
		where t.user = %s and t.merchant_key = %s and t.transaction_type = %s and t.needs_review = 0
		order by t.transaction_date desc, t.modified desc limit 1""",
		(user, key, ttype),
		pluck=True,
	)
	return rows[0] if rows else None


def _match_account(user: str, last4: str | None) -> tuple[str | None, str | None]:
	if not last4:
		return None, _("The alert doesn't show an account number.")
	names = frappe.get_all("Finance Account", {"user": user, "is_archived": 0, "account_last4": last4}, pluck="name")
	if len(names) == 1:
		return names[0], None
	if not names:
		return None, _("No account ends in {0}. Add these digits to the account under Accounts → Edit.").format(last4)
	return None, _("More than one account ends in {0}.").format(last4)


def process_message(user: str, msg: "mailbox.Message") -> dict:
	"""Process one email for one user. Returns the Bank Alert as a dict."""
	message_id = mailbox.normalise_message_id(msg.message_id) or "mail-" + hashlib.sha1(msg.body.encode()).hexdigest()[:24]
	if frappe.db.exists("Bank Alert", {"user": user, "message_id": message_id}):
		return {"status": "Seen"}
	log = {
		"doctype": "Bank Alert", "user": user, "message_id": message_id, "sender": msg.sender[:140],
		"received_on": msg.received.replace(tzinfo=None) if msg.received else now_datetime(),
	}
	if not is_bank_sender(msg.sender, msg.subject, msg.body):
		return _log({**log, "status": "Ignored", "note": _("Not from a supported bank.")})

	parsed = parser.parse(msg.sender, msg.subject, msg.body)
	if not parsed:
		return _log({**log, "status": "Ignored" if parser.NOT_A_TRANSACTION.search(f"{msg.subject} {msg.body}") else "Unrecognised",
		             "bank": parser.detect_bank(msg.sender, msg.body),
		             "snippet": parser.mask(f"{msg.subject}. {msg.body}")})

	log.update({
		"bank": parsed.bank, "transaction_type": parsed.transaction_type, "amount": parsed.amount,
		"account_last4": parsed.account_last4, "reference": parsed.reference, "merchant": parsed.merchant,
		"alert_date": parsed.txn_date,
	})
	account, problem = _match_account(user, parsed.account_last4)
	if not account:
		return _log({**log, "status": "Needs Account", "note": problem})

	cid = f"bank:{parsed.reference}" if parsed.reference else "mail:" + hashlib.sha1(message_id.encode()).hexdigest()[:24]
	existing = frappe.db.get_value("Finance Transaction", {"user": user, "client_txn_id": cid}, "name")
	if existing:
		return _log({**log, "status": "Duplicate", "transaction": existing, "note": _("Already recorded.")})

	key = parser.merchant_key(parsed)
	ttype = parsed.transaction_type
	category = remembered_category(user, key, ttype)
	txn_date = parsed.txn_date or (msg.received.date() if msg.received else getdate(nowdate()))
	if txn_date > getdate(nowdate()):
		txn_date = getdate(nowdate())
	frappe.db.savepoint("et_bank_alert")
	try:
		doc = frappe.get_doc({
			"doctype": "Finance Transaction",
			"user": user,
			"transaction_type": ttype,
			"amount": parsed.amount,
			"account": account,
			"category": category or uncategorised(user, ttype),
			"transaction_date": txn_date,
			"title": (parsed.merchant or ("Bank credit" if ttype == "Income" else "Bank debit"))[:140],
			"notes": f"From {parsed.bank or 'bank'} alert" + (f", ref {parsed.reference}" if parsed.reference else ""),
			"client_txn_id": cid,
			"source": "Bank Alert",
			"needs_review": 0 if category else 1,
			"merchant_key": key,
			"bank_reference": parsed.reference,
		})
		doc.insert(ignore_permissions=True)
	except Exception as e:
		frappe.db.rollback(save_point="et_bank_alert")
		frappe.clear_messages()
		return _log({**log, "status": "Failed", "note": frappe.utils.strip_html(str(e))[:500]})
	return _log({**log, "status": "Posted", "transaction": doc.name,
	             "note": _("Category remembered from earlier payments.") if category else None})


def _log(values: dict) -> dict:
	doc = frappe.get_doc(values).insert(ignore_permissions=True)
	return {"status": doc.status, "name": doc.name, "transaction": doc.transaction, "amount": to_number(doc.amount or 0)}


def check_user(user: str) -> dict:
	"""Fetch and process new alerts for one user. Never raises for mailbox problems."""
	p = frappe.db.get_value("Expense Profile", user, ["alerts_enabled", "alerts_email", "alerts_last_uid",
	                                                  "alerts_uid_validity", "alerts_since"], as_dict=True)
	if not p or not p.alerts_enabled or not p.alerts_email:
		return {"ok": False, "error": _("Bank alert emails are not set up.")}
	from frappe.utils.password import get_decrypted_password

	password = get_decrypted_password("Expense Profile", user, "alerts_app_password", raise_exception=False)
	if not password:
		return {"ok": False, "error": _("Add the Google App Password for the alerts mailbox.")}
	try:
		messages, last_uid, validity = mailbox.fetch_new(p.alerts_email, password, p.alerts_last_uid or 0,
		                                                 p.alerts_uid_validity, p.alerts_since)
	except mailbox.MailboxError as e:
		_set_profile(user, alerts_last_checked=now_datetime(), alerts_last_error=str(e))
		_notify_error(user, str(e))
		return {"ok": False, "error": str(e)}

	results = {"Posted": 0, "Duplicate": 0, "Needs Account": 0, "Unrecognised": 0, "Ignored": 0, "Failed": 0}
	frappe.flags.expense_tracker_bulk = True
	try:
		for msg in messages:
			r = process_message(user, msg)
			if r["status"] in results:
				results[r["status"]] += 1
	finally:
		frappe.flags.expense_tracker_bulk = False
	if results["Posted"]:
		from expense_tracker.services import budgets, cache

		cache.bump(user)
		budgets.evaluate_alerts_safely(user)
	_set_profile(user, alerts_last_uid=last_uid, alerts_uid_validity=validity, alerts_last_checked=now_datetime(), alerts_last_error=None)
	return {"ok": True, "checked": len(messages), "results": results}


def _set_profile(user, **values):
	frappe.db.set_value("Expense Profile", user, values, update_modified=False)


def _notify_error(user, message):
	"""One notification per day for a failing mailbox (not one every few minutes)."""
	key = f"alerts-error:{user}:{nowdate()}"
	if not frappe.db.exists("Finance Notification", {"dedup_key": key}):
		frappe.get_doc({"doctype": "Finance Notification", "user": user, "notification_type": "System", "severity": "Warning",
		                "title": _("Couldn't read your bank alert emails"), "message": message, "dedup_key": key}).insert(ignore_permissions=True)


def check_all():
	"""Scheduler: check every enabled mailbox. One user's failure never blocks others."""
	for user in frappe.get_all("Expense Profile", {"alerts_enabled": 1}, pluck="user"):
		try:
			check_user(user)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Expense Tracker: bank alerts for {user} failed")
