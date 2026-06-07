"""
Draft Management — Professor reviews and finalizes AI attendance
"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import (
    User, AttendanceDraft, AttendanceRecord, AttendanceSession,
    ManualOverride, AuditLog, DraftStatus, AttendanceStatus,
    MarkedBy, SessionStatus, Enrollment, Student, Notification
)

router = APIRouter()


@router.get("/{session_id}")
async def get_draft(
    session_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Return the AI draft for a session."""
    # Verify session ownership
    from app.models.models import SubjectBatch
    session_res = await db.execute(
        select(AttendanceSession)
        .join(SubjectBatch, SubjectBatch.id == AttendanceSession.subject_batch_id)
        .where(
            AttendanceSession.id == session_id,
            SubjectBatch.professor_id == current_user.id,
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    drafts_res = await db.execute(
        select(AttendanceDraft).where(AttendanceDraft.session_id == session_id)
    )
    drafts = drafts_res.scalars().all()

    # Load student names, rolls, and reference photos for all enrolled students
    all_enrolled = await _get_enrolled_student_ids(session.subject_batch_id, db)
    student_names: dict[str, str] = {}
    student_rolls: dict[str, str] = {}
    student_photos: dict[str, str] = {}
    if all_enrolled:
        from sqlalchemy import text
        res = await db.execute(
            text("""
                SELECT s.user_id::text, u.full_name, s.student_id, fe.face_photo_b64
                FROM students s
                JOIN users u ON u.id = s.user_id
                LEFT JOIN face_embeddings fe ON fe.student_id = s.user_id
                WHERE s.user_id::text = ANY(:ids)
            """),
            {"ids": all_enrolled}
        )
        for row in res.fetchall():
            student_names[row[0]] = row[1]
            student_rolls[row[0]] = row[2]
            student_photos[row[0]] = row[3]

    auto_present  = []
    needs_review  = []
    unknown_faces = []

    for d in drafts:
        sid = str(d.student_id) if d.student_id else None
        base = {
            "draft_id":   str(d.id),
            "student_id": sid,
            "name":       student_names.get(sid, "Unknown") if sid else None,
            "roll":       student_rolls.get(sid, "") if sid else None,
            "confidence": float(d.confidence),
            "status":     d.professor_override or d.status.value,
            "face_crop":  d.face_crop_b64,
            "candidates": d.candidates or [],
        }
        if d.status == DraftStatus.unknown and not d.professor_override:
            unknown_faces.append(base)
        elif d.professor_override:
            # Already reviewed by professor — put in whichever list
            if d.professor_override == "present":
                auto_present.append(base)
            else:
                needs_review.append(base)
        elif d.status == DraftStatus.auto_present:
            auto_present.append(base)
        else:
            needs_review.append(base)

    detected_ids = {str(d.student_id) for d in drafts if d.student_id}
    not_detected = [
        {
            "student_id": sid,
            "name": student_names.get(sid, ""),
            "roll": student_rolls.get(sid, ""),
            "face_photo": student_photos.get(sid, None),
        }
        for sid in all_enrolled if sid not in detected_ids
    ]

    return {
        "session_id":   str(session_id),
        "is_finalized": session.is_finalized,
        "auto_present":  auto_present,
        "needs_review":  needs_review,
        "unknown_faces": unknown_faces,
        "not_detected":  not_detected,
    }


class OverrideRequest(BaseModel):
    action: str  # 'present' | 'absent'
    reason: Optional[str] = None
    # For not-detected students or candidate selection:
    student_id: Optional[str] = None


@router.patch("/{draft_id}/override")
async def override_draft_item(
    draft_id: UUID,
    payload: OverrideRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Professor manually overrides a single draft entry."""
    if payload.action not in ("present", "absent"):
        raise HTTPException(status_code=400, detail="Action must be 'present' or 'absent'")

    draft_res = await db.execute(
        select(AttendanceDraft).where(AttendanceDraft.id == draft_id)
    )
    draft = draft_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft item not found")

    prev = draft.professor_override or draft.status.value
    
    if payload.student_id:
        draft.student_id = UUID(payload.student_id)
        
    draft.professor_override = payload.action

    # Audit
    db.add(ManualOverride(
        session_id=draft.session_id,
        student_id=draft.student_id,
        professor_id=current_user.id,
        previous_status=prev,
        new_status=payload.action,
        reason=payload.reason or "Manual review correction",
    ))
    await db.flush()
    return {"message": "Override applied", "draft_id": str(draft_id), "new_status": payload.action}


@router.post("/{session_id}/add-manual")
async def add_manual_attendance(
    session_id: UUID,
    payload: OverrideRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Add a student who wasn't detected — creates a draft entry directly."""
    if not payload.student_id:
        raise HTTPException(status_code=400, detail="student_id required")

    sid = UUID(payload.student_id)
    # Check if already in draft
    existing = await db.execute(
        select(AttendanceDraft).where(
            AttendanceDraft.session_id == session_id,
            AttendanceDraft.student_id == sid,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student already in draft. Use /override instead.")

    draft = AttendanceDraft(
        session_id=session_id,
        student_id=sid,
        confidence=0.0,
        status=DraftStatus.confirmed,
        professor_override=payload.action,
        face_crop_b64=None,
    )
    db.add(draft)

    db.add(ManualOverride(
        session_id=session_id,
        student_id=sid,
        professor_id=current_user.id,
        previous_status="not_detected",
        new_status=payload.action,
        reason=payload.reason or "Manual add by professor",
    ))
    await db.flush()
    return {"message": "Manual attendance added"}


@router.post("/{session_id}/finalize")
async def finalize_attendance(
    session_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Convert all draft entries into permanent attendance_records.
    Marks session as finalized.
    """
    from app.models.models import SubjectBatch
    session_res = await db.execute(
        select(AttendanceSession)
        .join(SubjectBatch, SubjectBatch.id == AttendanceSession.subject_batch_id)
        .where(
            AttendanceSession.id == session_id,
            SubjectBatch.professor_id == current_user.id,
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_finalized:
        raise HTTPException(status_code=409, detail="Session already finalized")

    drafts_res = await db.execute(
        select(AttendanceDraft).where(
            AttendanceDraft.session_id == session_id,
            AttendanceDraft.student_id != None,  # skip unknown faces
        )
    )
    drafts = drafts_res.scalars().all()

    present_count = 0
    absent_count  = 0

    for draft in drafts:
        # Determine final status
        final_action = draft.professor_override or (
            "present" if draft.status == DraftStatus.auto_present else None
        )
        if final_action is None:
            # needs_review with no professor decision → absent
            final_action = "absent"

        att_status = AttendanceStatus.present if final_action == "present" else AttendanceStatus.absent
        marked_by  = MarkedBy.professor if draft.professor_override else MarkedBy.ai

        record = AttendanceRecord(
            session_id=session_id,
            student_id=draft.student_id,
            status=att_status,
            marked_by=marked_by,
            face_confidence=float(draft.confidence),
        )
        db.add(record)
        
        db.add(Notification(
            user_id=draft.student_id,
            title="Attendance Marked",
            body=f"Your attendance was marked as {att_status.value} by your professor.",
            type="attendance_finalized"
        ))

        if att_status == AttendanceStatus.present:
            present_count += 1
        else:
            absent_count += 1

    # Finalize session
    session.is_finalized = True
    session.status = SessionStatus.finalized
    session.finalized_at = datetime.now(timezone.utc)

    # Audit log
    db.add(AuditLog(
        session_id=session_id,
        actor_id=current_user.id,
        action="finalized",
        details={"present": present_count, "absent": absent_count},
    ))
    await db.flush()

    return {
        "message": "Attendance finalized",
        "session_id": str(session_id),
        "present_count": present_count,
        "absent_count":  absent_count,
    }


# ── Records (Professor reads final attendance) ─────────────────────────────────

@router.get("/{session_id}/records")
async def get_session_records(
    session_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Return finalized attendance records for a session."""
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT u.full_name, s.student_id, ar.status, ar.marked_by, ar.face_confidence, ar.marked_at
            FROM attendance_records ar
            JOIN students s ON s.user_id = ar.student_id
            JOIN users u ON u.id = s.user_id
            WHERE ar.session_id = :sid
            ORDER BY u.full_name
        """),
        {"sid": str(session_id)}
    )
    rows = result.fetchall()
    return [
        {
            "name":       r[0],
            "roll":       r[1],
            "status":     r[2],
            "marked_by":  r[3],
            "confidence": float(r[4]) if r[4] else None,
            "marked_at":  r[5],
        }
        for r in rows
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_enrolled_student_ids(subject_batch_id: UUID, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Enrollment.student_id).where(
            Enrollment.subject_batch_id == subject_batch_id,
            Enrollment.is_active == True,
        )
    )
    return [str(r[0]) for r in result.fetchall()]
