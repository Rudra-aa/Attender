"""Exports endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import require_prof_or_head
from app.models.models import User

router = APIRouter()

@router.post("/attendance")
async def export_attendance(
    current_user: User = Depends(require_prof_or_head),
    db: AsyncSession = Depends(get_db)
):
    # Stub: enqueue a celery task to generate the CSV and return a job ID
    return {"message": "Export job queued", "job_id": "12345-mock-job"}

@router.get("/{job_id}")
async def get_export_status(job_id: str):
    return {"status": "processing"}
