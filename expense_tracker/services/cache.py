"""Per-user data version used to invalidate cached summaries.

Every write that changes financial figures calls :func:`bump`. Cached
summaries include the version in their key, so stale entries are simply never
read again and expire on their own.
"""

import frappe

_KEY = "expense_tracker:data_version:{user}"


def get_version(user: str) -> int:
	return int(frappe.cache.get_value(_KEY.format(user=user)) or 0)


def bump(user: str) -> None:
	key = _KEY.format(user=user)
	frappe.cache.set_value(key, get_version(user) + 1)


def cached(user: str, name: str, generator, ttl: int = 600):
	"""Return a cached value keyed by user, name and data version."""
	key = f"expense_tracker:{name}:{user}:v{get_version(user)}"
	value = frappe.cache.get_value(key)
	if value is None:
		value = generator()
		frappe.cache.set_value(key, value, expires_in_sec=ttl)
	return value
