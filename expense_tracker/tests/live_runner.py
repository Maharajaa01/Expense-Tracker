"""Run the app's tests on an existing (shared) site without side effects.

Unlike ``bench run-tests`` this runner does not disable the site's scheduler,
does not create global test records, and fails loudly if anything commits.
Every test rolls back in ``tearDown`` (see tests/utils.py).

Usage::

    bench --site <site> execute expense_tracker.tests.live_runner.run
    bench --site <site> execute expense_tracker.tests.live_runner.run --kwargs "{'pattern': 'test_ledger.py'}"
"""

import os
import sys
import unittest

import frappe


def run(pattern: str = "test_*.py", verbosity: int = 2):
	start_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	top = os.path.dirname(start_dir)

	frappe.flags.in_test = True
	frappe.db.rollback()

	real_commit = frappe.db.commit

	def forbidden_commit(*args, **kwargs):
		raise AssertionError("frappe.db.commit() was called during a test; tests must not persist data.")

	frappe.db.commit = forbidden_commit
	try:
		suite = unittest.defaultTestLoader.discover(start_dir, pattern=pattern, top_level_dir=top)
		result = unittest.TextTestRunner(stream=sys.stdout, verbosity=verbosity).run(suite)
	finally:
		frappe.db.rollback()
		frappe.db.commit = real_commit
		frappe.flags.in_test = False

	if not result.wasSuccessful():
		raise SystemExit(1)
