import uuid
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Boolean, Integer, Float, DateTime, ForeignKey,
    Enum as SAEnum, UniqueConstraint, Text, DECIMAL, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    student   = "student"
    professor = "professor"
    head      = "head"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent  = "absent"
    late    = "late"
    excused = "excused"


class DraftStatus(str, enum.Enum):
    auto_present  = "auto_present"
    needs_review  = "needs_review"
    unknown       = "unknown"
    # After professor action:
    confirmed     = "confirmed"
    rejected      = "rejected"


class SessionStatus(str, enum.Enum):
    active    = "active"
    finalized = "finalized"
    cancelled = "cancelled"


class DisputeStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class MarkedBy(str, enum.Enum):
    ai        = "ai"
    professor = "professor"


class EnrollmentRequestStatus(str, enum.Enum):
    pending_approval   = "pending_approval"
    approved           = "approved"
    rejected           = "rejected"
    re_enrollment      = "re_enrollment"   # second+ attempt after lock


# ── University & Department ────────────────────────────────────────────────────

class University(Base):
    __tablename__ = "universities"
    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]       = mapped_column(String(255), nullable=False)
    logo_url:   Mapped[Optional[str]] = mapped_column(Text)
    timezone:   Mapped[str]       = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    departments: Mapped[List["Department"]] = relationship(back_populates="university")


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("university_id", "code"),)

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"))
    name:          Mapped[str]       = mapped_column(String(255), nullable=False)
    code:          Mapped[str]       = mapped_column(String(20),  nullable=False)
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    university: Mapped["University"] = relationship(back_populates="departments")


# ── Users ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:         Mapped[str]       = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str]       = mapped_column(String(255), nullable=False)
    role:          Mapped[UserRole]  = mapped_column(SAEnum(UserRole), nullable=False)
    full_name:     Mapped[str]       = mapped_column(String(255), nullable=False)
    phone:         Mapped[Optional[str]] = mapped_column(String(20))
    avatar_url:    Mapped[Optional[str]] = mapped_column(Text)
    bio:           Mapped[Optional[str]] = mapped_column(Text)
    is_active:     Mapped[bool]      = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student_profile:   Mapped[Optional["Student"]]   = relationship(back_populates="user", uselist=False)
    professor_profile: Mapped[Optional["Professor"]] = relationship(back_populates="user", uselist=False)
    notifications:     Mapped[List["Notification"]]  = relationship(back_populates="user")


# ── Professor ──────────────────────────────────────────────────────────────────

class Professor(Base):
    __tablename__ = "professors"

    user_id:       Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id"))
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"))
    employee_id:   Mapped[str]       = mapped_column(String(50), unique=True)
    designation:   Mapped[Optional[str]] = mapped_column(String(100))
    auto_approve_enrollments: Mapped[bool] = mapped_column(Boolean, default=False)

    user:            Mapped["User"]               = relationship(back_populates="professor_profile")
    subject_batches: Mapped[List["SubjectBatch"]] = relationship(back_populates="professor")


# ── Subject, Batch, SubjectBatch ───────────────────────────────────────────────

class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("department_id", "code"),)

    id:                   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id:        Mapped[uuid.UUID]      = mapped_column(ForeignKey("departments.id"))
    name:                 Mapped[str]            = mapped_column(String(255))
    code:                 Mapped[str]            = mapped_column(String(20))
    credits:              Mapped[int]            = mapped_column(Integer, default=3)
    attendance_threshold: Mapped[float]          = mapped_column(DECIMAL(5, 2), default=75.00)
    created_at:           Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    subject_batches: Mapped[List["SubjectBatch"]] = relationship(back_populates="subject")


class Batch(Base):
    __tablename__ = "batches"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:          Mapped[str]       = mapped_column(String(100))
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"))
    year:          Mapped[int]       = mapped_column(Integer)
    semester:      Mapped[int]       = mapped_column(Integer)

    subject_batches: Mapped[List["SubjectBatch"]] = relationship(back_populates="batch")
    students:        Mapped[List["Student"]]      = relationship(back_populates="batch")


class SubjectBatch(Base):
    __tablename__ = "subject_batches"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id:    Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    batch_id:      Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"))
    professor_id:  Mapped[uuid.UUID] = mapped_column(ForeignKey("professors.user_id"))
    academic_year: Mapped[Optional[str]] = mapped_column(String(10))
    is_active:     Mapped[bool]      = mapped_column(Boolean, default=True)

    subject:     Mapped["Subject"]                 = relationship(back_populates="subject_batches")
    batch:       Mapped["Batch"]                   = relationship(back_populates="subject_batches")
    professor:   Mapped["Professor"]               = relationship(back_populates="subject_batches")
    enrollments: Mapped[List["Enrollment"]]        = relationship(back_populates="subject_batch")
    sessions:    Mapped[List["AttendanceSession"]] = relationship(back_populates="subject_batch")


# ── Student ────────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    user_id:            Mapped[uuid.UUID]    = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    university_id:      Mapped[uuid.UUID]    = mapped_column(ForeignKey("universities.id"))
    department_id:      Mapped[uuid.UUID]    = mapped_column(ForeignKey("departments.id"))
    batch_id:           Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id"), nullable=True)
    student_id:         Mapped[str]          = mapped_column(String(50), unique=True)
    year_of_study:      Mapped[Optional[int]] = mapped_column(Integer)
    is_face_enrolled:   Mapped[bool]          = mapped_column(Boolean, default=False)
    # Enrollment approval system
    is_face_approved:   Mapped[bool]          = mapped_column(Boolean, default=False)
    enrollment_locked:  Mapped[bool]          = mapped_column(Boolean, default=False)
    last_approved_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user:               Mapped["User"]                     = relationship(back_populates="student_profile")
    batch:              Mapped[Optional["Batch"]]          = relationship(back_populates="students")
    enrollments:        Mapped[List["Enrollment"]]         = relationship(back_populates="student")
    records:            Mapped[List["AttendanceRecord"]]   = relationship(back_populates="student")
    embedding:          Mapped[Optional["FaceEmbedding"]]  = relationship(back_populates="student", uselist=False)
    disputes:           Mapped[List["AttendanceDispute"]]  = relationship(back_populates="student")
    enrollment_requests: Mapped[List["FaceEnrollmentRequest"]] = relationship(back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "subject_batch_id"),)

    id:               Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id:       Mapped[uuid.UUID] = mapped_column(ForeignKey("students.user_id"))
    subject_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject_batches.id"))
    enrolled_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active:        Mapped[bool]      = mapped_column(Boolean, default=True)

    student:       Mapped["Student"]      = relationship(back_populates="enrollments")
    subject_batch: Mapped["SubjectBatch"] = relationship(back_populates="enrollments")


# ── Face Embeddings ────────────────────────────────────────────────────────────

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id:                 Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id:         Mapped[uuid.UUID]       = mapped_column(ForeignKey("students.user_id", ondelete="CASCADE"), unique=True)
    embedding:          Mapped[List[float]]     = mapped_column(Vector(512), nullable=False)  # averaged embedding for ANN search
    embeddings_by_angle: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)         # {"front": [...], "left": [...], ...}
    model_version:      Mapped[str]             = mapped_column(String(50), default="buffalo_l_v1")
    quality_score:      Mapped[Optional[float]] = mapped_column(DECIMAL(4, 3))
    face_photo_b64:     Mapped[Optional[str]]   = mapped_column(Text, nullable=True)           # Reference front-facing photo
    enrolled_at:        Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student: Mapped["Student"] = relationship(back_populates="embedding")


# ── Attendance Session (V3) ────────────────────────────────────────────────────

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id:               Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_batch_id: Mapped[uuid.UUID]      = mapped_column(ForeignKey("subject_batches.id"))
    status:           Mapped[SessionStatus]  = mapped_column(SAEnum(SessionStatus), default=SessionStatus.active)
    is_finalized:     Mapped[bool]           = mapped_column(Boolean, default=False)
    classroom_images: Mapped[Optional[dict]] = mapped_column(JSONB)  # [{url, timestamp}]
    started_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalized_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    subject_batch: Mapped["SubjectBatch"]           = relationship(back_populates="sessions")
    records:       Mapped[List["AttendanceRecord"]] = relationship(back_populates="session")
    drafts:        Mapped[List["AttendanceDraft"]]  = relationship(back_populates="session")


# ── Attendance Draft (AI Output — pre-finalization) ────────────────────────────

class AttendanceDraft(Base):
    __tablename__ = "attendance_drafts"

    id:               Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id:       Mapped[uuid.UUID]    = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id:       Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("students.user_id"), nullable=True)
    confidence:       Mapped[float]        = mapped_column(DECIMAL(5, 4))
    status:           Mapped[DraftStatus]  = mapped_column(SAEnum(DraftStatus))
    source_image_idx: Mapped[int]          = mapped_column(Integer, default=0)
    face_crop_b64:    Mapped[Optional[str]] = mapped_column(Text)   # For review UI
    bbox:             Mapped[Optional[dict]] = mapped_column(JSONB)
    candidates:       Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # Top 3 Candidates
    # Professor override
    professor_override: Mapped[Optional[str]] = mapped_column(String(20))  # 'present' | 'absent'
    created_at:       Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AttendanceSession"]   = relationship(back_populates="drafts")
    student: Mapped[Optional["Student"]]   = relationship()


# ── Attendance Record (Finalized — permanent) ──────────────────────────────────

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id"),
        Index("idx_att_student", "student_id", "marked_at"),
    )

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id:      Mapped[uuid.UUID]       = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id:      Mapped[uuid.UUID]       = mapped_column(ForeignKey("students.user_id"))
    status:          Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus))
    marked_by:       Mapped[MarkedBy]        = mapped_column(SAEnum(MarkedBy), default=MarkedBy.ai)
    face_confidence: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 4))
    marked_at:       Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AttendanceSession"] = relationship(back_populates="records")
    student: Mapped["Student"]           = relationship(back_populates="records")
    disputes: Mapped[List["AttendanceDispute"]] = relationship(back_populates="record")


# ── Manual Overrides (Audit trail of professor corrections) ────────────────────

class ManualOverride(Base):
    __tablename__ = "manual_overrides"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id:      Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id:      Mapped[uuid.UUID] = mapped_column(ForeignKey("students.user_id"))
    professor_id:    Mapped[uuid.UUID] = mapped_column(ForeignKey("professors.user_id"))
    previous_status: Mapped[Optional[str]] = mapped_column(String(20))
    new_status:      Mapped[str]       = mapped_column(String(20))
    reason:          Mapped[Optional[str]] = mapped_column(Text)
    overridden_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Attendance Disputes ────────────────────────────────────────────────────────

class AttendanceDispute(Base):
    __tablename__ = "attendance_disputes"

    id:             Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id:      Mapped[uuid.UUID]     = mapped_column(ForeignKey("attendance_records.id"))
    student_id:     Mapped[uuid.UUID]     = mapped_column(ForeignKey("students.user_id"))
    reason:         Mapped[str]           = mapped_column(Text, nullable=False)
    evidence_url:   Mapped[Optional[str]] = mapped_column(Text)
    status:         Mapped[DisputeStatus] = mapped_column(SAEnum(DisputeStatus), default=DisputeStatus.pending)
    professor_id:   Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("professors.user_id"), nullable=True)
    professor_note: Mapped[Optional[str]] = mapped_column(Text)
    raised_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    record:  Mapped["AttendanceRecord"] = relationship(back_populates="disputes")
    student: Mapped["Student"]          = relationship(back_populates="disputes")


# ── Audit Logs ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("attendance_sessions.id"), nullable=True)
    actor_id:   Mapped[uuid.UUID]    = mapped_column(ForeignKey("users.id"))
    action:     Mapped[str]          = mapped_column(String(100))  # 'ai_draft_created' | 'manual_override' | 'finalized'
    target_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    details:    Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Notifications ──────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title:      Mapped[str]       = mapped_column(String(255))
    body:       Mapped[str]       = mapped_column(Text)
    type:       Mapped[str]       = mapped_column(String(50))
    data:       Mapped[Optional[dict]] = mapped_column(JSONB)
    is_read:    Mapped[bool]      = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="notifications")


# ── Face Enrollment Requests ───────────────────────────────────────────────────

class FaceEnrollmentRequest(Base):
    """
    Represents a student's guided face enrollment request awaiting professor approval.
    Scoped per subject batch.
    Status flow: pending_approval → approved | rejected
                 re_enrollment   → approved | rejected  (for locked students)
    """
    __tablename__ = "face_enrollment_requests"

    id:                 Mapped[uuid.UUID]                = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id:         Mapped[uuid.UUID]                = mapped_column(ForeignKey("students.user_id", ondelete="CASCADE"))
    subject_batch_id:   Mapped[uuid.UUID]                = mapped_column(ForeignKey("subject_batches.id", ondelete="CASCADE"))
    status:             Mapped[EnrollmentRequestStatus]  = mapped_column(
                            SAEnum(EnrollmentRequestStatus), default=EnrollmentRequestStatus.pending_approval
                        )
    quality_score:      Mapped[Optional[float]]          = mapped_column(DECIMAL(5, 2), nullable=True)
    # Professor approval tracking
    approved_by:        Mapped[Optional[uuid.UUID]]      = mapped_column(ForeignKey("professors.user_id"), nullable=True)
    approved_at:        Mapped[Optional[datetime]]       = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason:    Mapped[Optional[str]]            = mapped_column(Text, nullable=True)
    # Per-angle embeddings stored as JSON lists (to be written to face_embeddings on approval)
    angles_data:        Mapped[Optional[dict]]           = mapped_column(JSONB, nullable=True)  # {angle: [512 floats]}
    # Photos for professor review
    reference_photo_b64: Mapped[Optional[str]]           = mapped_column(Text, nullable=True)   # front photo
    angle_photos_b64:   Mapped[Optional[dict]]           = mapped_column(JSONB, nullable=True)  # {angle: base64}
    created_at:         Mapped[datetime]                 = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[datetime]                 = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student:       Mapped["Student"]      = relationship(back_populates="enrollment_requests")
    subject_batch: Mapped["SubjectBatch"] = relationship()
