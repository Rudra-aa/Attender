"""Attendance marking and active sessions endpoints (Cleaned up for V3)"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_student
from app.models.models import User, AttendanceSession, SessionStatus, Enrollment

router = APIRouter()


@router.post("/mark")
async def mark_attendance_endpoint():
    """Deprecated in V3. Professor handles image upload and review."""
    raise HTTPException(status_code=501, detail="Student self-marking is disabled in V3. Professor-Driven flow active.")


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Get all active attendance sessions for this student's enrolled subjects."""
    result = await db.execute(
        select(AttendanceSession)
        .join(Enrollment, Enrollment.subject_batch_id == AttendanceSession.subject_batch_id)
        .where(
            Enrollment.student_id == current_user.id,
            Enrollment.is_active == True,
            AttendanceSession.status == SessionStatus.active,
        )
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "subject_batch_id": str(s.subject_batch_id),
            "status": s.status.value,
            "started_at": s.started_at,
        }
        for s in sessions
    ]
