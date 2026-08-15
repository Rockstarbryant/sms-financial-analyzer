"""Real SMS sync endpoint: retrieves device SMS via Termux:API and runs
them through the exact same parsing pipeline demo mode uses.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.user import User
from app.schemas.transaction import DemoImportResponse
from app.services.parsing_pipeline import process_messages
from app.services.termux_sms import (
    SmsPermissionDeniedError,
    TermuxApiUnavailableError,
    list_device_sms,
)

router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync", response_model=DemoImportResponse)
def sync_sms(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> DemoImportResponse:
    """Pull SMS from the device via Termux:API and import recognized transactions.

    When signed in, new rows belong to that user. Local/demo mode keeps user_id NULL.
    """
    try:
        messages = list_device_sms()
    except SmsPermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TermuxApiUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    user_id = current_user.id if current_user is not None else None
    stats = process_messages(db, messages, user_id=user_id)
    return DemoImportResponse(**stats.as_dict())
