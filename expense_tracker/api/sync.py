"""Offline sync: apply a batch of queued client operations.

Each operation is applied independently inside its own savepoint, so one
bad operation never blocks the rest. Results per operation:

* ``applied``   – done now
* ``duplicate`` – already applied earlier (same client_txn_id); returns the record
* ``conflict``  – the record changed or was deleted on another device; returns the
                  server version (or ``null`` if deleted) so the user can choose
* ``rejected``  – validation failed (e.g. archived account); message explains why
* ``error``     – unexpected server error; safe to retry

Creates are idempotent via the unique (user, client_txn_id) index. Deletes of
records that no longer exist count as applied.
"""

import hashlib
import json

import frappe
from frappe import _

from expense_tracker.api import ok, parse_dict, pick, require_user
from expense_tracker.api.transactions import EDITABLE
from expense_tracker.services import queries

MAX_BATCH = 50


@frappe.whitelist(methods=["POST"])
def push(ops, device_id=None):
	user = require_user()
	ops = frappe.parse_json(ops) if isinstance(ops, str) else ops
	if not isinstance(ops, list):
		frappe.throw(_("Invalid sync batch."))
	if len(ops) > MAX_BATCH:
		frappe.throw(_("Too many changes in one batch (max {0}).").format(MAX_BATCH))
	device_id = (device_id or "")[:64] or None
	results = [_apply(user, parse_dict(op), device_id) for op in ops]
	if any(r["status"] in ("applied",) for r in results):
		from expense_tracker.services import cache

		cache.bump(user)
	return ok(results)


def _apply(user: str, op: dict, device_id: str | None) -> dict:
	cid = str(op.get("client_txn_id") or "")[:64]
	kind = op.get("op")
	out = {"client_txn_id": cid, "op": kind}
	if not cid or kind not in ("create", "update", "delete"):
		return {**out, "status": "rejected", "message": _("Invalid change.")}

	frappe.db.savepoint("et_sync_op")
	try:
		if kind == "create":
			result = _create(user, cid, op)
		elif kind == "update":
			result = _update(user, op)
		else:
			result = _delete(user, op)
	except (frappe.ValidationError, frappe.PermissionError) as e:  # validation, link, mandatory, permission
		frappe.db.rollback(save_point="et_sync_op")
		frappe.clear_messages()
		result = {"status": "rejected", "message": frappe.utils.strip_html(str(e)) or _("This change was not accepted.")}
	except Exception:
		frappe.db.rollback(save_point="et_sync_op")
		frappe.clear_messages()
		frappe.log_error(title="Expense Tracker: offline sync operation failed")
		result = {"status": "error", "message": _("Server error. It will be retried.")}

	_log(user, cid, kind, result, op, device_id)
	return {**out, **result}


def _create(user, cid, op):
	existing = frappe.db.get_value("Finance Transaction", {"user": user, "client_txn_id": cid}, "name")
	if existing:
		return {"status": "duplicate", "transaction": queries.get_row(user, existing)}
	doc = frappe.get_doc({"doctype": "Finance Transaction", **pick(parse_dict(op.get("data")), EDITABLE),
	                      "client_txn_id": cid, "source": "Sync"})
	doc.insert()
	return {"status": "applied", "transaction": queries.get_row(user, doc.name)}


def _update(user, op):
	name = op.get("name")
	row = frappe.db.get_value("Finance Transaction", {"name": name, "user": user}, ["name", "modified", "savings_goal"], as_dict=True)
	if not row:
		return {"status": "conflict", "reason": "deleted", "message": _("This transaction was deleted on another device."),
		        "transaction": None}
	expected = op.get("expected_modified")
	if expected and str(row.modified) != str(expected) and not op.get("force"):
		return {"status": "conflict", "reason": "changed", "message": _("This transaction was changed on another device."),
		        "transaction": queries.get_row(user, name)}
	if row.savings_goal:
		frappe.throw(_("This transfer belongs to a savings goal. Edit it from the goal instead."))
	doc = frappe.get_doc("Finance Transaction", name)
	doc.check_permission("write")
	doc.update(pick(parse_dict(op.get("data")), EDITABLE))
	doc.save()
	return {"status": "applied", "transaction": queries.get_row(user, name)}


def _delete(user, op):
	name = op.get("name")
	if not frappe.db.exists("Finance Transaction", {"name": name, "user": user}):
		return {"status": "applied", "transaction": None}  # already gone: deleting is idempotent
	doc = frappe.get_doc("Finance Transaction", name)
	doc.check_permission("delete")
	doc.delete()
	return {"status": "applied", "transaction": None}


def _log(user, cid, kind, result, op, device_id):
	status = {"applied": "Applied", "duplicate": "Duplicate", "conflict": "Conflict"}.get(result["status"], "Failed")
	payload = json.dumps(op.get("data") or {}, sort_keys=True, default=str)
	txn = (result.get("transaction") or {}).get("name") if isinstance(result.get("transaction"), dict) else op.get("name")
	frappe.get_doc({
		"doctype": "Offline Sync Log",
		"user": user,
		"client_txn_id": cid,
		"operation": kind,
		"status": status,
		"reference_doctype": "Finance Transaction" if txn and frappe.db.exists("Finance Transaction", txn) else None,
		"reference_name": txn if txn and frappe.db.exists("Finance Transaction", txn) else None,
		"device_id": device_id,
		"payload_hash": hashlib.sha256(payload.encode()).hexdigest(),
		"error": result.get("message") if status in ("Failed", "Conflict") else None,
	}).insert(ignore_permissions=True)
