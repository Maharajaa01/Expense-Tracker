"""Pure date-maths tests for recurring schedules (no DB)."""

import unittest
from datetime import date

from expense_tracker.services.recurrence import first_on_or_after, occurrence, occurrences_between


class TestRecurrence(unittest.TestCase):
	def test_month_end_anchor(self):
		got = [occurrence("2026-01-31", n, "Monthly") for n in range(4)]
		self.assertEqual(got, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)])

	def test_leap_year(self):
		self.assertEqual(occurrence("2027-02-28", 1, "Yearly"), date(2028, 2, 28))
		self.assertEqual(occurrence("2028-02-29", 1, "Yearly"), date(2029, 2, 28))
		self.assertEqual(occurrence("2028-02-29", 4, "Yearly"), date(2032, 2, 29))

	def test_quarterly_and_weekly(self):
		self.assertEqual(occurrence("2026-01-15", 2, "Quarterly"), date(2026, 7, 15))
		self.assertEqual(occurrence("2026-01-01", 3, "Weekly", 2), date(2026, 2, 12))

	def test_custom(self):
		self.assertEqual(occurrence("2026-01-01", 2, "Custom", 10, "Days"), date(2026, 1, 21))
		self.assertEqual(occurrence("2026-01-31", 1, "Custom", 2, "Months"), date(2026, 3, 31))

	def test_first_on_or_after(self):
		self.assertEqual(first_on_or_after("2026-01-31", "2026-02-15", "Monthly"), (1, date(2026, 2, 28)))
		self.assertEqual(first_on_or_after("2026-01-31", "2026-01-01", "Monthly"), (0, date(2026, 1, 31)))
		self.assertEqual(first_on_or_after("2020-01-01", "2026-06-02", "Daily")[1], date(2026, 6, 2))

	def test_between(self):
		got = occurrences_between("2026-01-05", "2026-01-01", "2026-01-31", "Weekly")
		self.assertEqual(len(got), 4)
		self.assertEqual(got[0], date(2026, 1, 5))
