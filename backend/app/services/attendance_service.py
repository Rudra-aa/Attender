"""
Core Attendance Service
Orchestrates: liveness → GPS → face recognition → fraud check → record insert
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_liveness_token
from app.models.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus,
    FaceEmbedding, FraudLog, FraudType, SessionStatus, Student
)
from app.services.face_recognition_service import extract_embedding, cosine_similarity
from app.services.gps_service import validate_geofence, cross_validate_gps_with_ip
from app.schemas.attendance import MarkAttendanceRequest, AttendanceResult

logger = logging.getLogger(__name__)


class AttendanceError(Exception):
    def __init__(self, message: str, fraud_type: Optional[FraudType] = None):
        self.message = message
        self.fraud_type = fraud_type
        super().__init__(message)


async def mark_attendance(
    request: MarkAttendanceRequest,
    current_user_id: UUID,
    session_id: UUID,
    ip_address: str,
    user_agent: str,
    db: AsyncSession,
) -> AttendanceResult:
    """
    Full attendance pipeline:
    1. Verify liveness token
    2. Load active session
    3. GPS geofence validation + spoofing detection
    4. Face recognition (pgvector ANN)
    5. Duplicate check
    6. Record insert
    """

    # 1. Liveness token verification
    if not verify_liveness_token(
        request.liveness_token,
        request.liveness_challenge,
        str(current_user_id),
    ):
        raise AttendanceError(
            "Liveness verification failed or expired. Please try again.",
            FraudType.liveness_fail,
        )

    # 2. Load session
    session_result = await db.execute(
        select(AttendanceSession).where(
            AttendanceSession.id == session_id,
            AttendanceSession.status == SessionStatus.active,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise AttendanceError("No active session found.")

    # 3a. GPS geofence check
    gps_valid, distance_m = validate_geofence(
        student_lat=request.lat,
        student_lon=request.lon,
        geofence_lat=float(session.geofence_lat),
        geofence_lon=float(session.geofence_lon),
        geofence_radius=session.geofence_radius,
    )
    if not gps_valid:
        raise AttendanceError(
            f"You are {distance_m}m from the classroom. Must be within {session.geofence_radius}m.",
            FraudType.gps_spoof,
        )

    # 3b. IP vs GPS cross-check (non-blocking)
    gps_suspicious, discrepancy_km = await cross_validate_gps_with_ip(
        student_lat=request.lat,
        student_lon=request.lon,
        ip_address=ip_address,
    )
    if gps_suspicious:
        await _log_fraud(db, current_user_id, session_id, FraudType.ip_mismatch, ip_address, {
            "discrepancy_km": discrepancy_km
        })
        # Don't block on IP mismatch alone (VPNs, mobile data) — just log it

    # 4. Face recognition
    embedding, quality_score = extract_embedding(request.image_base64)
    if embedding is None:
        raise AttendanceError("No face detected in image. Please try again.")

    # pgvector ANN search
    query_vec = str(embedding.tolist())
    ann_result = await db.execute(
        text("""
            SELECT student_id, 1 - (embedding <=> :qv::vector) AS similarity
            FROM face_embeddings
            ORDER BY embedding <=> :qv::vector
            LIMIT 1
        """),
        {"qv": query_vec},
    )
    row = ann_result.fetchone()

    if not row or row.similarity < settings.FACE_SIMILARITY_THRESHOLD:
        raise AttendanceError(
            "Face not recognized. Please ensure your face is clearly visible.",
            FraudType.proxy_attempt,
        )

    matched_student_id = row.student_id
    face_confidence = float(row.similarity)

    # Verify matched student is THIS user (prevent proxy)
    if matched_student_id != current_user_id:
        await _log_fraud(db, current_user_id, session_id, FraudType.proxy_attempt, ip_address, {
            "matched_to": str(matched_student_id),
            "requester": str(current_user_id),
        })
        raise AttendanceError("Face recognition mismatch. Proxy attendance detected.")

    # 5. Duplicate check
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == current_user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AttendanceError("You have already marked attendance for this session.")

    # 6. Determine status (present vs late)
    now = datetime.now(timezone.utc)
    late_cutoff = session.actual_start
    if session.actual_start and late_cutoff:
        from datetime import timedelta
        late_cutoff = session.actual_start + timedelta(minutes=session.late_threshold)
    att_status = AttendanceStatus.late if (session.actual_start and now > late_cutoff) else AttendanceStatus.present

    # 7. Insert record
    record = AttendanceRecord(
        session_id=session_id,
        student_id=current_user_id,
        status=att_status,
        face_confidence=face_confidence,
        liveness_score=1.0,  # Passed challenge
        liveness_passed=True,
        student_lat=request.lat,
        student_lon=request.lon,
        distance_from_geofence=distance_m,
        gps_valid=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(record)
    await db.flush()

    logger.info(f"✅ Attendance marked: student={current_user_id}, session={session_id}, status={att_status}")

    return AttendanceResult(
        status=att_status.value,
        session_id=str(session_id),
        subject_name=session.subject.name if session.subject else "",
        marked_at=record.marked_at,
        face_confidence=face_confidence,
        distance_m=distance_m,
    )


async def _log_fraud(
    db: AsyncSession,
    student_id: UUID,
    session_id: UUID,
    fraud_type: FraudType,
    ip: str,
    details: dict,
):
    log = FraudLog(
        student_id=student_id,
        session_id=session_id,
        fraud_type=fraud_type,
        severity=3,
        details=details,
        ip_address=ip,
    )
    db.add(log)
    await db.flush()
