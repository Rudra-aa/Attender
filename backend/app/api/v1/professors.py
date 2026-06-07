"""Professor profile and associated entities"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import User, Subject, Enrollment, Student

router = APIRouter()


@router.get("/me")
async def get_profile(
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import Professor, Department
    prof_res = await db.execute(
        select(Professor, Department.name)
        .outerjoin(Department, Department.id == Professor.department_id)
        .where(Professor.user_id == current_user.id)
    )
    row = prof_res.first()
    prof_record = row[0] if row else None
    dept_name = row[1] if row else None
    
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value,
        "avatar_url": current_user.avatar_url,
        "designation": prof_record.designation if prof_record else None,
        "department": dept_name,
        "auto_approve_enrollments": prof_record.auto_approve_enrollments if prof_record else False
    }

from pydantic import BaseModel
class ProfessorSettings(BaseModel):
    auto_approve_enrollments: bool

@router.patch("/settings")
async def update_settings(
    payload: ProfessorSettings,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import Professor
    prof = await db.execute(select(Professor).where(Professor.user_id == current_user.id))
    prof_record = prof.scalar_one_or_none()
    if not prof_record:
        raise HTTPException(status_code=404, detail="Professor profile not found")
        
    prof_record.auto_approve_enrollments = payload.auto_approve_enrollments
    await db.flush()
    return {"message": "Settings updated", "auto_approve_enrollments": prof_record.auto_approve_enrollments}

@router.get("/subjects")
async def get_professor_subjects(
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import SubjectBatch, Subject, Batch
    result = await db.execute(
        select(SubjectBatch, Subject, Batch)
        .join(Subject, Subject.id == SubjectBatch.subject_id)
        .join(Batch, Batch.id == SubjectBatch.batch_id)
        .where(SubjectBatch.professor_id == current_user.id)
    )
    rows = result.all()
    return [
        {
            "id": str(sb.id),
            "name": sub.name,
            "code": sub.code,
            "semester": b.semester,
            "is_active": sb.is_active
        }
        for sb, sub, b in rows
    ]

@router.get("/subjects/{subject_id}/students")
async def get_enrolled_students(
    subject_id: str,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import SubjectBatch
    # Verify subject batch belongs to professor
    subj = await db.execute(select(SubjectBatch).where(SubjectBatch.id == subject_id, SubjectBatch.professor_id == current_user.id))
    if not subj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    result = await db.execute(
        select(User.full_name, Student.student_id, Enrollment.is_active)
        .join(Student, Student.user_id == User.id)
        .join(Enrollment, Enrollment.student_id == Student.user_id)
        .where(Enrollment.subject_batch_id == subject_id)
    )
    
    return [
        {"name": row[0], "student_id": row[1], "active": row[2]}
        for row in result.all()
    ]
