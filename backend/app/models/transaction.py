"""ORM model for a parsed financial transaction."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Direction(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class TransactionType(str, enum.Enum):
    RECEIVED = "received"
    SENT = "sent"
    PAYMENT = "payment"
    BUNDLE = "bundle"
    AIRTIME = "airtime"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    REVERSAL = "reversal"
    OTHER = "other"


class Category(str, enum.Enum):
    TRANSFER = "transfer"
    BUNDLE = "bundle"
    AIRTIME = "airtime"
    PAYMENT = "payment"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    OTHER = "other"


class Confidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    UNKNOWN = "UNKNOWN"


class Provider(str, enum.Enum):
    MPESA = "mpesa"
    AIRTEL_MONEY = "airtel_money"
    UNKNOWN = "unknown"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(Base):
    """A single financial transaction parsed from an SMS message.

    `amount`, `fee`, and `balance` are always stored as independent,
    separately-extracted fields — never derived from one another. See
    parsers/base.py for the extraction contract.

    In cloud multi-user mode each transaction belongs to a user.
    `user_id` is nullable so local-first / demo mode continues to work
    without requiring authentication.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        # Same SMS fingerprint can exist for different users, but never twice
        # for the same user. When user_id is NULL (local/demo), SQLite treats
        # multiple NULLs as distinct, which preserves prior single-user behaviour.
        UniqueConstraint("user_id", "source_sms_hash", name="uq_user_sms_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    provider: Mapped[str] = mapped_column(Enum(Provider), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(Enum(Direction), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(Enum(TransactionType), nullable=False, index=True)
    category: Mapped[str] = mapped_column(Enum(Category), nullable=False, index=True)

    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)

    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="KES")

    confidence: Mapped[str] = mapped_column(Enum(Confidence), nullable=False, index=True)

    # Deterministic fingerprint of (sender + timestamp + body). Uniqueness is
    # enforced per-user via the composite UniqueConstraint above.
    source_sms_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    user = relationship("User", back_populates="transactions")
