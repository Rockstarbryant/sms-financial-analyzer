"""End-to-end API tests using a temporary DB and monkeypatched demo fixtures.

These exercise the real FastAPI app (routes, dependency wiring, pipeline)
rather than calling service functions directly. Uses FastAPI dependency
overrides instead of reloading modules, so the SQLAlchemy declarative Base
and ORM model registration stay stable across the whole test session.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.parsers.base import RawSms


def _demo_messages() -> list[RawSms]:
    return [
        RawSms(
            sender="MPESA",
            body=(
                "QGH7X1A2B1 Confirmed. Ksh20.00 sent to JOHN KAMAU 0722111222 on 1/8/26 at 9:12 AM. "
                "New M-PESA balance is Ksh4,530.00. Transaction cost, Ksh0.00."
            ),
            timestamp=datetime(2026, 8, 1, 9, 12, 0),
        ),
        RawSms(
            sender="MPESA",
            body=(
                "QGH7X1A2B2 Confirmed. You have received Ksh1,500.00 from MARY WANJIRU 0733222333 "
                "on 1/8/26 at 10:05 AM. New M-PESA balance is Ksh6,030.00."
            ),
            timestamp=datetime(2026, 8, 1, 10, 5, 0),
        ),
        RawSms(
            sender="AirtelMoney",
            body="You have sent Ksh200.00 to BRIAN OUMA(0733444555). Transaction ID CI10001A. Fee: Ksh10.00. Balance: Ksh2,300.00.",
            timestamp=datetime(2026, 8, 1, 8, 30, 0),
        ),
    ]


@pytest.fixture()
def client(monkeypatch) -> Generator[TestClient, None, None]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    from app.models import transaction, user  # noqa: F401 - ensure models registered on Base

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db() -> Generator:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Swap in a temp DB and swap demo import to use fully synthetic
    # in-memory fixtures instead of reading sample_data/ from disk.
    app.dependency_overrides[get_db] = override_get_db
    import app.api.demo as demo_api_module

    monkeypatch.setattr(demo_api_module, "load_demo_messages", _demo_messages)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()
    os.remove(path)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_import_and_dashboard(client):
    response = client.post("/api/demo/import")
    assert response.status_code == 200
    body = response.json()
    assert body["scanned"] == 3
    assert body["inserted"] == 3
    assert body["duplicates"] == 0

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["money_in"] == 1500.00
    assert data["money_out"] == 220.00  # 20 sent (mpesa) + 200 sent (airtel)
    assert "mpesa" in data["providers"]
    assert "airtel_money" in data["providers"]


def test_demo_import_is_idempotent(client):
    first = client.post("/api/demo/import").json()
    second = client.post("/api/demo/import").json()
    assert first["inserted"] == 3
    assert second["inserted"] == 0
    assert second["duplicates"] == 3


def test_transactions_listing_excludes_sms_body_field(client):
    client.post("/api/demo/import")
    response = client.get("/api/transactions")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    for item in body["items"]:
        assert "body" not in item
        assert "sms_body" not in item


def test_transaction_detail_not_found(client):
    response = client.get("/api/transactions/9999")
    assert response.status_code == 404


def test_counterparty_breakdown(client):
    client.post("/api/demo/import")
    response = client.get("/api/counterparties")
    assert response.status_code == 200
    names = [c["counterparty"] for c in response.json()]
    assert "JOHN KAMAU" in names
