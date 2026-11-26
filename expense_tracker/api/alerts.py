"""Bank alert email settings, manual check and the processing log."""

import frappe
from frappe import _
from frappe.utils import cint, nowdate

from expense_tracker.api import ok, parse_dict, require_user
from expense_tracker.services.bank_alerts import ingest, mailbox
from expense_tracker.services.money import to_number


def _settings(user):
	p = frappe.get_doc("Expense Profile", user)
	from frappe.utils.password import get_decrypted_password

	has_password = bool(get_decrypted_password("Expense Profile", user, "alerts_app_password", raise_exception=False))
	accounts = frappe.get_all("Finance Account", {"user": user, "is_archived": 0}, ["name", "account_name", "account_last4"])
	return {
		"enabled": cint(p.alerts_enabled),
		"email": p.alerts_email,
		"has_password": has_password,  # the password itself is never sent back
		"since": str(p.alerts_since) if p.alerts_since else None,
		"last_checked": str(p.alerts_last_checked) if p.alerts_last_checked else None,
		"last_error": p.alerts_last_error,
		"accounts_without_digits": [a.account_name for a in accounts if not a.account_last4],
	}


@frappe.whitelist(methods=["GET"])
def get_settings():
	return ok(_settings(require_user()))


@frappe.whitelist(methods=["POST"])
def save_settings(data):
	user = require_user()
	values = parse_dict(data)
	p = frappe.get_doc("Expense Profile", user)
	p.check_permission("write")
	if "email" in values:
		email = (values.get("email") or "").strip().lower()
		if email and not frappe.utils.validate_email_address(email):
			frappe.throw(_("Enter a valid Gmail address."))
		if email != (p.alerts_email or ""):
			p.alerts_last_uid, p.alerts_uid_validity = 0, None  # a different mailbox starts fresh
		p.alerts_email = email or None
	if values.get("app_password"):
		p.alerts_app_password = str(values["app_password"]).replace(" ", "")[:64]
	if "since" in values:
		p.alerts_since = values.get("since") or nowdate()
	if "enabled" in values:
		p.alerts_enabled = 1 if cint(values["enabled"]) else 0
		if p.alerts_enabled and not p.alerts_since:
			p.alerts_since = nowdate()  # never import old history by surprise
	p.save()
	return ok(_settings(user))


@frappe.whitelist(methods=["POST"])
def test_connection():
	"""Sign in and count messages since the start date, without processing anything."""
	user = require_user()
	p = frappe.db.get_value("Expense Profile", user, ["alerts_email", "alerts_since"], as_dict=True)
	from frappe.utils.password import get_decrypted_password

	password = get_decrypted_password("Expense Profile", user, "alerts_app_password", raise_exception=False)
	if not p.alerts_email or not password:
		frappe.throw(_("Save the Gmail address and App Password first."))
	try:
		messages, _last, _validity = mailbox.fetch_new(p.alerts_email, password, 0, None, p.alerts_since)
	except mailbox.MailboxError as e:
		return ok({"ok": False, "error": str(e)})
	bank = sum(1 for m in messages if ingest.is_bank_sender(m.sender, m.subject, m.body))
	return ok({"ok": True, "messages": len(messages), "bank_messages": bank})


@frappe.whitelist(methods=["POST"])
def check_now():
	user = require_user()
	result = ingest.check_user(user)
	return ok(result)


@frappe.whitelist(methods=["GET"])
def log(limit=50):
	user = require_user()
	rows = frappe.get_all(
		"Bank Alert", {"user": user},
		["name", "received_on", "bank", "status", "transaction_type", "amount", "account_last4", "reference",
		 "merchant", "transaction", "note", "snippet"],
		order_by="creation desc", limit_page_length=min(max(cint(limit) or 50, 1), 200),
	)
	for r in rows:
		r["received_on"] = str(r["received_on"]) if r["received_on"] else None
		r["amount"] = to_number(r["amount"] or 0)
	return ok(rows)
