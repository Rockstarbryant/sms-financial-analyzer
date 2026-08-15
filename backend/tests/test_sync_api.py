"""Tests for POST /api/sync -- mocks device SMS retrieval, uses a real
temp DB via dependency override (same pattern as test_api.py) so the full
pipeline (parse -> dedupe -> insert) is exercised end-to-end.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.parsers.base import RawSms
from app.services.termux_sms import SmsPermissionDeniedError, TermuxApiUnavailableError


def _device_messages() -> list[RawSms]:
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
            sender="RandomPromo",
            body="Win a free prize today!",
            timestamp=datetime(2026, 8, 1, 9, 20, 0),
        ),
    ]


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    from app.models import transaction  # noqa: F401

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db() -> Generator:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
    os.remove(path)


def test_sync_success(client):
    with patch("app.api.sync.list_device_sms", return_value=_device_messages()):
        response = client.post("/api/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["scanned"] == 2
    assert body["inserted"] == 1
    assert body["unknown"] == 1


def test_sync_is_idempotent_no_duplicates_on_repeat(client):
    with patch("app.api.sync.list_device_sms", return_value=_device_messages()):
        first = client.post("/api/sync").json()
        second = client.post("/api/sync").json()
    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["duplicates"] == 1


def test_sync_ten_times_creates_no_duplicates(client):
    with patch("app.api.sync.list_device_sms", return_value=_device_messages()):
        for _ in range(10):
            client.post("/api/sync")
        final = client.post("/api/sync").json()
    assert final["duplicates"] == 1  # only 1 recognized txn total, always a dup after the first


def test_sync_response_never_contains_sms_body(client):
    with patch("app.api.sync.list_device_sms", return_value=_device_messages()):
        response = client.post("/api/sync")
    assert "sent to JOHN KAMAU" not in response.text
    assert "body" not in response.json()


def test_sync_termux_api_unavailable_returns_503(client):
    with patch(
        "app.api.sync.list_device_sms",
        side_effect=TermuxApiUnavailableError("Termux:API is not available."),
    ):
        response = client.post("/api/sync")
    assert response.status_code == 503
    assert "Termux:API" in response.json()["detail"]


def test_sync_permission_denied_returns_403(client):
    with patch(
        "app.api.sync.list_device_sms",
        side_effect=SmsPermissionDeniedError("SMS permission was denied."),
    ):
        response = client.post("/api/sync")
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()
