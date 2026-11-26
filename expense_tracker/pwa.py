"""Serve the service worker and web manifest from inside ``/expense/``.

A service worker can only control pages at or below the path it is served
from. Frappe serves build output from ``/assets/...``, so the worker is
served from ``/expense/sw.js`` by this page renderer instead (no web-server
configuration needed). Registered via the ``page_renderer`` hook.

Note: ``website_route_rules`` map ``/expense/<path>`` to the SPA endpoint
before renderers run, so the original request path is checked here.
"""

import json
import os

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

SW_PATH = "/expense/sw.js"
MANIFEST_PATH = "/expense/manifest.webmanifest"
ICONS = "/assets/expense_tracker/icons"


def _request_path() -> str:
	req = getattr(frappe.local, "request", None)
	return req.path if req else ""


def manifest() -> dict:
	return {
		"id": "/expense",
		"name": "Expense Tracker",
		"short_name": "Expenses",
		"description": "Track spending, budgets and savings.",
		# /expense/ redirects to /expense; a start URL must not redirect.
		"start_url": "/expense",
		"scope": "/expense",
		"display": "standalone",
		"orientation": "portrait",
		"background_color": "#faf8f5",
		"theme_color": "#047857",
		"categories": ["finance", "productivity"],
		"icons": [
			{"src": f"{ICONS}/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": f"{ICONS}/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
			{"src": f"{ICONS}/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
		],
		"shortcuts": [
			{"name": "Add expense", "url": "/expense?add=Expense", "icons": [{"src": f"{ICONS}/icon-192.png", "sizes": "192x192"}]},
		],
	}


class PWARenderer(BaseRenderer):
	def can_render(self):
		return _request_path() in (SW_PATH, MANIFEST_PATH)

	def render(self):
		if _request_path() == MANIFEST_PATH:
			return Response(
				json.dumps(manifest()),
				mimetype="application/manifest+json",
				headers={"Cache-Control": "no-cache"},
			)
		path = frappe.get_app_path("expense_tracker", "public", "frontend", "sw.js")
		if not os.path.exists(path):
			return Response("// service worker not built", status=404, mimetype="application/javascript")
		with open(path, encoding="utf-8") as f:
			body = f.read()
		return Response(
			body,
			mimetype="application/javascript",
			headers={
				# Browsers re-check the worker on every navigation; never let a proxy pin an old one.
				"Cache-Control": "no-cache, no-store, must-revalidate",
				# Scope "/expense" (no trailing slash) so the bare /expense URL is controlled too.
				"Service-Worker-Allowed": "/expense",
			},
		)
