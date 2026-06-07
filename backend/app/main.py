"""
Attender V3 — FastAPI Application Factory
Professor-driven AI classroom attendance.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# slowapi removed — not required for MVP demo

from app.config import settings
from app.core.middleware import LoggingMiddleware
from app.db.session import engine
from app.db.base import Base

# API Routers
from app.api.v1 import (
    auth, students, professors, subjects,
    sessions, drafts, faces,
    attendance, head, exports, disputes, enrollment, notifications
)
# analyze is mounted under /sessions prefix alongside sessions router
from app.api.v1 import analyze
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Attender V3 starting...")
    async with engine.begin() as conn:
        # Create extension first (needed for pgvector Vector type)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            print("✅ pgvector extension ensured")
        except Exception as e:
            print(f"⚠️ Failed to ensure pgvector extension (safe if local SQLite): {e}")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables ready")

        # Create student_subject_attendance view
        try:
            await conn.execute(text("""
                CREATE OR REPLACE VIEW student_subject_attendance AS
                SELECT
                    e.student_id AS student_id,
                    sb.subject_id AS subject_id,
                    sub.name AS subject_name,
                    sub.attendance_threshold AS attendance_threshold,
                    COUNT(ses.id) AS total_sessions,
                    COUNT(rec.id) FILTER (WHERE rec.status IN ('present', 'late')) AS attended_sessions,
                    CASE
                        WHEN COUNT(ses.id) = 0 THEN 100.0
                        ELSE ROUND(COUNT(rec.id) FILTER (WHERE rec.status IN ('present', 'late'))::decimal / COUNT(ses.id) * 100, 2)
                    END AS attendance_percentage,
                    CASE
                        WHEN COUNT(ses.id) > 0 AND (COUNT(rec.id) FILTER (WHERE rec.status IN ('present', 'late'))::decimal / COUNT(ses.id) * 100) < sub.attendance_threshold THEN TRUE
                        ELSE FALSE
                    END AS is_at_risk
                FROM enrollments e
                JOIN subject_batches sb ON sb.id = e.subject_batch_id
                JOIN subjects sub ON sub.id = sb.subject_id
                LEFT JOIN attendance_sessions ses ON ses.subject_batch_id = sb.id AND ses.is_finalized = TRUE
                LEFT JOIN attendance_records rec ON rec.session_id = ses.id AND rec.student_id = e.student_id
                WHERE e.is_active = TRUE
                GROUP BY e.student_id, sb.subject_id, sub.name, sub.attendance_threshold;
            """))
            print("✅ Database view student_subject_attendance ensured")
        except Exception as e:
            print(f"⚠️ Failed to create database view student_subject_attendance (safe if SQLite): {e}")

    yield
    await engine.dispose()
    print("👋 Attender V3 shut down")


app = FastAPI(
    title="Attender V3 API",
    description="Professor-driven AI classroom attendance — 80 students in 30 seconds",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

V1 = "/api/v1"

app.include_router(auth.router,       prefix=f"{V1}/auth",       tags=["Auth"])
app.include_router(students.router,   prefix=f"{V1}/students",   tags=["Students"])
app.include_router(professors.router, prefix=f"{V1}/professor",  tags=["Professors"])
app.include_router(subjects.router,   prefix=f"{V1}/subjects",   tags=["Subjects"])
app.include_router(sessions.router,   prefix=f"{V1}/sessions",   tags=["Sessions"])
app.include_router(analyze.router,    prefix=f"{V1}/sessions",   tags=["AI Analysis"])  # POST /sessions/{id}/analyze
app.include_router(drafts.router,     prefix=f"{V1}/drafts",     tags=["Drafts"])
app.include_router(faces.router,      prefix=f"{V1}/faces",      tags=["Face Enrollment"])
app.include_router(enrollment.router, prefix=f"{V1}/enrollment", tags=["Enrollment Approval"])
app.include_router(attendance.router, prefix=f"{V1}/attendance", tags=["Attendance"])
app.include_router(head.router,       prefix=f"{V1}/head",       tags=["Head Dashboard"])
app.include_router(exports.router,    prefix=f"{V1}/exports",    tags=["Exports"])
app.include_router(disputes.router,   prefix=f"{V1}/disputes",   tags=["Disputes"])
app.include_router(notifications.router, prefix=f"{V1}/notifications", tags=["Notifications"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "3.0.0"}
