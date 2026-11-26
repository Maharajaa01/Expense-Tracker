"""CSV export and import."""

import frappe

from expense_tracker.api import ok, parse_dict, require_user
from expense_tracker.services import csv_io


@frappe.whitelist(methods=["GET"])
def export_csv(filters=None):
	user = require_user()
	filename, content = csv_io.export(user, parse_dict(filters))
	frappe.response["type"] = "download"
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["content_type"] = "text/csv; charset=utf-8"


@frappe.whitelist(methods=["POST"])
def preview_import(text, options=None):
	"""Validate a CSV without writing anything."""
	return ok(csv_io.analyse(require_user(), text or "", parse_dict(options)))


@frappe.whitelist(methods=["POST"])
def commit_import(text, options=None):
	return ok(csv_io.commit(require_user(), text or "", parse_dict(options)))
