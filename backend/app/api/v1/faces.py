"""
Face Enrollment — V3
======================
Student guided enrollment: subject-scoped, multi-angle, creates pending request.
Professor-assisted enrollment: directly approves (skips request flow).

Status Flow:
  Student submits → pending_approval → professor approves/rejects
  If enrollment_locked → request becomes re_enrollment type
"""
import numpy as np
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user, require_professor
from app.models.models import (
    User, FaceEmbedding, Student, Subject, SubjectBatch, Professor, Enrollment,
    FaceEnrollmentRequest, EnrollmentRequestStatus, UserRole
)
from app.services.face_recognition_service import extract_embedding

router = APIRouter()

# Quality thresholds
ENROLLMENT_QUALITY_MIN = 0.70  # Per-angle minimum
ENROLLMENT_QUALITY_OVERALL = 80.0  # Overall score out of 100


# ── Guided Enrollment Request (Student) ───────────────────────────────────────

class GuidedEnrollRequest(BaseModel):
    """
    Student submits 5 angles captured during guided enrollment.
    subject_id determines which professor receives the approval request.
    """
    subject_id: str
    angles: dict  # {"front": "base64...", "left": "base64...", "right": "base64...", "up": "base64...", "down": "base64..."}

REQUIRED_ANGLES = ["front", "left", "right", "up", "down"]


@router.post("/enroll/guided")
async def enroll_guided(
    payload: GuidedEnrollRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Student-facing guided enrollment.
    Processes 5-angle face images, validates quality, creates a pending approval request.
    If enrollment_locked, creates a RE_ENROLLMENT_REQUEST.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can self-enroll.")

    # Get student profile
    s_res = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = s_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    # Verify the student is enrolled in this subject
    subj_id = UUID(payload.subject_id)
    enroll_res = await db.execute(
        select(Enrollment, SubjectBatch)
        .join(SubjectBatch, SubjectBatch.id == Enrollment.subject_batch_id)
        .where(
            Enrollment.student_id == current_user.id,
            SubjectBatch.subject_id == subj_id,
            Enrollment.is_active == True,
        )
    )
    row = enroll_res.first()
    if not row:
        raise HTTPException(status_code=403, detail="You are not enrolled in this subject.")
    enrollment, subject_batch = row

    # Get the professor's auto-approve setting
    prof_res = await db.execute(select(Professor).where(Professor.user_id == subject_batch.professor_id))
    professor = prof_res.scalar_one()

    # Check if there is an active pending request for this student+subject
    existing = await db.execute(
        select(FaceEnrollmentRequest).where(
            FaceEnrollmentRequest.student_id == current_user.id,
            FaceEnrollmentRequest.subject_batch_id == subject_batch.id,
            FaceEnrollmentRequest.status.in_([
                EnrollmentRequestStatus.pending_approval,
                EnrollmentRequestStatus.re_enrollment,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have a pending enrollment request for this subject. Please wait for professor approval."
        )

    # Validate angles provided
    missing = [a for a in REQUIRED_ANGLES if a not in payload.angles]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required angles: {missing}. All 5 angles must be captured."
        )

    # Extract embeddings per angle
    valid_embeddings: dict[str, list] = {}
    angle_quality: dict[str, float] = {}
    angle_photos: dict[str, str] = {}
    failed_angles = []

    for angle in REQUIRED_ANGLES:
        img_b64 = payload.angles[angle]
        try:
            embedding, quality = extract_embedding(img_b64)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=f"Face recognition model unavailable: {e}")

        if embedding is None:
            failed_angles.append(angle)
            continue
        if quality < ENROLLMENT_QUALITY_MIN:
            failed_angles.append(angle)
            continue

        valid_embeddings[angle] = embedding.tolist()
        angle_quality[angle] = round(float(quality), 4)
        angle_photos[angle] = img_b64

    if len(valid_embeddings) < 3:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(valid_embeddings)}/5 angles passed quality check. "
                f"Failed angles: {failed_angles}. "
                f"Ensure good lighting, face centered, no obstructions, no blur."
            )
        )

    # Compute overall quality score (0–100)
    avg_quality = float(np.mean(list(angle_quality.values()))) * 100

    # Determine request type automatically based on AI score if Professor enabled it
    if professor.auto_approve_enrollments:
        if avg_quality >= ENROLLMENT_QUALITY_OVERALL:
            request_status = EnrollmentRequestStatus.approved
        else:
            request_status = EnrollmentRequestStatus.re_enrollment
    else:
        # Fall back to manual professor review
        is_re_enrollment = student.enrollment_locked
        request_status = (
            EnrollmentRequestStatus.re_enrollment
            if is_re_enrollment
            else EnrollmentRequestStatus.pending_approval
        )

    # Create enrollment request
    req = FaceEnrollmentRequest(
        student_id=current_user.id,
        subject_batch_id=subject_batch.id,
        status=request_status,
        quality_score=round(avg_quality, 2),
        angles_data=valid_embeddings,
        reference_photo_b64=valid_embeddings.get("front") and payload.angles.get("front"),
        angle_photos_b64=angle_photos,
    )
    db.add(req)
    
    # If approved by AI, directly enroll the student
    if request_status == EnrollmentRequestStatus.approved:
        # Save embeddings
        avg_embedding = np.mean([np.array(emb) for emb in valid_embeddings.values()], axis=0)
        face_record = FaceEmbedding(
            student_id=current_user.id,
            embedding=avg_embedding.tolist(),
            embeddings_by_angle=valid_embeddings,
            face_photo_b64=req.reference_photo_b64,
            quality_score=round(avg_quality, 2),
            model_version="buffalo_l",
            enrolled_at=datetime.now(timezone.utc),
        )
        db.add(face_record)

        # Update student profile
        student.is_face_enrolled = True
        student.is_face_approved = True
        student.last_approved_at = datetime.now(timezone.utc)
        student.enrollment_locked = True
        
    await db.flush()

    return {
        "request_id": str(req.id),
        "status": request_status.value,
        "quality_score": round(avg_quality, 2),
        "angles_captured": len(valid_embeddings),
        "angles_quality": angle_quality,
        "message": (
            "Face verification successful! You are now enrolled."
            if request_status == EnrollmentRequestStatus.approved
            else "Quality score is too low. Please reverify your face in better lighting."
            if request_status == EnrollmentRequestStatus.re_enrollment and professor.auto_approve_enrollments
            else "Re-enrollment request submitted. Your professor will review it."
            if request_status == EnrollmentRequestStatus.re_enrollment
            else "Enrollment request submitted. Your professor will review and approve it."
        )
    }


@router.get("/enrollment-status")
async def get_enrollment_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student: check their overall face enrollment status."""
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Students only.")

    s_res = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = s_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    # Get latest request
    req_res = await db.execute(
        select(FaceEnrollmentRequest)
        .where(FaceEnrollmentRequest.student_id == current_user.id)
        .order_by(FaceEnrollmentRequest.created_at.desc())
        .limit(1)
    )
    latest_req = req_res.scalar_one_or_none()

    return {
        "is_face_enrolled": student.is_face_enrolled,
        "is_face_approved": student.is_face_approved,
        "enrollment_locked": student.enrollment_locked,
        "last_approved_at": student.last_approved_at,
        "pending_request": {
            "id": str(latest_req.id),
            "status": latest_req.status.value,
            "quality_score": float(latest_req.quality_score) if latest_req.quality_score else None,
            "created_at": latest_req.created_at,
        } if latest_req and latest_req.status in (
            EnrollmentRequestStatus.pending_approval,
            EnrollmentRequestStatus.re_enrollment,
        ) else None,
    }


@router.get("/enrollment-status/subjects")
async def get_enrollment_status_by_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student: check enrollment status per enrolled subject."""
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Students only.")

    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT
                sub.id::text as subject_id,
                sub.name as subject_name,
                sub.code as subject_code,
                fer.id::text as request_id,
                fer.status as request_status,
                fer.quality_score,
                fer.created_at as requested_at
            FROM subjects sub
            JOIN subject_batches sb ON sb.subject_id = sub.id
            JOIN enrollments e ON e.subject_batch_id = sb.id
            LEFT JOIN face_enrollment_requests fer
                ON fer.subject_batch_id = sb.id AND fer.student_id = :sid
                AND fer.id = (
                    SELECT id FROM face_enrollment_requests
                    WHERE subject_batch_id = sb.id AND student_id = :sid
                    ORDER BY created_at DESC LIMIT 1
                )
            WHERE e.student_id = :sid AND e.is_active = TRUE
            ORDER BY sub.name
        """),
        {"sid": str(current_user.id)}
    )
    rows = result.fetchall()
    return [
        {
            "subject_id": r.subject_id,
            "subject_name": r.subject_name,
            "subject_code": r.subject_code,
            "request_id": r.request_id,
            "status": r.request_status,
            "quality_score": float(r.quality_score) if r.quality_score else None,
            "requested_at": r.requested_at,
        }
        for r in rows
    ]


# ── Status check (by student_id, for professors) ─────────────────────────────

@router.get("/status/{student_id}")
async def enrollment_status_for_professor(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Professor/admin: Check if a specific student has a face enrolled."""
    result = await db.execute(
        select(FaceEmbedding).where(FaceEmbedding.student_id == student_id)
    )
    record = result.scalar_one_or_none()
    return {
        "student_id": str(student_id),
        "enrolled": record is not None,
        "quality_score": float(record.quality_score) if record else None,
        "enrolled_at": record.enrolled_at if record else None,
        "model_version": record.model_version if record else None,
        "has_multi_angle": bool(record.embeddings_by_angle) if record else False,
    }


@router.delete("/me")
async def delete_my_face(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student removes their own face data (GDPR right to delete)."""
    result = await db.execute(
        select(FaceEmbedding).where(FaceEmbedding.student_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if record:
        await db.delete(record)
        s_result = await db.execute(select(Student).where(Student.user_id == current_user.id))
        student = s_result.scalar_one_or_none()
        if student:
            student.is_face_enrolled = False
            student.is_face_approved = False
            student.enrollment_locked = False
    return {"message": "Face data removed"}
