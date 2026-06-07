"""
Attendance Disputes — V3 Review Request Workflow
Allows students to raise issues on incorrect attendance records.
Allows professors to approve/reject disputes and logs manual overrides.
"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional

from app.db.session import get_db
from app.core.security import require_student, require_professor
from app.models.models import (
    User, AttendanceDispute, AttendanceRecord, AttendanceStatus,
    DisputeStatus, ManualOverride, AuditLog, Subject, MarkedBy
)

router = APIRouter()


class DisputeCreate(BaseModel):
    record_id: UUID
    reason: str


class DisputeResolve(BaseModel):
    status: str  # 'approved' | 'rejected'
    professor_note: Optional[str] = None


@router.post("/")
async def raise_dispute(
    payload: DisputeCreate,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Student submits an attendance review request."""
    # Verify the record exists and belongs to the student
    record_res = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.id == payload.record_id,
            AttendanceRecord.student_id == current_user.id
        )
    )
    record = record_res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Check if duplicate dispute already exists
    existing = await db.execute(
        select(AttendanceDispute).where(
            AttendanceDispute.record_id == payload.record_id,
            AttendanceDispute.student_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Dispute already raised for this record")

    dispute = AttendanceDispute(
        record_id=payload.record_id,
        student_id=current_user.id,
        reason=payload.reason,
        status=DisputeStatus.pending,
    )
    db.add(dispute)
    await db.flush()

    return {"message": "Dispute submitted successfully", "id": str(dispute.id)}


@router.get("/student")
async def get_my_disputes(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """View disputes raised by the current student."""
    result = await db.execute(
        text("""
            SELECT ad.id, ad.reason, ad.status, ad.raised_at, ad.resolved_at, ad.professor_note,
                   sub.name AS subject_name, ses.started_at AS class_date
            FROM attendance_disputes ad
            JOIN attendance_records ar ON ar.id = ad.record_id
            JOIN attendance_sessions ses ON ses.id = ar.session_id
            JOIN subjects sub ON sub.id = ses.subject_id
            WHERE ad.student_id = :sid
            ORDER BY ad.raised_at DESC
        """),
        {"sid": str(current_user.id)}
    )
    return [
        {
            "id": r[0],
            "reason": r[1],
            "status": r[2],
            "raised_at": r[3],
            "resolved_at": r[4],
            "professor_note": r[5],
            "subject": r[6],
            "class_date": r[7],
        }
        for r in result.fetchall()
    ]


@router.get("/professor")
async def get_professor_disputes(
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """View disputes pending resolution for subjects taught by this professor."""
    result = await db.execute(
        text("""
            SELECT ad.id, ad.reason, ad.status, ad.raised_at, u.full_name, s.student_id AS roll,
                   sub.name AS subject_name, ses.started_at AS class_date, ar.status AS original_status
            FROM attendance_disputes ad
            JOIN users u ON u.id = ad.student_id
            JOIN students s ON s.user_id = ad.student_id
            JOIN attendance_records ar ON ar.id = ad.record_id
            JOIN attendance_sessions ses ON ses.id = ar.session_id
            JOIN subject_batches sb ON sb.id = ses.subject_batch_id
            JOIN subjects sub ON sub.id = sb.subject_id
            WHERE sb.professor_id = :pid
            ORDER BY ad.status DESC, ad.raised_at ASC
        """),
        {"pid": str(current_user.id)}
    )
    return [
        {
            "id": r[0],
            "reason": r[1],
            "status": r[2],
            "raised_at": r[3],
            "student_name": r[4],
            "roll": r[5],
            "subject": r[6],
            "class_date": r[7],
            "original_status": r[8],
        }
        for r in result.fetchall()
    ]


@router.patch("/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: UUID,
    payload: DisputeResolve,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Professor approves or rejects student's attendance dispute."""
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    # Load dispute
    dispute_res = await db.execute(
        select(AttendanceDispute).where(AttendanceDispute.id == dispute_id)
    )
    dispute = dispute_res.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.status != DisputeStatus.pending:
        raise HTTPException(status_code=400, detail="Dispute is already resolved")

    # Load record
    record_res = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.id == dispute.record_id)
    )
    record = record_res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Associated attendance record not found")

    # Verify subject owner is this professor
    from app.models.models import SubjectBatch
    session_res = await db.execute(
        select(AttendanceSession)
        .join(SubjectBatch, SubjectBatch.id == AttendanceSession.subject_batch_id)
        .where(
            AttendanceSession.id == record.session_id,
            SubjectBatch.professor_id == current_user.id,
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=403, detail="Not authorized to resolve this dispute")

    # Apply changes
    dispute.status = DisputeStatus.approved if payload.status == "approved" else DisputeStatus.rejected
    dispute.professor_id = current_user.id
    dispute.professor_note = payload.professor_note
    dispute.resolved_at = datetime.now(timezone.utc)

    if payload.status == "approved":
        prev = record.status.value
        record.status = AttendanceStatus.present
        record.marked_by = MarkedBy.professor

        # Manual Override audit trail
        db.add(ManualOverride(
            session_id=record.session_id,
            student_id=record.student_id,
            professor_id=current_user.id,
            previous_status=prev,
            new_status="present",
            reason=payload.professor_note or f"Dispute resolution: {dispute.reason}",
        ))

    # Audit Log entry
    db.add(AuditLog(
        session_id=record.session_id,
        actor_id=current_user.id,
        action="dispute_resolved",
        target_id=dispute.id,
        details={
            "status": payload.status,
            "student_id": str(dispute.student_id),
            "professor_note": payload.professor_note,
        }
    ))

    await db.flush()
    return {"message": f"Dispute {payload.status}"}
