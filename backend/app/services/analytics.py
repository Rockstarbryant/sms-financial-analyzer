"""Analytics queries over stored transactions.

All calculations here operate only on rows already in the transactions
table -- rows with confidence=UNKNOWN are never inserted by the parsing
pipeline in the first place (see services/parsing_pipeline.py), so nothing
here needs to re-filter for that; it's structurally excluded upstream.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Direction, Provider, Transaction


def _user_filter(query, user_id: int | None):
    """Apply user scoping. None means local/demo rows (user_id IS NULL)."""
    if user_id is not None:
        return query.filter(Transaction.user_id == user_id)
    return query.filter(Transaction.user_id.is_(None))


def dashboard_summary(db: Session, user_id: int | None = None) -> dict:
    money_in = _sum(db, Direction.IN, user_id=user_id)
    money_out = _sum(db, Direction.OUT, user_id=user_id)

    fees_q = db.query(func.coalesce(func.sum(Transaction.fee), 0.0))
    fees_q = _user_filter(fees_q, user_id)
    fees = fees_q.scalar() or 0.0

    balance_q = (
        db.query(Transaction.balance)
        .filter(Transaction.balance.isnot(None))
        .order_by(Transaction.timestamp.desc())
    )
    balance_q = _user_filter(balance_q, user_id)
    latest_balance_row = balance_q.first()
    total_balance = latest_balance_row[0] if latest_balance_row else None

    providers = {}
    for provider in Provider:
        if provider == Provider.UNKNOWN:
            continue
        p_in = _sum(db, Direction.IN, provider=provider, user_id=user_id)
        p_out = _sum(db, Direction.OUT, provider=provider, user_id=user_id)
        p_fees_q = (
            db.query(func.coalesce(func.sum(Transaction.fee), 0.0))
            .filter(Transaction.provider == provider)
        )
        p_fees_q = _user_filter(p_fees_q, user_id)
        p_fees = p_fees_q.scalar() or 0.0
        providers[provider.value] = {
            "money_in": p_in,
            "money_out": p_out,
            "fees": p_fees,
            "net_flow": p_in - p_out,
        }

    return {
        "total_balance": total_balance,
        "money_in": money_in,
        "money_out": money_out,
        "fees": fees,
        "net_cash_flow": money_in - money_out,
        "providers": providers,
    }


def _sum(
    db: Session,
    direction: Direction,
    provider: Provider | None = None,
    user_id: int | None = None,
) -> float:
    query = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
        Transaction.direction == direction
    )
    if provider is not None:
        query = query.filter(Transaction.provider == provider)
    query = _user_filter(query, user_id)
    return query.scalar() or 0.0


def category_breakdown(db: Session, user_id: int | None = None) -> list[dict]:
    query = db.query(
        Transaction.category,
        Transaction.direction,
        func.coalesce(func.sum(Transaction.amount), 0.0),
        func.count(Transaction.id),
    )
    query = _user_filter(query, user_id)
    rows = query.group_by(Transaction.category, Transaction.direction).all()

    by_category: dict[str, dict] = defaultdict(lambda: {"total_in": 0.0, "total_out": 0.0, "count": 0})
    for category, direction, total, count in rows:
        key = by_category[category.value if hasattr(category, "value") else category]
        if direction == Direction.IN or direction == Direction.IN.value:
            key["total_in"] += total
        else:
            key["total_out"] += total
        key["count"] += count

    return [
        {"category": category, **values}
        for category, values in sorted(by_category.items())
    ]


def provider_breakdown(db: Session, user_id: int | None = None) -> list[dict]:
    result = []
    for provider in Provider:
        if provider == Provider.UNKNOWN:
            continue
        total_in = _sum(db, Direction.IN, provider=provider, user_id=user_id)
        total_out = _sum(db, Direction.OUT, provider=provider, user_id=user_id)
        fees_q = (
            db.query(func.coalesce(func.sum(Transaction.fee), 0.0))
            .filter(Transaction.provider == provider)
        )
        fees_q = _user_filter(fees_q, user_id)
        fees = fees_q.scalar() or 0.0
        count_q = db.query(func.count(Transaction.id)).filter(Transaction.provider == provider)
        count_q = _user_filter(count_q, user_id)
        count = count_q.scalar() or 0
        if count == 0:
            continue
        result.append(
            {
                "provider": provider.value,
                "total_in": total_in,
                "total_out": total_out,
                "fees": fees,
                "count": count,
            }
        )
    return result


def monthly_breakdown(db: Session, user_id: int | None = None) -> list[dict]:
    query = db.query(
        Transaction.timestamp, Transaction.direction, Transaction.amount, Transaction.fee
    )
    query = _user_filter(query, user_id)
    rows = query.all()

    by_month: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "spending": 0.0, "fees": 0.0})
    for timestamp, direction, amount, fee in rows:
        month_key = timestamp.strftime("%Y-%m")
        entry = by_month[month_key]
        direction_value = direction.value if hasattr(direction, "value") else direction
        if direction_value == Direction.IN.value:
            entry["income"] += amount or 0.0
        else:
            entry["spending"] += amount or 0.0
        entry["fees"] += fee or 0.0

    return [
        {
            "month": month,
            "income": values["income"],
            "spending": values["spending"],
            "fees": values["fees"],
            "net": values["income"] - values["spending"],
        }
        for month, values in sorted(by_month.items())
    ]


def _norm_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 12 and digits.startswith("254"):
        digits = "0" + digits[3:]
    if len(digits) == 9 and digits.startswith("7"):
        digits = "0" + digits
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    return None


def _norm_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.strip().split()).title()


def counterparty_breakdown(db: Session, user_id: int | None = None) -> list[dict]:
    """Group people by phone when available, else by normalized name.

    Prevents duplicate rows like "BRIAN OUMA" and "0797***326 brian ouma".
    """
    query = db.query(
        Transaction.counterparty,
        Transaction.counterparty_phone,
        Transaction.direction,
        Transaction.amount,
    ).filter(Transaction.counterparty.isnot(None))
    query = _user_filter(query, user_id)
    rows = query.all()

    # key -> aggregates + display name candidates
    by_key: dict[str, dict] = {}
    for counterparty, phone, direction, amount in rows:
        phone_n = _norm_phone(phone)
        name_n = _norm_name(counterparty)
        key = f"p:{phone_n}" if phone_n else f"n:{name_n.lower()}"
        entry = by_key.get(key)
        if entry is None:
            entry = {
                "money_sent": 0.0,
                "money_received": 0.0,
                "transaction_count": 0,
                "names": {},
                "phone": phone_n,
            }
            by_key[key] = entry
        direction_value = direction.value if hasattr(direction, "value") else direction
        if direction_value == Direction.IN.value:
            entry["money_received"] += amount or 0.0
        else:
            entry["money_sent"] += amount or 0.0
        entry["transaction_count"] += 1
        if name_n:
            entry["names"][name_n] = entry["names"].get(name_n, 0) + 1

    results = []
    for values in by_key.values():
        # Prefer real name over pure phone display
        names = values["names"]
        if names:
            display = max(names.items(), key=lambda x: (x[1], len(x[0])))[0]
        else:
            display = values["phone"] or "Unknown"
        if values["phone"] and not display.startswith("0"):
            # keep name; phone used only for merge key
            pass
        results.append(
            {
                "counterparty": display,
                "money_sent": values["money_sent"],
                "money_received": values["money_received"],
                "transaction_count": values["transaction_count"],
                "net_flow": values["money_received"] - values["money_sent"],
            }
        )
    return sorted(results, key=lambda r: r["counterparty"])


def counterparty_detail(db: Session, name: str, user_id: int | None = None) -> dict | None:
    # Match exact name or same normalized name / related phone rows
    name_n = _norm_name(name)
    query = db.query(Transaction).filter(Transaction.counterparty.isnot(None))
    query = _user_filter(query, user_id)
    all_rows = query.order_by(Transaction.timestamp.desc()).all()
    transactions = [
        t
        for t in all_rows
        if _norm_name(t.counterparty) == name_n
        or (t.counterparty and t.counterparty.strip() == name.strip())
    ]
    # If still empty, try phone-based merge: any txn whose phone matches phones of this name
    if not transactions:
        return None

    phones = {_norm_phone(t.counterparty_phone) for t in transactions}
    phones.discard(None)
    if phones:
        transactions = [
            t
            for t in all_rows
            if _norm_name(t.counterparty) == name_n
            or _norm_phone(t.counterparty_phone) in phones
        ]

    money_sent = sum(t.amount or 0.0 for t in transactions if t.direction == Direction.OUT)
    money_received = sum(t.amount or 0.0 for t in transactions if t.direction == Direction.IN)

    return {
        "counterparty": name_n or name,
        "money_sent": money_sent,
        "money_received": money_received,
        "transaction_count": len(transactions),
        "net_flow": money_received - money_sent,
        "transactions": transactions,
    }
