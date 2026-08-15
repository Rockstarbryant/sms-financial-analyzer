"""Orchestrates provider detection, parsing, and safe transaction insertion.

This is the single pipeline used by demo-mode import, local Termux SMS sync,
and the cloud companion-app sync — so behaviour (dedup, confidence filtering,
error containment) stays identical no matter where the raw SMS came from.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.transaction import Confidence, Provider, Transaction
from app.parsers.airtel_money import AirtelMoneyParser
from app.parsers.base import BaseParser, RawSms
from app.parsers.provider_config import detect_provider
from app.utils.hashing import sms_fingerprint
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PARSERS: dict[Provider, BaseParser] = {
    Provider.MPESA: __import__(
        "app.parsers.mpesa", fromlist=["MpesaParser"]
    ).MpesaParser(),
    Provider.AIRTEL_MONEY: AirtelMoneyParser(),
}


@dataclass
class ImportStats:
    scanned: int = 0
    recognized: int = 0
    inserted: int = 0
    duplicates: int = 0
    unknown: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "recognized": self.recognized,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "unknown": self.unknown,
        }


def process_messages(
    db: Session,
    messages: list[RawSms],
    user_id: int | None = None,
) -> ImportStats:
    """Parse and insert a batch of raw SMS messages, skipping duplicates.

    When `user_id` is provided (cloud mode), transactions are owned by that
    user and deduplication is scoped to that user. When `user_id` is None
    (local/demo mode), behaviour matches the original single-user design.

    Never raises on a single malformed message — any per-message failure
    is caught, counted as unknown, and logged (without PII), so one bad
    message can never abort the whole batch.
    """
    stats = ImportStats()

    for sms in messages:
        stats.scanned += 1
        try:
            provider = detect_provider(sms.sender)
            parser = _PARSERS.get(provider)

            if parser is None:
                stats.unknown += 1
                continue

            parsed = parser.parse(sms)

            if parsed.confidence == Confidence.UNKNOWN or parsed.amount is None:
                stats.unknown += 1
                continue

            # Recognized: parser confidently identified this as a real
            # transaction. Whether it becomes a new row or a duplicate is
            # decided next, but it counts as "recognized" either way.
            stats.recognized += 1

            fingerprint = sms_fingerprint(sms.sender, sms.timestamp.isoformat(), sms.body)

            existing_query = db.query(Transaction.id).filter(
                Transaction.source_sms_hash == fingerprint
            )
            if user_id is not None:
                existing_query = existing_query.filter(Transaction.user_id == user_id)
            else:
                existing_query = existing_query.filter(Transaction.user_id.is_(None))

            if existing_query.first() is not None:
                stats.duplicates += 1
                continue

            transaction = Transaction(
                user_id=user_id,
                provider=parsed.provider,
                direction=parsed.direction,
                transaction_type=parsed.transaction_type,
                category=parsed.category,
                amount=parsed.amount,
                fee=parsed.fee,
                balance=parsed.balance,
                counterparty=parsed.counterparty,
                counterparty_phone=parsed.counterparty_phone,
                transaction_id=parsed.transaction_id,
                timestamp=sms.timestamp,
                currency=parsed.currency,
                confidence=parsed.confidence,
                source_sms_hash=fingerprint,
            )
            db.add(transaction)
            db.commit()
            stats.inserted += 1

        except Exception:  # noqa: BLE001 - deliberate: one bad message must not abort the batch
            db.rollback()
            stats.unknown += 1
            logger.warning("Failed to process an SMS message; skipping. count=%s", stats.scanned)
            continue

    return stats
