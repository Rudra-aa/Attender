"""Session management routes — V3 Professor-Driven"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import AttendanceSession, SessionStatus, SubjectBatch, User

router = APIRouter()


class CreateSessionRequest(BaseModel):
    subject_id: str


@router.post("/")
async def create_session(
    payload: CreateSessionRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Create a new attendance session for a subject."""
    # Verify subject batch belongs to professor
    subj_res = await db.execute(
        select(SubjectBatch).where(
            SubjectBatch.id == UUID(payload.subject_id),
            SubjectBatch.professor_id == current_user.id,
            SubjectBatch.is_active == True,
        )
    )
    subject_batch = subj_res.scalar_one_or_none()
    if not subject_batch:
        raise HTTPException(status_code=404, detail="Subject not found or not owned by you.")

    session = AttendanceSession(
        subject_batch_id=UUID(payload.subject_id),
        status=SessionStatus.active,
    )
    db.add(session)
    await db.flush()

    return {
        "id": str(session.id),
        "subject_id": str(session.subject_batch_id),
        "status": session.status.value,
        "started_at": session.started_at,
    }


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AttendanceSession)
        .join(SubjectBatch, SubjectBatch.id == AttendanceSession.subject_batch_id)
        .where(
            AttendanceSession.id == session_id,
            SubjectBatch.professor_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "id": str(session.id),
        "status": session.status.value,
        "is_finalized": session.is_finalized,
        "started_at": session.started_at,
        "finalized_at": session.finalized_at,
    }
