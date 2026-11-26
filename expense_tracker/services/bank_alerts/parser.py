"""Read Indian bank transaction alerts (email text) into structured data.

Pure functions, no database access. A result is returned only when the text
clearly describes a completed debit or credit with an amount; everything else
(OTPs, failed payments, collect requests, reminders, statements, offers)
returns None, so the app never invents a transaction.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

BANKS = (
	# (pattern matched against sender + text, display name)
	(re.compile(r"axis\s*bank|axisbank|axis\.bank", re.I), "Axis Bank"),
	(re.compile(r"karnataka\s*bank|ktkbank|karnatakabank", re.I), "Karnataka Bank"),
)

AMOUNT = re.compile(r"(?:INR|Rs\.?|₹)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)

# Messages that mention money but are not a completed transaction.
NOT_A_TRANSACTION = re.compile(
	r"\bOTP\b|one[\s-]time\s+password|\bfailed\b|\bdeclined\b|unsuccessful|could\s+not\s+be\s+processed"
	r"|has\s+requested|collect\s+request|payment\s+request|will\s+be\s+(?:debited|deducted|charged)"
	r"|is\s+due\b|due\s+date|minimum\s+(?:amount\s+)?due|statement\s+(?:for|of|is\s+ready)|e-?mandate"
	r"|pre-?approved|offer\b|cashback\s+up\s+to|win\b",
	re.I,
)

ACCOUNT = re.compile(
	r"(?:a/?c|acct|account|card)\s*(?:no\.?|number|num)?\s*(?:ending\s*(?:with|in)?)?\s*[:\-]?\s*"
	r"(?:[Xx*•]+\s*)?(\d{3,4})\b",
	re.I,
)
ENDING = re.compile(r"ending\s*(?:with|in)?\s*[:\-]?\s*(\d{4})\b", re.I)

REFERENCE = re.compile(
	r"(?:UPI\s*(?:Ref(?:erence)?|Txn|Transaction)?\.?\s*(?:No\.?|Number|ID|#)?|RRN|IMPS\s*Ref(?:\.|erence)?\s*(?:No\.?)?"
	r"|Ref(?:erence)?\.?\s*(?:No\.?|Number|#|ID)|Transaction\s*(?:ID|Ref(?:erence)?)(?:\s*No\.?)?)\s*[:\-]?\s*([A-Za-z0-9]{8,22})\b",
	re.I,
)
# e.g. "UPI/P2M/432112345678/SWIGGY" or "UPI/P2A/432112345678/RAVI KUMAR/..."
UPI_PATH = re.compile(r"\bUPI/(?:P2[AM]|[A-Z]{2,5})/(\d{9,14})/([^/\n.]{2,40}?)(?=[/.]|\s{2,}|$)", re.I)
VPA = re.compile(r"\b([a-z0-9][a-z0-9.\-_]{1,60}@[a-z][a-z0-9]{1,20})\b(?![.\w])", re.I)

DEBIT_ON_ACCOUNT = [
	re.compile(r"(?:debited|withdrawn|deducted|spent|paid)\b[^.]{0,60}?\b(?:from|on|in|using|via)\s+(?:your\s+)?(?:a/?c|acct|account|card)", re.I),
	re.compile(r"(?:a/?c|acct|account|card)\b[^.]{0,40}?\b(?:is|has\s+been|was)\s+debited", re.I),
	re.compile(r"\b(?:debited|withdrawn|deducted)\b", re.I),
	re.compile(r"\b(?:spent|paid|sent)\b", re.I),
]
CREDIT_ON_ACCOUNT = [
	re.compile(r"credited\b[^.]{0,60}?\b(?:to|in|into)\s+(?:your\s+)?(?:a/?c|acct|account)", re.I),
	re.compile(r"(?:a/?c|acct|account)\b[^.]{0,40}?\b(?:is|has\s+been|was)\s+credited", re.I),
	re.compile(r"\b(?:received|deposited|reversed|refunded)\b", re.I),
	re.compile(r"\bcredited\b", re.I),
]

DATE_PATTERNS = (
	(re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b"), "dmy"),
	(re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2})\b"), "dmy2"),
	(re.compile(r"\b(\d{1,2})[-\s]([A-Za-z]{3,9})[-\s,]*(\d{2,4})\b"), "dMonY"),
	(re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
)


@dataclass
class ParsedAlert:
	direction: str  # "debit" | "credit"
	amount: Decimal
	bank: str | None = None
	account_last4: str | None = None
	reference: str | None = None
	vpa: str | None = None
	merchant: str | None = None
	txn_date: date | None = None
	notes: list[str] = field(default_factory=list)

	@property
	def transaction_type(self) -> str:
		return "Expense" if self.direction == "debit" else "Income"


def html_to_text(html: str) -> str:
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	for tag in soup(["script", "style", "head"]):
		tag.decompose()
	return soup.get_text(" ")


def _clean(text: str) -> str:
	return re.sub(r"[ \t\r\f\v ]+", " ", text or "").strip()


def detect_bank(sender: str, text: str) -> str | None:
	for pattern, name in BANKS:
		if pattern.search(sender or "") :
			return name
	for pattern, name in BANKS:
		if pattern.search(text or ""):
			return name
	return None


def _direction(text: str) -> str | None:
	"""Debit or credit *for the customer's account*. Strong (account-specific)
	phrases win over generic words, so 'debited from your A/c … credited to
	swiggy@icici' is a debit."""
	for level in range(len(DEBIT_ON_ACCOUNT)):
		d = DEBIT_ON_ACCOUNT[level].search(text)
		c = CREDIT_ON_ACCOUNT[level].search(text)
		if d and not c:
			return "debit"
		if c and not d:
			return "credit"
		if d and c:
			return "debit" if d.start() < c.start() else "credit"
	return None


def _amount(text: str) -> Decimal | None:
	m = AMOUNT.search(text)
	if not m:
		return None
	try:
		value = Decimal(m.group(1).replace(",", ""))
	except InvalidOperation:
		return None
	return value if value > 0 else None


def _date(text: str) -> date | None:
	for pattern, kind in DATE_PATTERNS:
		for m in pattern.finditer(text):
			try:
				if kind == "ymd":
					return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
				if kind == "dmy":
					return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
				if kind == "dmy2":
					return date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
				year = int(m.group(3))
				year = year + 2000 if year < 100 else year
				return datetime.strptime(f"{m.group(1)} {m.group(2)[:3]} {year}", "%d %b %Y").date()
			except ValueError:
				continue
	return None


def _merchant(text: str, direction: str, vpa: str | None, upi_name: str | None) -> str | None:
	"""Payee (debits) or payer (credits). Priority: name in a UPI path, the UPI ID,
	then a "to …" / "from …" phrase. Amounts and account words are never names."""
	if upi_name:
		return upi_name.strip(" .-")[:60]
	if vpa:
		return vpa
	stop = r"(?=\s+(?:on|at|via|using|ref|upi|for|is|has|was|with|dated|avl|available|info)\b|[.,;()]|$)"
	words = ("to", "at", "towards") if direction == "debit" else ("from", "by")
	for word in words:  # earlier words are preferred ("from X" over "by X")
		for m in re.finditer(rf"\b{word}\s+(?:VPA\s+)?([A-Za-z0-9&'@._\- ]{{3,40}}?){stop}", text, re.I):
			name = m.group(1).strip(" .-")
			if re.search(r"\b(?:your|a/?c|account|acct|card|rs|inr|neft|imps|rtgs|upi)\b|₹|\d{3,}", name, re.I):
				continue
			return name[:60]
	return None


def parse(sender: str, subject: str, body: str) -> ParsedAlert | None:
	text = _clean(f"{subject or ''}. {body or ''}")
	if NOT_A_TRANSACTION.search(text):
		return None
	amount = _amount(text)
	direction = _direction(text)
	if not amount or not direction:
		return None

	upi = UPI_PATH.search(text)
	ref_match = REFERENCE.search(text)
	reference = upi.group(1) if upi else (ref_match.group(1) if ref_match else None)
	vpa = next((v.lower() for v in VPA.findall(text) if "." not in v.split("@", 1)[1]), None)
	acct = ENDING.search(text) or ACCOUNT.search(text)
	last4 = acct.group(1)[-4:] if acct else None

	parsed = ParsedAlert(
		direction=direction,
		amount=amount,
		bank=detect_bank(sender, text),
		account_last4=last4 if last4 and len(last4) == 4 else None,
		reference=reference,
		vpa=vpa,
		txn_date=_date(text),
	)
	parsed.merchant = _merchant(text, direction, vpa, upi.group(2) if upi else None)
	return parsed


def merchant_key(parsed: ParsedAlert) -> str | None:
	"""Stable key for remembering categories: the UPI ID, else the normalised name."""
	if parsed.vpa:
		return parsed.vpa.lower()
	if parsed.merchant:
		return re.sub(r"[^a-z0-9]+", " ", parsed.merchant.lower()).strip()[:140] or None
	return None


def mask(text: str, limit: int = 500) -> str:
	"""Keep only the start of a message and mask long digit runs (account numbers)."""
	text = re.sub(r"\d{5,}", lambda m: "X" * (len(m.group()) - 4) + m.group()[-4:], _clean(text))
	return text[:limit]
