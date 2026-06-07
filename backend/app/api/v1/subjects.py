"""Subject management endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.core.security import require_professor
from app.models.models import User, Subject, Professor

router = APIRouter()

class SubjectCreate(BaseModel):
    name: str
    code: str
    semester: int
    academic_year: str
    credits: int = 3
    attendance_threshold: float = 75.0

@router.post("/")
async def create_subject(
    payload: SubjectCreate,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    prof_res = await db.execute(select(Professor).where(Professor.user_id == current_user.id))
    prof = prof_res.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=400, detail="Professor profile incomplete")

    subject = Subject(
        department_id=prof.department_id,
        name=payload.name,
        code=payload.code,
        credits=payload.credits,
        attendance_threshold=payload.attendance_threshold
    )
    db.add(subject)
    await db.flush()

    from app.models.models import Batch, SubjectBatch
    batch_res = await db.execute(select(Batch).where(
        Batch.department_id == prof.department_id,
        Batch.semester == payload.semester
    ))
    batch = batch_res.scalars().first()
    if not batch:
        year = (payload.semester + 1) // 2
        batch = Batch(
            name=f"Semester {payload.semester}",
            department_id=prof.department_id,
            year=year,
            semester=payload.semester
        )
        db.add(batch)
        await db.flush()

    sb = SubjectBatch(
        subject_id=subject.id,
        batch_id=batch.id,
        professor_id=current_user.id,
        academic_year=payload.academic_year,
        is_active=True
    )
    db.add(sb)
    await db.commit()
    return {"id": str(sb.id), "message": "Subject created"}

@router.patch("/{subject_batch_id}/archive")
async def archive_subject(
    subject_batch_id: UUID,
    current_user: User = Depends(require_professor),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import SubjectBatch
    result = await db.execute(
        select(SubjectBatch).where(
            SubjectBatch.id == subject_batch_id,
            SubjectBatch.professor_id == current_user.id
        )
    )
    sb = result.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=404, detail="Subject batch not found or access denied")
    
    sb.is_active = False
    await db.commit()
    return {"message": "Subject archived successfully"}
