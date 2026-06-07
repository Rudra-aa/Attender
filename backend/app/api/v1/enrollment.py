"""
Enrollment Approval — Professor-facing API
==========================================
Professor sees only enrollment requests for subjects they own.
Supports: list, detail, approve, reject, bulk-approve.
"""
import numpy as np
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import (
    User, Student, Subject, SubjectBatch, FaceEnrollmentRequest, FaceEmbedding,
    EnrollmentRequestStatus, Notification
)

router = APIRouter()


# ── GET: List pending enrollment requests for this professor's subjects ────────

@router.get("/pending")
async def list_pending_enrollments(
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all pending/re-enrollment requests for subjects this professor owns.
    Matching rule: request.subject_id → subject.professor_id == current_user.id
    """
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT
                fer.id::text              AS request_id,
                fer.student_id::text      AS student_id,
                sb.subject_id::text       AS subject_id,
                fer.status                AS status,
                fer.quality_score         AS quality_score,
                fer.created_at            AS created_at,
                u.full_name               AS student_name,
                s.student_id              AS student_roll,
                sub.name                  AS subject_name,
                sub.code                  AS subject_code,
                b.semester                AS semester,
                s.year_of_study           AS year_of_study,
                fer.reference_photo_b64   AS reference_photo
            FROM face_enrollment_requests fer
            JOIN students s ON s.user_id = fer.student_id
            JOIN users u ON u.id = fer.student_id
            JOIN subject_batches sb ON sb.id = fer.subject_batch_id
            JOIN subjects sub ON sub.id = sb.subject_id
            JOIN batches b ON b.id = sb.batch_id
            WHERE
                sb.professor_id = :prof_id
                AND fer.status IN ('pending_approval', 're_enrollment')
            ORDER BY fer.created_at ASC
        """),
        {"prof_id": str(current_user.id)}
    )
    rows = result.fetchall()
    return [
        {
            "request_id": r.request_id,
            "student_id": r.student_id,
            "student_name": r.student_name,
            "student_roll": r.student_roll,
            "subject_id": r.subject_id,
            "subject_name": r.subject_name,
            "subject_code": r.subject_code,
            "semester": r.semester,
            "year_of_study": r.year_of_study,
            "status": r.status,
            "quality_score": float(r.quality_score) if r.quality_score else None,
            "created_at": r.created_at,
            "reference_photo": r.reference_photo,
        }
        for r in rows
    ]


@router.get("/count")
async def pending_enrollment_count(
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Quick count for dashboard badge."""
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM face_enrollment_requests fer
            JOIN subject_batches sb ON sb.id = fer.subject_batch_id
            WHERE sb.professor_id = :prof_id
              AND fer.status IN ('pending_approval', 're_enrollment')
        """),
        {"prof_id": str(current_user.id)}
    )
    row = result.fetchone()
    return {"pending_count": row.cnt if row else 0}


# ── GET: Request detail with all angle photos ─────────────────────────────────

@router.get("/{request_id}")
async def get_enrollment_request_detail(
    request_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Full detail for one enrollment request.
    Includes all 5 angle photos for visual inspection.
    """
    req_res = await db.execute(
        select(FaceEnrollmentRequest).where(FaceEnrollmentRequest.id == request_id)
    )
    req = req_res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Enrollment request not found.")

    # Verify this professor owns the subject
    subj_res = await db.execute(
        select(SubjectBatch).where(
            SubjectBatch.id == req.subject_batch_id,
            SubjectBatch.professor_id == current_user.id,
        )
    )
    if not subj_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="This request is not for your subject.")

    # Get student info
    s_res = await db.execute(
        select(Student, User)
        .join(User, User.id == Student.user_id)
        .where(Student.user_id == req.student_id)
    )
    row = s_res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    student, user = row

    return {
        "request_id": str(req.id),
        "status": req.status.value,
        "quality_score": float(req.quality_score) if req.quality_score else None,
        "created_at": req.created_at,
        "student": {
            "id": str(student.user_id),
            "name": user.full_name,
            "roll": student.student_id,
            "year_of_study": student.year_of_study,
            "is_face_approved": student.is_face_approved,
            "enrollment_locked": student.enrollment_locked,
        },
        "subject": {
            "id": str(req.subject_id),
            "semester": req.semester,
        },
        "angle_photos": req.angle_photos_b64 or {},
        "angles_captured": list(req.angles_data.keys()) if req.angles_data else [],
        "rejected_reason": req.rejected_reason,
        "approved_at": req.approved_at,
    }


# ── POST: Approve a single request ────────────────────────────────────────────

@router.post("/{request_id}/approve")
async def approve_enrollment(
    request_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve an enrollment request.
    - Averages angle embeddings → stores in face_embeddings
    - Sets student.is_face_approved = True
    - Sets student.enrollment_locked = True
    - Updates request status to APPROVED
    """
    req, student = await _get_request_and_verify_ownership(request_id, current_user.id, db)

    await _finalize_approval(req, student, current_user.id, db)

    return {
        "message": "Enrollment approved",
        "request_id": str(request_id),
        "student_name": (await db.execute(
            select(User).where(User.id == student.user_id)
        )).scalar_one().full_name,
    }


# ── POST: Reject a single request ─────────────────────────────────────────────

class RejectRequest(BaseModel):
    reason: Optional[str] = "Rejected by professor"


@router.post("/{request_id}/reject")
async def reject_enrollment(
    request_id: UUID,
    payload: RejectRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Reject an enrollment request with a reason."""
    req, student = await _get_request_and_verify_ownership(request_id, current_user.id, db)

    req.status = EnrollmentRequestStatus.rejected
    req.rejected_reason = payload.reason
    req.approved_by = current_user.id
    req.approved_at = datetime.now(timezone.utc)

    db.add(Notification(
        user_id=req.student_id,
        title="Enrollment Rejected",
        body=f"Your face enrollment was rejected: {payload.reason}",
        type="enrollment_rejected"
    ))

    await db.flush()
    return {
        "message": "Enrollment rejected",
        "request_id": str(request_id),
        "reason": payload.reason,
    }


# ── POST: Bulk approve ────────────────────────────────────────────────────────

class BulkApproveRequest(BaseModel):
    request_ids: List[str]


@router.post("/bulk-approve")
async def bulk_approve_enrollments(
    payload: BulkApproveRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve multiple enrollment requests at once.
    Only approves requests belonging to this professor's subjects.
    """
    approved = []
    failed = []

    for rid_str in payload.request_ids:
        try:
            rid = UUID(rid_str)
            req, student = await _get_request_and_verify_ownership(rid, current_user.id, db)
            await _finalize_approval(req, student, current_user.id, db)
            approved.append(rid_str)
        except HTTPException as e:
            failed.append({"request_id": rid_str, "reason": e.detail})
        except Exception as e:
            failed.append({"request_id": rid_str, "reason": str(e)})

    return {
        "approved_count": len(approved),
        "approved": approved,
        "failed_count": len(failed),
        "failed": failed,
    }


class BulkRejectRequest(BaseModel):
    request_ids: List[str]
    reason: Optional[str] = "Bulk rejected by professor"


@router.post("/bulk-reject")
async def bulk_reject_enrollments(
    payload: BulkRejectRequest,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db),
):
    """Reject multiple enrollment requests at once."""
    rejected = []
    failed = []

    for rid_str in payload.request_ids:
        try:
            rid = UUID(rid_str)
            req, student = await _get_request_and_verify_ownership(rid, current_user.id, db)
            req.status = EnrollmentRequestStatus.rejected
            req.rejected_reason = payload.reason
            req.approved_by = current_user.id
            req.approved_at = datetime.now(timezone.utc)
            db.add(Notification(
                user_id=req.student_id,
                title="Enrollment Rejected",
                body=f"Your face enrollment was rejected: {payload.reason}",
                type="enrollment_rejected"
            ))
            rejected.append(rid_str)
        except HTTPException as e:
            failed.append({"request_id": rid_str, "reason": e.detail})

    await db.flush()
    return {
        "rejected_count": len(rejected),
        "rejected": rejected,
        "failed": failed,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_request_and_verify_ownership(
    request_id: UUID,
    professor_id: UUID,
    db: AsyncSession,
):
    """Fetch the request and verify this professor owns the subject."""
    req_res = await db.execute(
        select(FaceEnrollmentRequest).where(FaceEnrollmentRequest.id == request_id)
    )
    req = req_res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Enrollment request not found.")

    if req.status not in (
        EnrollmentRequestStatus.pending_approval,
        EnrollmentRequestStatus.re_enrollment,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Request is already {req.status.value} — cannot process again."
        )

    # Verify professor owns the subject batch
    subj_res = await db.execute(
        select(SubjectBatch).where(
            SubjectBatch.id == req.subject_batch_id,
            SubjectBatch.professor_id == professor_id,
        )
    )
    if not subj_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="This request is not for your subject.")

    s_res = await db.execute(select(Student).where(Student.user_id == req.student_id))
    student = s_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return req, student


async def _finalize_approval(
    req: FaceEnrollmentRequest,
    student: Student,
    professor_id: UUID,
    db: AsyncSession,
):
    """
    Convert an approved enrollment request into face_embeddings.
    Averages the per-angle embeddings into one primary search vector.
    Stores all angles in embeddings_by_angle for future multi-angle search.
    """
    if not req.angles_data:
        raise HTTPException(status_code=400, detail="No angle embeddings found in request.")

    # Average embeddings
    arrays = [np.array(v, dtype=np.float32) for v in req.angles_data.values()]
    avg = np.mean(arrays, axis=0)
    avg = avg / np.linalg.norm(avg)  # L2 normalize

    embedding_list = avg.tolist()
    angles_by_angle = req.angles_data  # already dict of angle→[512 floats]

    # Upsert into face_embeddings
    fe_res = await db.execute(
        select(FaceEmbedding).where(FaceEmbedding.student_id == req.student_id)
    )
    fe = fe_res.scalar_one_or_none()

    if fe:
        fe.embedding = embedding_list
        fe.embeddings_by_angle = angles_by_angle
        fe.quality_score = float(req.quality_score) / 100.0 if req.quality_score else None
        fe.face_photo_b64 = req.reference_photo_b64
        fe.model_version = "buffalo_l_v1"
    else:
        fe = FaceEmbedding(
            student_id=req.student_id,
            embedding=embedding_list,
            embeddings_by_angle=angles_by_angle,
            quality_score=float(req.quality_score) / 100.0 if req.quality_score else None,
            face_photo_b64=req.reference_photo_b64,
            model_version="buffalo_l_v1",
        )
        db.add(fe)

    # Update request status
    req.status = EnrollmentRequestStatus.approved
    req.approved_by = professor_id
    req.approved_at = datetime.now(timezone.utc)

    # Update student flags
    student.is_face_enrolled = True
    student.is_face_approved = True
    student.enrollment_locked = True
    student.last_approved_at = datetime.now(timezone.utc)

    # Notify student
    db.add(Notification(
        user_id=req.student_id,
        title="Enrollment Approved",
        body="Your biometric face enrollment has been approved! You are now active for AI attendance.",
        type="enrollment_approved"
    ))

    await db.flush()
