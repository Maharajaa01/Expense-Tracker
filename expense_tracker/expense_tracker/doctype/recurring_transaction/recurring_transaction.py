# Copyright (c) 2026, Maharaja and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from expense_tracker.services import cache
from expense_tracker.services.ownership import assign_user
from expense_tracker.services.recurrence import first_on_or_after
from expense_tracker.services.transactions import clean_text, validate_date, validate_entry

SCHEDULE_FIELDS = ("frequency", "interval", "custom_unit", "start_date")


class RecurringTransaction(Document):
	def before_validate(self):
		assign_user(self)

	def validate(self):
		self.title = clean_text(self.title, 140)
		validate_entry(self, check_archived=bool(self.is_active))
		validate_date(self.start_date, "Start date")
		self.interval = max(int(self.interval or 1), 1)
		self.remind_days_before = min(max(int(self.remind_days_before or 0), 0), 30)
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End date must be on or after the start date."))
		if self._schedule_changed() or not self.next_run_date:
			self._reset_next_run()
		if self.end_date and self.next_run_date and getdate(self.next_run_date) > getdate(self.end_date):
			self.next_run_date = None

	def on_update(self):
		cache.bump(self.user)

	def after_delete(self):
		cache.bump(self.user)

	def _schedule_changed(self) -> bool:
		before = self.get_doc_before_save()
		return bool(before) and any(str(before.get(f)) != str(self.get(f)) for f in SCHEDULE_FIELDS)

	def _reset_next_run(self):
		"""Next due date: first occurrence on/after today and after the last posted run.

		Past occurrences before creation are not back-filled (users add history
		manually or via import); that avoids surprise bulk postings.
		"""
		floor = getdate(nowdate())
		if self.last_run_date and getdate(self.last_run_date) >= floor:
			floor = frappe.utils.add_days(self.last_run_date, 1)
		_idx, d = first_on_or_after(self.start_date, floor, self.frequency, self.interval, self.custom_unit)
		self.next_run_date = d
