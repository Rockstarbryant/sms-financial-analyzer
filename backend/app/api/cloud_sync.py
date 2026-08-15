"""Cloud sync endpoint: receives SMS from the Android companion app."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.parsers.base import RawSms
from app.schemas.auth import CloudSyncRequest
from app.schemas.transaction import DemoImportResponse
from app.services.parsing_pipeline import process_messages

router = APIRouter(prefix="/api/v1", tags=["cloud-sync"])


@router.post("/sync", response_model=DemoImportResponse)
def cloud_sync(
    payload: CloudSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DemoImportResponse:
    """Accept a batch of SMS messages from the Android companion app.

    Requires a valid JWT. Messages are run through the exact same parsing
    pipeline used by demo mode and the local Termux sync. Deduplication is
    scoped to the authenticated user.
    """
    messages = [
        RawSms(sender=m.sender, body=m.body, timestamp=m.timestamp)
        for m in payload.messages
    ]
    stats = process_messages(db, messages, user_id=current_user.id)
    return DemoImportResponse(**stats.as_dict())
