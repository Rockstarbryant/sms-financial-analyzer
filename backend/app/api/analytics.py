"""Dashboard and analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.user import User
from app.schemas.transaction import (
    CategoryBreakdownItem,
    CounterpartySummary,
    DashboardResponse,
    MonthlyBreakdownItem,
    ProviderBreakdownItem,
    TransactionRead,
)
from app.services import analytics

router = APIRouter(prefix="/api", tags=["analytics"])


def _uid(user: User | None) -> int | None:
    return user.id if user is not None else None


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> DashboardResponse:
    return DashboardResponse(**analytics.dashboard_summary(db, user_id=_uid(current_user)))


@router.get("/analytics/categories", response_model=list[CategoryBreakdownItem])
def get_category_breakdown(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CategoryBreakdownItem]:
    return [
        CategoryBreakdownItem(**item)
        for item in analytics.category_breakdown(db, user_id=_uid(current_user))
    ]


@router.get("/analytics/providers", response_model=list[ProviderBreakdownItem])
def get_provider_breakdown(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[ProviderBreakdownItem]:
    return [
        ProviderBreakdownItem(**item)
        for item in analytics.provider_breakdown(db, user_id=_uid(current_user))
    ]


@router.get("/analytics/monthly", response_model=list[MonthlyBreakdownItem])
def get_monthly_breakdown(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[MonthlyBreakdownItem]:
    return [
        MonthlyBreakdownItem(**item)
        for item in analytics.monthly_breakdown(db, user_id=_uid(current_user))
    ]


@router.get("/analytics/counterparties", response_model=list[CounterpartySummary])
def get_counterparty_breakdown(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CounterpartySummary]:
    return [
        CounterpartySummary(**item)
        for item in analytics.counterparty_breakdown(db, user_id=_uid(current_user))
    ]


@router.get("/counterparties", response_model=list[CounterpartySummary])
def list_counterparties(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CounterpartySummary]:
    return [
        CounterpartySummary(**item)
        for item in analytics.counterparty_breakdown(db, user_id=_uid(current_user))
    ]


@router.get("/counterparties/{name}")
def get_counterparty(
    name: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    detail = analytics.counterparty_detail(db, name, user_id=_uid(current_user))
    if detail is None:
        raise HTTPException(status_code=404, detail="Counterparty not found")
    return {
        "counterparty": detail["counterparty"],
        "money_sent": detail["money_sent"],
        "money_received": detail["money_received"],
        "transaction_count": detail["transaction_count"],
        "net_flow": detail["net_flow"],
        "transactions": [TransactionRead.model_validate(t) for t in detail["transactions"]],
    }
