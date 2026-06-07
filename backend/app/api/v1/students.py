"""Student profile and attendance history routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.db.session import get_db
from app.core.security import require_student
from app.models.models import User, AttendanceRecord, Enrollment, Student, Batch, SubjectBatch, Department
from pydantic import BaseModel
from typing import List

router = APIRouter()


@router.get("/me")
async def get_profile(current_user: User = Depends(require_student), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student, Department.name)
        .outerjoin(Department, Department.id == Student.department_id)
        .where(Student.user_id == current_user.id)
    )
    row = result.first()
    student = row[0] if row else None
    dept_name = row[1] if row else None
    
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value,
        "avatar_url": current_user.avatar_url,
        "student_id": student.student_id if student else None,
        "department": dept_name,
        "year_of_study": student.year_of_study if student else None,
        "batch_id": str(student.batch_id) if student and student.batch_id else None,
        "is_face_enrolled": student.is_face_enrolled if student else False,
        "is_face_approved": student.is_face_approved if student else False,
        "phone": current_user.phone,
        "bio": current_user.bio,
    }

class UpdateProfileRequest(BaseModel):
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

@router.patch("/me")
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
        
    await db.commit()
    return {"message": "Profile updated successfully"}

@router.get("/onboard/metadata")
async def get_onboard_metadata(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    # Fetch all departments
    dept_res = await db.execute(select(Department))
    departments = dept_res.scalars().all()
    
    # Fetch all batches
    batch_res = await db.execute(select(Batch))
    batches = batch_res.scalars().all()
    
    return {
        "departments": [{"id": str(d.id), "name": d.name, "code": d.code} for d in departments],
        "batches": [{"id": str(b.id), "name": b.name, "department_id": str(b.department_id), "year": b.year, "semester": b.semester} for b in batches]
    }

class OnboardRequest(BaseModel):
    department_id: str
    year_of_study: int
    batch_id: str

@router.post("/me/onboard")
async def onboard_student(
    payload: OnboardRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    from uuid import UUID
    from fastapi import HTTPException
    
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    if student.batch_id:
        raise HTTPException(status_code=400, detail="Student is already onboarded")
        
    batch_id = UUID(payload.batch_id)
    # Validate batch
    b_res = await db.execute(select(Batch).where(Batch.id == batch_id))
    if not b_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Batch not found")

    student.department_id = UUID(payload.department_id)
    student.year_of_study = payload.year_of_study
    student.batch_id = batch_id
    
    # Fetch all SubjectBatches for this batch to enroll the student automatically
    sb_res = await db.execute(select(SubjectBatch).where(SubjectBatch.batch_id == batch_id, SubjectBatch.is_active == True))
    subject_batches = sb_res.scalars().all()
    
    for sb in subject_batches:
        enroll = Enrollment(
            student_id=student.user_id,
            subject_batch_id=sb.id,
            is_active=True
        )
        db.add(enroll)
        
    await db.commit()
    return {"message": "Onboarding successful", "enrolled_subjects": len(subject_batches)}


@router.get("/me/attendance/subjects")
async def attendance_by_subject(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT subject_name, attendance_percentage, total_sessions,
                   attended_sessions, attendance_threshold, is_at_risk
            FROM student_subject_attendance
            WHERE student_id = :sid
            ORDER BY attendance_percentage ASC
        """),
        {"sid": str(current_user.id)},
    )
    rows = result.fetchall()
    return [
        {
            "subject": r.subject_name,
            "pct": float(r.attendance_percentage or 0),
            "total": r.total_sessions,
            "attended": r.attended_sessions,
            "threshold": float(r.attendance_threshold),
            "at_risk": r.is_at_risk,
        }
        for r in rows
    ]


@router.get("/me/attendance/risk")
async def at_risk_subjects(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT subject_name, attendance_percentage, attendance_threshold
            FROM student_subject_attendance
            WHERE student_id = :sid AND is_at_risk = TRUE
        """),
        {"sid": str(current_user.id)},
    )
    return [
        {"subject": r.subject_name, "pct": float(r.attendance_percentage), "threshold": float(r.attendance_threshold)}
        for r in result.fetchall()
    ]


@router.get("/me/attendance/records")
async def get_my_attendance_records(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """List all individual attendance records for the student."""
    result = await db.execute(
        text("""
            SELECT ar.id, ar.status, ar.marked_at, ar.marked_by, ar.face_confidence,
                   sub.name AS subject_name, ses.id AS session_id
            FROM attendance_records ar
            JOIN attendance_sessions ses ON ses.id = ar.session_id
            JOIN subject_batches sb ON sb.id = ses.subject_batch_id
            JOIN subjects sub ON sub.id = sb.subject_id
            WHERE ar.student_id = :sid
            ORDER BY ar.marked_at DESC
        """),
        {"sid": str(current_user.id)}
    )
    return [
        {
            "record_id": str(r[0]),
            "status": r[1],
            "marked_at": r[2],
            "marked_by": r[3],
            "confidence": float(r[4]) if r[4] else None,
            "subject": r[5],
            "session_id": str(r[6]),
        }
        for r in result.fetchall()
    ]
