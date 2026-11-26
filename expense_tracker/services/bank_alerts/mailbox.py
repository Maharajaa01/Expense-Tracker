"""Read-only IMAP access to the dedicated alerts mailbox (Gmail).

Opens the mailbox read-only (nothing is marked read, moved or deleted) and
returns only messages newer than the last one processed. No message content
is stored by this module.
"""

import email
import imaplib
from dataclasses import dataclass
from datetime import date, datetime
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

from expense_tracker.services.bank_alerts.parser import html_to_text

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAX_PER_RUN = 100


class MailboxError(Exception):
	"""Connection/login problem, with a message safe to show the user."""


@dataclass
class Message:
	uid: int
	message_id: str
	sender: str
	subject: str
	body: str
	received: datetime | None


def normalise_message_id(value: str | None) -> str:
	"""'<abc@mail.gmail.com>' → 'abc@mail.gmail.com'. The angle brackets would be
	stripped as HTML when saved, so they are removed up front, consistently."""
	return (value or "").strip().strip("<>").strip()[:255]


def _decode(value) -> str:
	try:
		return str(make_header(decode_header(value or "")))
	except Exception:
		return value or ""


def _body(msg) -> str:
	plain, html = [], []
	for part in msg.walk() if msg.is_multipart() else [msg]:
		if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
			continue
		try:
			payload = part.get_payload(decode=True)
			if payload is None:
				continue
			text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
		except Exception:
			continue
		(plain if part.get_content_type() == "text/plain" else html if part.get_content_type() == "text/html" else []).append(text)
	return "\n".join(plain) if plain else html_to_text("\n".join(html))


def fetch_new(address: str, password: str, last_uid: int, uid_validity: str | None, since: date | None):
	"""Return (messages, new_last_uid, uid_validity). Raises MailboxError."""
	try:
		conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
	except OSError as e:
		raise MailboxError(f"Couldn't reach Gmail ({e.__class__.__name__}). It will be retried.") from e
	try:
		try:
			conn.login(address, password.replace(" ", ""))
		except imaplib.IMAP4.error as e:
			raise MailboxError(
				"Gmail rejected the sign-in. Check the address and App Password "
				"(Google Account → Security → App passwords)."
			) from e
		typ, _ = conn.select("INBOX", readonly=True)
		if typ != "OK":
			raise MailboxError("Couldn't open the inbox.")
		current_validity = (conn.response("UIDVALIDITY")[1] or [b""])[0]
		current_validity = current_validity.decode() if isinstance(current_validity, bytes) else str(current_validity or "")
		if uid_validity and current_validity and current_validity != uid_validity:
			last_uid = 0  # mailbox was rebuilt: start over (duplicates are still skipped)

		if last_uid:
			typ, data = conn.uid("search", None, f"UID {last_uid + 1}:*")
		else:
			start = (since or date.today()).strftime("%d-%b-%Y")
			typ, data = conn.uid("search", None, f"SINCE {start}")
		uids = sorted(int(u) for u in (data[0] or b"").split() if int(u) > last_uid)[:MAX_PER_RUN]

		messages = []
		for uid in uids:
			typ, parts = conn.uid("fetch", str(uid), "(BODY.PEEK[])")  # PEEK: don't mark as read
			raw = next((p[1] for p in parts or [] if isinstance(p, tuple)), None)
			if not raw:
				continue
			msg = email.message_from_bytes(raw)
			try:
				received = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
			except (TypeError, ValueError):
				received = None
			messages.append(Message(
				uid=uid,
				message_id=normalise_message_id(msg.get("Message-ID")) or f"uid-{current_validity}-{uid}",
				sender=parseaddr(msg.get("From", ""))[1].lower(),
				subject=_decode(msg.get("Subject")),
				body=_body(msg),
				received=received,
			))
		new_last = max([last_uid, *uids]) if uids else last_uid
		return messages, new_last, current_validity
	finally:
		try:
			conn.logout()
		except Exception:
			pass
