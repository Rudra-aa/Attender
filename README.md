# Attender V3 🎓📸

**Professor-Driven AI Classroom Attendance System**

[![Status](https://img.shields.io/badge/Status-Production%20Ready-success)](#)
[![Stack](https://img.shields.io/badge/Stack-React%20%7C%20FastAPI%20%7C%20Supabase-blue)](#)

Attender V3 is a state-of-the-art classroom attendance platform designed to eliminate roll calls. Using localized edge AI models and vector embeddings, professors can mark an entire classroom of 80 students in under 30 seconds simply by uploading a few photos of the class.

---

## 📑 Table of Contents
1. [Overview](#-overview)
2. [Features](#-features)
3. [Architecture](#-architecture)
4. [Folder Structure](#-folder-structure)
5. [Tech Stack](#-tech-stack)
6. [Database Schema](#-database-schema)
7. [SubjectBatch Architecture](#-subjectbatch-architecture)
8. [Workflows](#-workflows)
9. [Installation & Setup](#-installation--setup)
10. [API Summary](#-api-summary)
11. [Security](#-security)
12. [Deployment](#-deployment)
13. [Roadmap](#-roadmap)

---

## 🎯 Overview
Traditional attendance systems are slow, manual, and prone to proxy attendance. Attender V3 shifts the paradigm:
- **Guided Student Enrollment**: Students use a banking-grade guided UI to capture 5 facial angles.
- **AI Vector Search**: The backend utilizes `insightface` and `pgvector` for hyper-fast, highly accurate facial recognition.
- **Professor-in-the-Loop**: The AI creates an attendance *draft*. The professor reviews, overrides if necessary, and finalizes the records.

## ✨ Features
- **Multi-Angle Face Biometrics**: 5-angle guided capture prevents spoofing.
- **Batched AI Analysis**: Processes up to 5 classroom photos simultaneously to handle occlusions and large rooms.
- **Granular RBAC**: Distinct dashboards for Students, Professors, and Department Heads.
- **Dispute Resolution Workflow**: Students can raise flags on their attendance status for manual professor review.
- **Analytics & Exports**: Real-time threshold tracking and CSV exports.

## 🏗 Architecture
Attender uses a decoupled client-server architecture:
- **Frontend**: A React SPA handling complex webcam streams and state management using TanStack Query.
- **Backend**: A FastAPI server running asynchronous SQL queries and managing AI inference via `insightface`.
- **Database**: PostgreSQL hosted on Supabase, leveraging `pgvector` to perform cosine-similarity matches directly inside the database engine.

## 📁 Folder Structure
```text
attender/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route controllers
│   │   ├── core/         # Security, JWT, config
│   │   ├── db/           # SQLAlchemy session and Base
│   │   ├── models/       # ORM Database Models
│   │   └── services/     # AI Engine (InsightFace + ONNX)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios client
│   │   ├── components/   # Shared UI elements
│   │   └── pages/        # Route views (Student, Professor, Head)
│   ├── index.css         # Global Tailwind + Glassmorphic styles
│   └── package.json
└── .env.example          # Environment variable template
```

## 🛠 Tech Stack
- **Frontend**: React 18, Vite, TailwindCSS, React Router, TanStack Query, React-Webcam.
- **Backend**: Python 3.12, FastAPI, SQLAlchemy (Async), Uvicorn.
- **AI & ML**: InsightFace (buffalo_l), ONNXRuntime, OpenCV, NumPy.
- **Database**: PostgreSQL (Supabase) with `pgvector`.

## 🗄 Database Schema
Core entities include:
- `Users` (Base authentication)
- `Students` / `Professors` / `Heads` (Role-specific profiles)
- `Subjects` & `SubjectBatches` (Curriculum structure)
- `Enrollments` & `FaceEnrollmentRequests` (Student onboarding)
- `FaceEmbeddings` (pgvector 512-dimension array)
- `AttendanceSessions`, `AttendanceDrafts`, `AttendanceRecords` (Attendance lifecycle)

## 🔄 SubjectBatch Architecture
To support modern university structures, V3 migrated from a flat `Subject` table to a relational `SubjectBatch` architecture.
- **Subject**: Defines the core curriculum (e.g., "Machine Learning", Code "CS402").
- **Batch**: Defines a cohort of students (e.g., "Section A", Year 3).
- **SubjectBatch**: The bridge table tying a Subject and a Batch to a specific **Professor**. This allows multiple professors to teach different sections of the same subject securely.

## 📈 Workflows

### Enrollment Workflow
1. **Student Onboarding**: Student selects their Department, Year, Semester, and Batch.
2. **Subject Association**: System automatically maps the student to relevant `SubjectBatches`.
3. **Face Capture**: Student completes a guided 5-angle face scan via webcam.
4. **Approval**: Professor reviews the request in their dashboard. Upon approval, the embeddings are committed to the `pgvector` database.

### Attendance Workflow
1. **Session Creation**: Professor creates an active session for a specific `SubjectBatch`.
2. **Image Upload**: Professor uploads photos of the physical classroom.
3. **AI Draft Generation**: The FastAPI backend extracts faces, calculates embeddings, and runs cosine-similarity against enrolled students.
4. **Review**: The Professor sees an organized UI of "Auto-Present", "Needs Review", and "Unknown Faces".
5. **Finalize**: The Professor overrides any mistakes and finalizes the draft into permanent records.

## 🚀 Installation & Setup

### 1. Supabase Setup
1. Create a new Supabase project.
2. Under Database -> Extensions, enable `vector`.

### 2. Environment Variables
Copy the `.env.example` to `.env` in both `frontend` and `backend` (or a single root `.env` if unified) and populate:
```env
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres
SECRET_KEY=your_super_secret_jwt_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Run migrations/seed if needed
python seed.py
uvicorn app.main:app --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Docker Setup (Optional)
A `Dockerfile` is provided for the backend to handle the complex C++ dependencies required by `insightface` and `onnxruntime`.
```bash
docker build -t attender-backend ./backend
docker run -p 8000:8000 --env-file .env attender-backend
```

## 🔌 API Summary
- `/api/v1/auth/*` - Login, registration, and me.
- `/api/v1/students/*` - Onboarding and dashboard metrics.
- `/api/v1/subjects/*` - Subject and batch creation.
- `/api/v1/faces/*` - Guided enrollment capture.
- `/api/v1/enrollment/*` - Professor approval queues.
- `/api/v1/sessions/*` & `/api/v1/drafts/*` - AI attendance generation.

## 🛡 Security
- Complete OAuth2 Bearer token authentication.
- Strict FastAPI Dependency Injection ensures students cannot access professor endpoints.
- `.env` files are ignored, and JWT tokens are securely hashed.
- *Refer to `SECURITY_AUDIT.md` for the full report.*

## 🚢 Deployment
- **Backend**: Can be deployed on AWS ECS, Render, or Railway via the included Dockerfile. Needs 2GB+ RAM for ONNX models.
- **Frontend**: Can be deployed on Vercel, Netlify, or Cloudflare Pages.

## 🗺 Roadmap
- [ ] Implement WebSockets for real-time AI draft generation progress bars.
- [ ] Add mobile application wrap via React Native.
- [ ] Integrate with University LMS platforms (Canvas, Blackboard).
- [ ] Support Liveness Detection during student enrollment.
