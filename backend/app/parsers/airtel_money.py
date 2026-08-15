"""Airtel Money SMS parser.

Supports classic Airtel Money wording ("You have sent…") and the compact
Kenyan format seen in the wild:

  E3PTAL2OKFV. Ksh 60 sent to PETER WANYOIKE 721613229 on 10/08/26 at 05:19 AM.
  Fee: Ksh 0. Bal: Ksh 550.59. MPESA ID: UHAPB23UN4
"""
from __future__ import annotations

import re

from app.models.transaction import Category, Confidence, Direction, Provider, TransactionType
from app.parsers.base import BaseParser, ParsedTransaction, RawSms

_AMOUNT_RE = r"Ksh\s?([\d,]+(?:\.\d{1,2})?)"
_TXN_ID_RE = re.compile(
    r"(?:Transaction ID|MPESA ID|Txn(?: ID)?)\s*[:\-]?\s*([A-Z0-9]{6,20})",
    re.IGNORECASE,
)
_LEADING_CODE_RE = re.compile(r"^([A-Z0-9]{8,14})\.")
# 07XXXXXXXX, 7XXXXXXXX, +2547XXXXXXXX, 2547XXXXXXXX
_PHONE_RE = re.compile(r"(?:\+?254|0)?(7\d{8})")


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _extract_txn_id(body: str) -> str | None:
    m = _TXN_ID_RE.search(body)
    if m:
        return m.group(1)
    m = _LEADING_CODE_RE.match(body.strip())
    if m:
        return m.group(1)
    return None


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9 and digits.startswith("7"):
        return "0" + digits
    if len(digits) == 12 and digits.startswith("254"):
        return "0" + digits[3:]
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    return raw


class AirtelMoneyParser(BaseParser):
    provider = Provider.AIRTEL_MONEY

    def parse(self, sms: RawSms) -> ParsedTransaction:
        body = sms.body.strip()
        if not body:
            return self.unknown(sms, reason="empty message body")

        transaction_id = _extract_txn_id(body)

        for handler in (
            self._try_withdrawal,
            self._try_deposit,
            self._try_bundle,
            self._try_airtime,
            self._try_payment,
            self._try_sent,
            self._try_received,
            self._try_compact_sent,
            self._try_compact_received,
        ):
            result = handler(body, transaction_id)
            if result is not None:
                return result

        return self.unknown(sms, reason="no recognized Airtel Money transaction pattern")

    def _balance(self, body: str) -> float | None:
        # Classic "Balance: Ksh…" and compact "Bal: Ksh…"
        return _to_float(
            _first_match(r"(?:Balance|Bal)\s*[:\-]?\s*" + _AMOUNT_RE, body)
        )

    def _fee(self, body: str) -> float | None:
        return _to_float(_first_match(r"Fee\s*[:\-]?\s*" + _AMOUNT_RE, body))

    def _try_withdrawal(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "withdrawn" not in body.lower():
            return None
        amount = _to_float(_first_match(r"withdrawn\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"from\s+Agent\s+([A-Za-z0-9]+)", body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.WITHDRAWAL,
            category=Category.WITHDRAWAL,
            confidence=confidence,
            amount=amount,
            fee=self._fee(body),
            balance=self._balance(body),
            counterparty=f"Airtel Agent {counterparty}" if counterparty else "Airtel Money Agent",
            transaction_id=transaction_id,
        )

    def _try_deposit(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "deposited" not in body.lower():
            return None
        amount = _to_float(_first_match(r"deposited\s+" + _AMOUNT_RE, body))
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.DEPOSIT,
            category=Category.DEPOSIT,
            confidence=confidence,
            amount=amount,
            balance=self._balance(body),
            counterparty="Airtel Money Agent",
            transaction_id=transaction_id,
        )

    def _try_bundle(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if not re.search(r"purchased\s+(?:Internet\s+)?Bundle", body, re.IGNORECASE):
            return None
        amount = _to_float(_first_match(r"worth\s+" + _AMOUNT_RE, body))
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.BUNDLE,
            category=Category.BUNDLE,
            confidence=confidence,
            amount=amount,
            balance=self._balance(body),
            counterparty="Airtel Bundle",
            transaction_id=transaction_id,
        )

    def _try_airtime(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if not re.search(r"purchased\s+Airtime", body, re.IGNORECASE):
            return None
        amount = _to_float(_first_match(r"worth\s+" + _AMOUNT_RE, body))
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.AIRTIME,
            category=Category.AIRTIME,
            confidence=confidence,
            amount=amount,
            balance=self._balance(body),
            counterparty="Airtel Airtime",
            transaction_id=transaction_id,
        )

    def _try_payment(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if not body.lower().startswith("payment of"):
            return None
        amount = _to_float(_first_match(r"Payment of\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"to\s+([A-Za-z0-9 .]+?)\s+successful", body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.PAYMENT,
            category=Category.PAYMENT,
            confidence=confidence,
            amount=amount,
            fee=self._fee(body),
            balance=self._balance(body),
            counterparty=counterparty.strip() if counterparty else None,
            transaction_id=transaction_id,
        )

    def _try_sent(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "you have sent" not in body.lower():
            return None
        amount = _to_float(_first_match(r"sent\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"to\s+([A-Za-z0-9 .]+?)\s*\(", body)
        phone_match = _PHONE_RE.search(body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.SENT,
            category=Category.TRANSFER,
            confidence=confidence,
            amount=amount,
            fee=self._fee(body),
            balance=self._balance(body),
            counterparty=counterparty.strip() if counterparty else None,
            counterparty_phone=_normalize_phone(phone_match.group(0) if phone_match else None),
            transaction_id=transaction_id,
        )

    def _try_received(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "you have received" not in body.lower():
            return None
        amount = _to_float(_first_match(r"received\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"from\s+([A-Za-z0-9 .]+?)\s*\(", body)
        phone_match = _PHONE_RE.search(body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.RECEIVED,
            category=Category.TRANSFER,
            confidence=confidence,
            amount=amount,
            balance=self._balance(body),
            counterparty=counterparty.strip() if counterparty else None,
            counterparty_phone=_normalize_phone(phone_match.group(0) if phone_match else None),
            transaction_id=transaction_id,
        )

    def _try_compact_sent(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        """Compact: 'CODE. Ksh 60 sent to NAME 7216… on DATE. Fee: … Bal: …'"""
        lowered = body.lower()
        if " sent to " not in lowered:
            return None
        if "you have sent" in lowered:
            return None  # handled by classic path

        amount = _to_float(_first_match(_AMOUNT_RE + r"\s+sent to", body))
        # NAME then phone then "on"
        counterparty = _first_match(
            r"sent to\s+([A-Za-z][A-Za-z0-9 .]*?)\s+(?:\+?254|0)?7\d{8}\s+on",
            body,
        )
        if not counterparty:
            counterparty = _first_match(r"sent to\s+([A-Za-z][A-Za-z0-9 .]*?)\s+on", body)
        phone_match = _PHONE_RE.search(body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.SENT,
            category=Category.TRANSFER,
            confidence=confidence,
            amount=amount,
            fee=self._fee(body),
            balance=self._balance(body),
            counterparty=counterparty.strip() if counterparty else None,
            counterparty_phone=_normalize_phone(phone_match.group(0) if phone_match else None),
            transaction_id=transaction_id,
        )

    def _try_compact_received(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        """Compact receive: 'CODE. Ksh 60 received from NAME …'"""
        lowered = body.lower()
        if " received from " not in lowered and not re.search(
            r"received\s+" + _AMOUNT_RE, body, re.IGNORECASE
        ):
            return None
        if "you have received" in lowered:
            return None

        amount = _to_float(_first_match(r"received\s+" + _AMOUNT_RE, body))
        if amount is None:
            amount = _to_float(_first_match(_AMOUNT_RE + r"\s+received from", body))
        counterparty = _first_match(
            r"from\s+([A-Za-z][A-Za-z0-9 .]*?)\s+(?:\+?254|0)?7\d{8}",
            body,
        )
        if not counterparty:
            counterparty = _first_match(r"from\s+([A-Za-z][A-Za-z0-9 .]*?)\s+on", body)
        phone_match = _PHONE_RE.search(body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.RECEIVED,
            category=Category.TRANSFER,
            confidence=confidence,
            amount=amount,
            balance=self._balance(body),
            counterparty=counterparty.strip() if counterparty else None,
            counterparty_phone=_normalize_phone(phone_match.group(0) if phone_match else None),
            transaction_id=transaction_id,
        )
