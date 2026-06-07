"""Head Dashboard routes — university-level analytics (Cleaned up for V3)"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.db.session import get_db
from app.core.security import require_head
from app.models.models import (
    User, Student, Subject, AttendanceRecord, AttendanceSession,
    Department, AttendanceStatus
)

router = APIRouter()


@router.get("/overview")
async def university_overview(
    current_user: User = Depends(require_head),
    db: AsyncSession = Depends(get_db),
):
    """University-level KPI cards."""
    total_students = (await db.execute(select(func.count(Student.user_id)))).scalar()
    total_subjects = (await db.execute(select(func.count(Subject.id)).where(Subject.is_active == True))).scalar()

    # Average attendance %
    avg_att = await db.execute(
        text("""
            SELECT AVG(attendance_percentage)
            FROM student_subject_attendance
        """)
    )
    avg_pct = avg_att.scalar() or 0.0

    return {
        "total_students": total_students,
        "total_subjects": total_subjects,
        "avg_attendance_pct": round(float(avg_pct), 2),
        "open_fraud_alerts": 0, # Fraud logs removed in V3
    }


@router.get("/departments")
async def department_overview(
    current_user: User = Depends(require_head),
    db: AsyncSession = Depends(get_db),
):
    """Department-level attendance metrics."""
    result = await db.execute(
        text("""
            SELECT
                d.name AS dept_name,
                d.code AS dept_code,
                COUNT(DISTINCT s.user_id) AS student_count,
                ROUND(AVG(ssa.attendance_percentage), 2) AS avg_attendance
            FROM departments d
            LEFT JOIN students s ON s.department_id = d.id
            LEFT JOIN student_subject_attendance ssa ON ssa.student_id = s.user_id
            GROUP BY d.id, d.name, d.code
            ORDER BY avg_attendance DESC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "name": r.dept_name,
            "code": r.dept_code,
            "student_count": r.student_count,
            "avg_attendance": float(r.avg_attendance or 0),
        }
        for r in rows
    ]


@router.get("/students/at-risk")
async def at_risk_students(
    current_user: User = Depends(require_head),
    db: AsyncSession = Depends(get_db),
):
    """Students below attendance threshold in any subject."""
    result = await db.execute(
        text("""
            SELECT
                u.full_name,
                d.name AS department,
                s.name AS subject,
                ssa.attendance_percentage,
                ssa.attendance_threshold
            FROM student_subject_attendance ssa
            JOIN users u ON u.id = ssa.student_id
            JOIN subjects s ON s.id = ssa.subject_id
            JOIN students st ON st.user_id = ssa.student_id
            JOIN departments d ON d.id = st.department_id
            WHERE ssa.is_at_risk = TRUE
            ORDER BY ssa.attendance_percentage ASC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "student_name": r.full_name,
            "department": r.department,
            "subject": r.subject,
            "attendance_pct": float(r.attendance_percentage),
            "threshold": float(r.attendance_threshold),
        }
        for r in rows
    ]


@router.get("/fraud/reports")
async def fraud_reports():
    """Deprecated in V3."""
    return []


@router.get("/trends")
async def attendance_trends(
    current_user: User = Depends(require_head),
    db: AsyncSession = Depends(get_db),
):
    """30-day daily attendance rate for trend charts."""
    result = await db.execute(
        text("""
            SELECT
                DATE(ar.marked_at) AS date,
                COUNT(*) FILTER (WHERE ar.status IN ('present','late')) AS present_count,
                COUNT(*) AS total_count,
                ROUND(COUNT(*) FILTER (WHERE ar.status IN ('present','late'))::decimal / NULLIF(COUNT(*),0) * 100, 2) AS rate
            FROM attendance_records ar
            WHERE ar.marked_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(ar.marked_at)
            ORDER BY date ASC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "date": str(r.date),
            "present": r.present_count,
            "total": r.total_count,
            "rate": float(r.rate or 0)
        }
        for r in rows
    ]
