"""Demo-mode endpoints: import synthetic sample data through the real pipeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.user import User
from app.schemas.transaction import DemoImportResponse
from app.services.demo_data import load_demo_messages
from app.services.parsing_pipeline import process_messages

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/import", response_model=DemoImportResponse)
def import_demo_data(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> DemoImportResponse:
    """Import the synthetic sample_data fixtures.

    When a JWT is present, transactions are owned by that user so they show
    up in the signed-in dashboard. Without auth, rows stay local (user_id NULL).
    """
    messages = load_demo_messages()
    user_id = current_user.id if current_user is not None else None
    stats = process_messages(db, messages, user_id=user_id)
    return DemoImportResponse(**stats.as_dict())
