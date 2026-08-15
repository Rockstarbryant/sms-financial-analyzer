"""Base parser interface shared by all provider-specific parsers.

Design note: this is deliberately a plain abstract interface so a future
AIParser (see project notes) could implement the same contract without any
change to the pipeline that calls parsers. The core system never requires
AI and must work fully offline with deterministic parsing only.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.transaction import Category, Confidence, Direction, Provider, TransactionType


@dataclass
class ParsedTransaction:
    """Result of parsing a single SMS message.

    amount, fee, and balance are independent optional fields -- a parser
    must never fall back to using balance as amount, or vice versa. If a
    field cannot be confidently extracted, leave it as None rather than
    guessing.
    """

    provider: Provider
    direction: Direction
    transaction_type: TransactionType
    category: Category
    confidence: Confidence

    amount: float | None = None
    fee: float | None = None
    balance: float | None = None

    counterparty: str | None = None
    counterparty_phone: str | None = None
    transaction_id: str | None = None
    currency: str = "KES"

    # Populated by the parser only when it is confident this message is a
    # promotional/ambiguous/balance-only message rather than a real
    # transaction. Purely informational -- confidence=UNKNOWN already
    # signals this should be excluded from totals.
    reason: str | None = None


@dataclass
class RawSms:
    """A single raw SMS message as retrieved from the device (or fixtures)."""

    sender: str
    body: str
    timestamp: datetime


class BaseParser(ABC):
    """Interface every provider-specific parser must implement."""

    provider: Provider

    @abstractmethod
    def parse(self, sms: RawSms) -> ParsedTransaction:
        """Parse a single raw SMS into a ParsedTransaction.

        Implementations must never raise on malformed/unexpected input --
        instead return a ParsedTransaction with confidence=UNKNOWN and
        amount=None, so the pipeline can safely skip it from totals
        without aborting the whole batch.
        """
        raise NotImplementedError

    def unknown(self, sms: RawSms, reason: str) -> ParsedTransaction:
        """Convenience helper for building a safe UNKNOWN result."""
        return ParsedTransaction(
            provider=self.provider,
            direction=Direction.OUT,
            transaction_type=TransactionType.OTHER,
            category=Category.OTHER,
            confidence=Confidence.UNKNOWN,
            reason=reason,
        )
