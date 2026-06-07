import asyncio
import uuid
from app.db.session import AsyncSessionLocal
from app.models.models import User, University, Department, Professor, Student, UserRole, Subject, Enrollment
from sqlalchemy.future import select

async def seed_subject():
    async with AsyncSessionLocal() as session:
        # Find existing professor and student
        prof = await session.execute(select(User).where(User.email == "professor@test.com"))
        prof_user = prof.scalar_one_or_none()
        
        student = await session.execute(select(User).where(User.email == "student@test.com"))
        student_user = student.scalar_one_or_none()
        
        prof_profile = await session.execute(select(Professor).where(Professor.user_id == prof_user.id))
        prof_p = prof_profile.scalar_one_or_none()
        
        if not prof_user or not student_user or not prof_p:
            print("Base users not found. Run seed.py first.")
            return

        # Check if subject already exists
        subj_res = await session.execute(select(Subject).where(Subject.code == "CS401"))
        subject = subj_res.scalar_one_or_none()
        
        if not subject:
            subject_id = uuid.uuid4()
            subject = Subject(
                id=subject_id,
                professor_id=prof_user.id,
                department_id=prof_p.department_id,
                name="Introduction to Artificial Intelligence",
                code="CS401",
                semester=7,
                academic_year="2026",
                credits=4,
                attendance_threshold=75.0
            )
            session.add(subject)
            print("Created subject CS401")
        else:
            print("Subject already exists.")
            subject_id = subject.id

        # Check if enrollment already exists
        enr_res = await session.execute(select(Enrollment).where(
            (Enrollment.student_id == student_user.id) & 
            (Enrollment.subject_id == subject_id)
        ))
        enrollment = enr_res.scalar_one_or_none()
        
        if not enrollment:
            enrollment_id = uuid.uuid4()
            enrollment = Enrollment(
                id=enrollment_id,
                student_id=student_user.id,
                subject_id=subject_id,
                is_active=True
            )
            session.add(enrollment)
            print("Created enrollment for student.")
        else:
            print("Student is already enrolled.")
        
        await session.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(seed_subject())
