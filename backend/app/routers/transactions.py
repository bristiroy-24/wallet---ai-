"""
app/routers/transactions.py
────────────────────────────
Standard CRUD + AI-powered transaction endpoints.

GET  /api/v1/transactions          – filtered list
POST /api/v1/transactions          – manual create
POST /api/v1/transactions/magic-input  – AI natural language parse
POST /api/v1/transactions/scan-receipt – AI multimodal OCR
"""

import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_ai_service, get_current_user_id, get_db
from app.models.transaction import Transaction, TransactionType
from app.repositories.category import CategoryRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.ai import ParsedExpenseSchema
from app.schemas.transaction import (
    MagicInputRequest,
    TransactionCreate,
    TransactionRead,
)
from app.services.ai_base import BaseAIService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_category_names(db: AsyncSession) -> list[str]:
    """Returns flat list of all category names for AI context."""
    repo = CategoryRepository(db)
    cats = await repo.get_all_flat()
    return [c.name for c in cats]


def _txn_to_read(txn: Transaction) -> TransactionRead:
    """Maps ORM Transaction to the API response schema."""
    return TransactionRead(
        id=txn.id,
        user_id=txn.user_id,
        account_id=txn.account_id,
        category_id=txn.category_id,
        amount=txn.amount,
        type=txn.type,
        note=txn.note,
        tags=txn.tags or [],
        date=txn.date,
        created_at=txn.created_at,
        category_name=txn.category.name if txn.category else None,
        account_name=txn.account.name if txn.account else None,
    )


# ── GET /transactions ─────────────────────────────────────────────────────────

@router.get("/", response_model=list[TransactionRead])
async def list_transactions(
    start_date:  datetime | None = Query(default=None),
    end_date:    datetime | None = Query(default=None),
    category_id: UUID | None     = Query(default=None),
    account_id:  UUID | None     = Query(default=None),
    type:        TransactionType | None = Query(default=None),
    tag:         str | None      = Query(default=None),
    limit:       int             = Query(default=50, le=200),
    offset:      int             = Query(default=0, ge=0),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Return filtered, paginated transactions for the authenticated user.
    All filter parameters are optional.
    """
    repo = TransactionRepository(db)
    txns = await repo.list_by_user(
        user_id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        account_id=account_id,
        txn_type=type,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return [_txn_to_read(t) for t in txns]


# ── POST /transactions ────────────────────────────────────────────────────────

@router.post("/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a new transaction."""
    from datetime import timezone

    repo = TransactionRepository(db)
    txn = Transaction(
        user_id=user_id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        amount=payload.amount,
        type=payload.type,
        note=payload.note,
        tags=payload.tags,
        date=payload.date or datetime.now(timezone.utc),
    )
    created = await repo.create(txn)
    return _txn_to_read(created)


# ── POST /transactions/magic-input ────────────────────────────────────────────

@router.post(
    "/magic-input",
    response_model=ParsedExpenseSchema,
    summary="AI: Parse natural language expense",
)
async def magic_input(
    payload: MagicInputRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai_service: BaseAIService = Depends(get_ai_service),
):
    """
    Pass a natural language sentence to the AI service and receive
    a structured ParsedExpenseSchema back.

    The frontend uses this to pre-fill the expense form.
    Actual transaction creation is a separate POST / call.
    """
    categories = await _get_category_names(db)
    return await ai_service.parse_natural_language_expense(
        text=payload.prompt,
        available_categories=categories,
    )


# ── POST /transactions/scan-receipt ──────────────────────────────────────────

@router.post(
    "/scan-receipt",
    response_model=ParsedExpenseSchema,
    summary="AI: OCR a receipt image",
)
async def scan_receipt(
    file: UploadFile = File(..., description="Receipt image (JPEG, PNG, WEBP, max 10 MB)"),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai_service: BaseAIService = Depends(get_ai_service),
):
    """
    Upload a receipt image; the AI reads it via multimodal OCR and
    returns structured expense data.

    Accepts: image/jpeg, image/png, image/webp
    Max size: 10 MB
    """
    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WEBP.",
        )

    image_bytes = await file.read()

    # Guard against oversized payloads (10 MB)
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 10 MB.",
        )

    # Validate it's actually a valid image using Pillow
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image.",
        )

    categories = await _get_category_names(db)
    return await ai_service.extract_receipt_data(
        image_bytes=image_bytes,
        mime_type=file.content_type,
        available_categories=categories,
    )
