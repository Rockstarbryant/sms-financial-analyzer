"""M-Pesa SMS parser.

Handles the family of message formats Safaricom M-Pesa sends for sent,
received, payment, bundle, airtime, withdrawal, deposit, and reversal
transactions. Amount, fee, and balance are always extracted as independent
values -- never inferred from one another.
"""
from __future__ import annotations

import re

from app.models.transaction import Category, Confidence, Direction, Provider, TransactionType
from app.parsers.base import BaseParser, ParsedTransaction, RawSms

_AMOUNT_RE = r"Ksh\s?([\d,]+(?:\.\d{1,2})?)"
_TXN_ID_RE = re.compile(r"^([A-Z0-9]{6,12})\s+Confirmed", re.IGNORECASE)
_PHONE_RE = re.compile(r"(0\d{9}|\+?254\d{9})")


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


class MpesaParser(BaseParser):
    provider = Provider.MPESA

    def parse(self, sms: RawSms) -> ParsedTransaction:
        body = sms.body.strip()
        if not body:
            return self.unknown(sms, reason="empty message body")

        transaction_id = None
        txn_match = _TXN_ID_RE.match(body)
        if txn_match:
            transaction_id = txn_match.group(1)

        for handler in (
            self._try_reversal,
            self._try_withdrawal,
            self._try_deposit,
            self._try_bundle_or_sent_payment,
            self._try_received,
            self._try_airtime,
        ):
            result = handler(body, transaction_id)
            if result is not None:
                return result

        return self.unknown(sms, reason="no recognized M-Pesa transaction pattern")

    # -- individual pattern handlers -------------------------------------------------

    def _try_reversal(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "reversed" not in body.lower():
            return None
        amount = _to_float(_first_match(rf"{_AMOUNT_RE}\s+sent", body))
        balance = _to_float(_first_match(r"balance is (?:now\s+)?" + _AMOUNT_RE, body))
        counterparty = _first_match(r"sent to ([A-Za-z ]+?) has been reversed", body)
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.REVERSAL,
            category=Category.OTHER,
            confidence=Confidence.HIGH if amount is not None else Confidence.MEDIUM,
            amount=amount,
            balance=balance,
            counterparty=counterparty.strip() if counterparty else None,
            transaction_id=transaction_id,
        )

    def _try_withdrawal(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "withdrawn" not in body.lower():
            return None
        amount = _to_float(_first_match(rf"{_AMOUNT_RE}\s+withdrawn", body))
        fee = _to_float(_first_match(r"[Ww]ithdrawal charge\s+" + _AMOUNT_RE, body))
        balance = _to_float(_first_match(r"balance is\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"from\s+Agent\s+\d+\s*-?\s*([A-Za-z0-9 ]+?)\s+on", body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.WITHDRAWAL,
            category=Category.WITHDRAWAL,
            confidence=confidence,
            amount=amount,
            fee=fee,
            balance=balance,
            counterparty=counterparty.strip() if counterparty else "M-PESA Agent",
            transaction_id=transaction_id,
        )

    def _try_deposit(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "deposited" not in body.lower():
            return None
        amount = _to_float(_first_match(rf"{_AMOUNT_RE}\s+deposited", body))
        balance = _to_float(_first_match(r"balance is\s+" + _AMOUNT_RE, body))
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.DEPOSIT,
            category=Category.DEPOSIT,
            confidence=confidence,
            amount=amount,
            balance=balance,
            counterparty="M-PESA Agent",
            transaction_id=transaction_id,
        )

    def _try_bundle_or_sent_payment(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        lowered = body.lower()
        is_sent = " sent to " in lowered
        is_paid = " paid to " in lowered
        if not (is_sent or is_paid):
            return None

        amount = _to_float(_first_match(_AMOUNT_RE + r"\s+(?:sent|paid) to", body))
        fee = _to_float(_first_match(r"[Tt]ransaction cost,?\s*" + _AMOUNT_RE, body))
        balance = _to_float(_first_match(r"balance is\s+" + _AMOUNT_RE, body))

        counterparty = None
        if is_sent:
            counterparty = _first_match(r"sent to\s+([A-Za-z0-9 .]+?)\s+(?:on|for)", body)
        else:
            counterparty = _first_match(r"paid to\s+([A-Za-z0-9 .]+?)\s+on", body)

        counterparty_clean, counterparty_phone = _split_name_and_phone(counterparty)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM

        # Contextual bundle detection: only classify as a bundle when the
        # counterparty name itself indicates a bundle/data purchase -- not
        # merely because the word "data" appears somewhere in the body.
        if counterparty_clean and re.search(r"\bBUNDLE", counterparty_clean, re.IGNORECASE):
            return ParsedTransaction(
                provider=self.provider,
                direction=Direction.OUT,
                transaction_type=TransactionType.BUNDLE,
                category=Category.BUNDLE,
                confidence=confidence,
                amount=amount,
                fee=fee,
                balance=balance,
                counterparty=counterparty_clean,
                transaction_id=transaction_id,
            )

        if is_sent:
            return ParsedTransaction(
                provider=self.provider,
                direction=Direction.OUT,
                transaction_type=TransactionType.SENT,
                category=Category.TRANSFER,
                confidence=confidence,
                amount=amount,
                fee=fee,
                balance=balance,
                counterparty=counterparty_clean,
                counterparty_phone=counterparty_phone,
                transaction_id=transaction_id,
            )

        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.PAYMENT,
            category=Category.PAYMENT,
            confidence=confidence,
            amount=amount,
            fee=fee,
            balance=balance,
            counterparty=counterparty_clean,
            counterparty_phone=counterparty_phone,
            transaction_id=transaction_id,
        )

    def _try_received(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "received" not in body.lower():
            return None
        amount = _to_float(_first_match(r"received\s+" + _AMOUNT_RE, body))
        balance = _to_float(_first_match(r"balance is\s+" + _AMOUNT_RE, body))
        counterparty = _first_match(r"from\s+([A-Za-z0-9 .]+?)\s+0\d{9}", body)
        if not counterparty:
            counterparty = _first_match(r"from\s+([A-Za-z0-9 .]+?)\s+on", body)
        phone_match = _PHONE_RE.search(body)
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.IN,
            transaction_type=TransactionType.RECEIVED,
            category=Category.TRANSFER,
            confidence=confidence,
            amount=amount,
            balance=balance,
            counterparty=counterparty.strip() if counterparty else None,
            counterparty_phone=phone_match.group(1) if phone_match else None,
            transaction_id=transaction_id,
        )

    def _try_airtime(self, body: str, transaction_id: str | None) -> ParsedTransaction | None:
        if "airtime" not in body.lower():
            return None
        amount = _to_float(_first_match(r"bought\s+" + _AMOUNT_RE + r"\s+of airtime", body))
        balance = _to_float(_first_match(r"balance is\s+" + _AMOUNT_RE, body))
        confidence = Confidence.HIGH if amount is not None else Confidence.MEDIUM
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.AIRTIME,
            category=Category.AIRTIME,
            confidence=confidence,
            amount=amount,
            balance=balance,
            counterparty="Safaricom Airtime",
            transaction_id=transaction_id,
        )


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _split_name_and_phone(raw: str | None) -> tuple[str | None, str | None]:
    """Split a captured 'NAME 0722XXXXXX' fragment into name and phone.

    Counterparty capture groups sometimes greedily include a trailing
    phone number since M-Pesa often writes "sent to NAME 0722XXXXXX on...".
    Keeping name and phone as independent fields (matching the counterparty
    vs counterparty_phone schema) instead of leaving the digits glued onto
    the name.
    """
    if raw is None:
        return None, None
    raw = raw.strip()
    phone_match = _PHONE_RE.search(raw)
    if not phone_match:
        return raw, None
    phone = phone_match.group(1)
    name = raw.replace(phone, "").strip()
    return (name or None), phone
