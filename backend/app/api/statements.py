"""Upload and parse M-Pesa / Airtel Money PDF statements."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import DemoImportResponse
from app.services.statement_pdf import parse_statement
from app.services.parsing_pipeline import ImportStats

router = APIRouter(prefix="/api/statements", tags=["statements"])

MAX_PDF_BYTES = 15 * 1024 * 1024  # 15 MB


@router.post("/upload", response_model=DemoImportResponse)
async def upload_statement(
    file: UploadFile = File(...),
    provider: str = Form(...),
    password: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> DemoImportResponse:
    """Parse a password-protected (or open) statement PDF into transactions.

    When signed in, rows are owned by the current user. SMS is not used.
    Safe to re-upload — duplicate receipt fingerprints are skipped.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF is too large (max 15 MB).")

    try:
        rows = parse_statement(data, provider=provider, password=password or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}",
        ) from exc

    if not rows:
        raise HTTPException(
            status_code=422,
            detail=(
                "No transactions found in this PDF. "
                "Confirm the provider (M-Pesa / Airtel), password, and that the file is a full statement."
            ),
        )

    user_id = current_user.id if current_user is not None else None
    stats = ImportStats(scanned=len(rows))

    for row in rows:
        stats.recognized += 1
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.source_sms_hash == row.source_hash,
                Transaction.user_id == user_id,
            )
            .first()
        )
        if existing:
            stats.duplicates += 1
            continue

        db.add(
            Transaction(
                user_id=user_id,
                provider=row.provider,
                direction=row.direction,
                transaction_type=row.transaction_type,
                category=row.category,
                amount=row.amount,
                fee=row.fee,
                balance=row.balance,
                counterparty=row.counterparty,
                counterparty_phone=row.counterparty_phone,
                transaction_id=row.transaction_id,
                timestamp=row.timestamp,
                currency="KES",
                confidence=row.confidence,
                source_sms_hash=row.source_hash,
            )
        )
        stats.inserted += 1

    db.commit()
    return DemoImportResponse(**stats.as_dict())
