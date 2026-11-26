import unittest
from decimal import Decimal

import frappe

from expense_tracker.services.money import D, percent, percent_change, validate_amount


class TestMoney(unittest.TestCase):
	def test_float_conversion_is_exact(self):
		self.assertEqual(D(0.1) + D(0.2), Decimal("0.30"))
		self.assertEqual(D("2.675"), Decimal("2.68"))  # half-up, not banker's

	def test_validate_amount(self):
		self.assertEqual(validate_amount("12.5"), Decimal("12.50"))
		for bad in ("0", "-1", "1.001", "inf", "x", None):
			with self.assertRaises(frappe.ValidationError):
				validate_amount(bad)

	def test_percent(self):
		self.assertIsNone(percent(10, 0))
		self.assertEqual(percent(1, 3), 33.3)

	def test_percent_change(self):
		self.assertEqual(percent_change(118, 100), 18.0)
		self.assertEqual(percent_change(75, 100), -25.0)
		self.assertIsNone(percent_change(50, 0))
