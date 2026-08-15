"""Pydantic schemas for API request/response bodies."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransactionRead(BaseModel):
    """A transaction as returned by the API. Never includes raw SMS body."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    direction: str
    transaction_type: str
    category: str
    amount: float | None
    fee: float | None
    balance: float | None
    counterparty: str | None
    counterparty_phone: str | None
    transaction_id: str | None
    timestamp: datetime
    currency: str
    confidence: str
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    limit: int
    offset: int


class DemoImportResponse(BaseModel):
    scanned: int
    recognized: int
    inserted: int
    duplicates: int
    unknown: int


class DashboardResponse(BaseModel):
    total_balance: float | None
    money_in: float
    money_out: float
    fees: float
    net_cash_flow: float
    providers: dict[str, "ProviderSummary"]


class ProviderSummary(BaseModel):
    money_in: float
    money_out: float
    fees: float
    net_flow: float


class CategoryBreakdownItem(BaseModel):
    category: str
    total_in: float
    total_out: float
    count: int


class ProviderBreakdownItem(BaseModel):
    provider: str
    total_in: float
    total_out: float
    fees: float
    count: int


class MonthlyBreakdownItem(BaseModel):
    month: str  # YYYY-MM
    income: float
    spending: float
    fees: float
    net: float


class CounterpartySummary(BaseModel):
    counterparty: str
    money_sent: float
    money_received: float
    transaction_count: int
    net_flow: float


DashboardResponse.model_rebuild()
