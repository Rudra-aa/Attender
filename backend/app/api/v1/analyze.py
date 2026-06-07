"""
POST /api/v1/sessions/{session_id}/analyze
==========================================
Professor uploads 2–5 classroom photos.
AI Engine processes them and creates an attendance draft.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import (
    User, AttendanceSession, AttendanceDraft, SessionStatus,
    Enrollment, Student, DraftStatus, AuditLog
)
from app.services.ai_engine import run_ai_engine

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    images: list[str]  # 2–5 base64 JPEG images

    class Config:
        # Images can be large base64 strings
        arbitrary_types_allowed = True


@router.post("/{session_id}/analyze")
async def analyze_classroom(
    session_id: UUID,
    payload: AnalyzeRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Run AI attendance pipeline on classroom images.
    Creates attendance_drafts records.
    Returns the full draft for professor review.
    """
    if not (2 <= len(payload.images) <= 5):
        raise HTTPException(
            status_code=400,
            detail="Please provide between 2 and 5 classroom images for best accuracy."
        )

    # Verify session belongs to this professor and is active
    from app.models.models import SubjectBatch
    session_result = await db.execute(
        select(AttendanceSession)
        .join(SubjectBatch, SubjectBatch.id == AttendanceSession.subject_batch_id)
        .where(
            AttendanceSession.id == session_id,
            SubjectBatch.professor_id == current_user.id,
            AttendanceSession.status == SessionStatus.active,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")

    # Get all students enrolled in this subject
    enrollments_result = await db.execute(
        select(Student, User)
        .join(Enrollment, Enrollment.student_id == Student.user_id)
        .join(User, User.id == Student.user_id)
        .where(Enrollment.subject_batch_id == session.subject_batch_id, Enrollment.is_active == True)
    )
    rows = enrollments_result.all()

    enrolled_students = [
        {
            "student_id": str(student.user_id),
            "name": user.full_name,
            "roll": student.student_id,
        }
        for student, user in rows
    ]

    if not enrolled_students:
        raise HTTPException(status_code=400, detail="No enrolled students found for this subject.")

    # Clear any previous draft for this session (re-analysis)
    existing_drafts = await db.execute(
        select(AttendanceDraft).where(AttendanceDraft.session_id == session_id)
    )
    for draft in existing_drafts.scalars().all():
        await db.delete(draft)
    await db.flush()

    # Run AI engine
    try:
        result = await run_ai_engine(
            session_id=str(session_id),
            image_b64_list=payload.images,
            enrolled_students=enrolled_students,
            db=db,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Persist draft entries
    from uuid import UUID as _UUID
    for item in result.auto_present + result.needs_review:
        draft = AttendanceDraft(
            session_id=session_id,
            student_id=_UUID(item["student_id"]) if item.get("student_id") else None,
            confidence=item["confidence"],
            status=DraftStatus(item["status"]),
            source_image_idx=item.get("source_image", 0),
            face_crop_b64=item.get("face_crop"),
            bbox=None,
            candidates=item.get("candidates"),
        )
        db.add(draft)

    for item in result.unknown_faces:
        draft = AttendanceDraft(
            session_id=session_id,
            student_id=None,
            confidence=0.0,
            status=DraftStatus.unknown,
            source_image_idx=item.get("source_image", 0),
            face_crop_b64=item.get("face_crop"),
            bbox=item.get("bbox"),
            candidates=item.get("candidates"),
        )
        db.add(draft)

    # Audit log
    db.add(AuditLog(
        session_id=session_id,
        actor_id=current_user.id,
        action="ai_draft_created",
        details={
            "images_analyzed": len(payload.images),
            "auto_present": len(result.auto_present),
            "needs_review": len(result.needs_review),
            "unknown": len(result.unknown_faces),
            "not_detected": len(result.not_detected),
        }
    ))

    await db.flush()

    return {
        "session_id": str(session_id),
        "auto_present":  result.auto_present,
        "needs_review":  result.needs_review,
        "unknown_faces": result.unknown_faces,
        "not_detected":  result.not_detected,
        "summary": {
            "auto_present_count": len(result.auto_present),
            "needs_review_count": len(result.needs_review),
            "unknown_count":      len(result.unknown_faces),
            "not_detected_count": len(result.not_detected),
        }
    }
