import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from app.db.session import engine, AsyncSessionLocal
from app.models.models import (
    Base, University, Department, User, Professor, Student,
    Subject, Batch, SubjectBatch, Enrollment, AttendanceSession,
    AttendanceRecord, FaceEmbedding, UserRole, SessionStatus, AttendanceStatus,
    MarkedBy, FaceEnrollmentRequest, EnrollmentRequestStatus, Notification
)
from app.core.security import get_password_hash
from sqlalchemy import text

async def seed():
    print("Starting database seed...")
    async with engine.begin() as conn:
        print("Ensuring pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("Inserting University and Department...")
        uni = University(name="Global Tech University")
        db.add(uni)
        await db.flush()

        dept = Department(name="Computer Science", code="CS", university_id=uni.id)
        db.add(dept)
        await db.flush()

        print("Inserting Professor...")
        prof_user = User(
            email="professor@university.edu",
            password_hash=get_password_hash("password123"),
            role=UserRole.professor,
            full_name="Dr. Alan Turing",
            phone="+1 555-0100",
            avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Alan",
        )
        db.add(prof_user)
        await db.flush()

        prof = Professor(
            user_id=prof_user.id,
            university_id=uni.id,
            department_id=dept.id,
            employee_id="PROF-001",
            designation="Senior Professor",
        )
        db.add(prof)

        print("Inserting Batches and Subjects...")
        batch1 = Batch(name="CS-2026", department_id=dept.id, year=2026, semester=5)
        batch2 = Batch(name="CS-2027", department_id=dept.id, year=2027, semester=3)
        db.add_all([batch1, batch2])
        await db.flush()

        sub1 = Subject(name="Artificial Intelligence", code="CS501", department_id=dept.id, credits=4)
        sub2 = Subject(name="Database Systems", code="CS502", department_id=dept.id, credits=3)
        sub3 = Subject(name="Algorithms", code="CS301", department_id=dept.id, credits=4)
        db.add_all([sub1, sub2, sub3])
        await db.flush()

        sb1 = SubjectBatch(subject_id=sub1.id, batch_id=batch1.id, professor_id=prof.user_id, academic_year="2026")
        sb2 = SubjectBatch(subject_id=sub2.id, batch_id=batch1.id, professor_id=prof.user_id, academic_year="2026")
        sb3 = SubjectBatch(subject_id=sub3.id, batch_id=batch2.id, professor_id=prof.user_id, academic_year="2026")
        db.add_all([sb1, sb2, sb3])
        await db.flush()

        print("Inserting 20 Students...")
        students = []
        for i in range(1, 21):
            user = User(
                email=f"student{i}@university.edu",
                password_hash=get_password_hash("password123"),
                role=UserRole.student,
                full_name=f"Demo Student {i}",
                phone=f"+1 555-{i:04d}",
                avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed=Student{i}",
            )
            db.add(user)
            await db.flush()

            # Make 18 students approved, 2 pending
            is_approved = i <= 18
            
            student = Student(
                user_id=user.id,
                university_id=uni.id,
                department_id=dept.id,
                batch_id=batch1.id if i <= 10 else batch2.id,
                student_id=f"STU-2026-{i:03d}",
                year_of_study=3 if i <= 10 else 2,
                is_face_enrolled=is_approved,
                is_face_approved=is_approved,
                enrollment_locked=is_approved,
                last_approved_at=datetime.now(timezone.utc) if is_approved else None,
            )
            db.add(student)
            students.append((user, student))
            
            # Enroll in subjects
            batch_assigned = batch1.id if i <= 10 else batch2.id
            if batch_assigned == batch1.id:
                db.add(Enrollment(student_id=user.id, subject_batch_id=sb1.id))
                db.add(Enrollment(student_id=user.id, subject_batch_id=sb2.id))
            else:
                db.add(Enrollment(student_id=user.id, subject_batch_id=sb3.id))

            # Face Embedding
            if is_approved:
                # generate random 512-dim vector for pgvector
                vector = [random.uniform(-1, 1) for _ in range(512)]
                norm = sum(x**2 for x in vector) ** 0.5
                vector = [x/norm for x in vector]

                db.add(FaceEmbedding(
                    student_id=user.id,
                    embedding=vector,
                    quality_score=0.95,
                    model_version="buffalo_l_v1"
                ))
            else:
                db.add(FaceEnrollmentRequest(
                    student_id=user.id,
                    subject_batch_id=sb1.id if batch_assigned == batch1.id else sb3.id,
                    status=EnrollmentRequestStatus.pending_approval,
                    quality_score=0.92,
                ))
        
        await db.flush()

        print("Inserting Attendance Sessions and Records...")
        # 5 past sessions for sb1
        for day in range(5, 0, -1):
            sess_date = datetime.now(timezone.utc) - timedelta(days=day)
            session = AttendanceSession(
                subject_batch_id=sb1.id,
                status=SessionStatus.finalized,
                is_finalized=True,
                started_at=sess_date,
                finalized_at=sess_date + timedelta(hours=1)
            )
            db.add(session)
            await db.flush()

            # Add records for first 10 students (batch 1)
            for u, s in students[:10]:
                if s.is_face_approved:
                    status = AttendanceStatus.present if random.random() > 0.15 else AttendanceStatus.absent
                    db.add(AttendanceRecord(
                        session_id=session.id,
                        student_id=u.id,
                        status=status,
                        marked_by=MarkedBy.ai,
                        face_confidence=random.uniform(0.85, 0.99) if status == AttendanceStatus.present else None,
                        marked_at=sess_date + timedelta(minutes=random.randint(5, 55))
                    ))
        
        await db.commit()
        print("Seed complete! Use professor@university.edu and student1@university.edu (password: password123)")

if __name__ == "__main__":
    asyncio.run(seed())
