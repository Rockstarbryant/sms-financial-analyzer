"""Transaction listing and detail endpoints. Never exposes raw SMS bodies."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionListResponse, TransactionRead

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _base_query(db: Session, user: User | None):
    """Scope queries to the authenticated user when present.

    Unauthenticated requests (local/demo mode) only see rows with no user_id.
    """
    query = db.query(Transaction)
    if user is not None:
        query = query.filter(Transaction.user_id == user.id)
    else:
        query = query.filter(Transaction.user_id.is_(None))
    return query


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    provider: str | None = None,
    category: str | None = None,
    direction: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> TransactionListResponse:
    query = _base_query(db, current_user)

    if provider:
        query = query.filter(Transaction.provider == provider)
    if category:
        query = query.filter(Transaction.category == category)
    if direction:
        query = query.filter(Transaction.direction == direction)
    if start_date:
        query = query.filter(Transaction.timestamp >= start_date)
    if end_date:
        query = query.filter(Transaction.timestamp <= end_date)
    if search:
        like = f"%{search}%"
        query = query.filter(Transaction.counterparty.ilike(like))

    total = query.count()
    items = (
        query.order_by(Transaction.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return TransactionListResponse(
        items=[TransactionRead.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> TransactionRead:
    query = _base_query(db, current_user).filter(Transaction.id == transaction_id)
    transaction = query.first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionRead.model_validate(transaction)
