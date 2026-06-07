import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';

// Layouts
import ProfessorLayout from './components/layout/ProfessorLayout';
import StudentLayout from './components/layout/StudentLayout';

// Auth
import LoginPage from './pages/auth/Login';

// Professor
import ProfessorDashboard from './pages/professor/ProfessorDashboard';
import MySubjects from './pages/professor/MySubjects';
import ProfessorProfile from './pages/professor/ProfessorProfile';
import TakeAttendance from './pages/professor/TakeAttendance';
import AttendanceDraft from './pages/professor/AttendanceDraft';
import SessionManagement from './pages/professor/SessionManagement';
import SessionRecords from './pages/professor/SessionRecords';
import EnrollmentPanel from './pages/professor/EnrollmentPanel';

// Student
import StudentDashboard from './pages/student/StudentDashboard';
import StudentProfile from './pages/student/StudentProfile';
import AttendanceHistory from './pages/student/AttendanceHistory';
import FaceEnrollment from './pages/student/FaceEnrollment';

// Head
import HeadDashboard from './pages/head/HeadDashboard';

function RequireAuth({ children, role }: { children: React.ReactNode; role?: string }) {
  const { isAuthenticated, user } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role && user?.role !== role) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const { user, isAuthenticated } = useAuthStore();

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={
          isAuthenticated
            ? <Navigate to={`/${user?.role}`} replace />
            : <LoginPage />
        }
      />

      {/* Professor Routes - Wrapped in ProfessorLayout */}
      <Route path="/professor/*" element={
        <RequireAuth role="professor">
          <ProfessorLayout>
            <Routes>
              <Route path="" element={<ProfessorDashboard />} />
              <Route path="subjects" element={<MySubjects />} />
              <Route path="profile" element={<ProfessorProfile />} />
              <Route path="take-attendance/:subjectId" element={<TakeAttendance />} />
              <Route path="draft/:sessionId" element={<AttendanceDraft />} />
              <Route path="session/:sessionId/records" element={<SessionRecords />} />
              <Route path="sessions" element={<SessionManagement />} />
              <Route path="enrollments" element={<EnrollmentPanel />} />
              <Route path="*" element={<Navigate to="/professor" replace />} />
            </Routes>
          </ProfessorLayout>
        </RequireAuth>
      } />

      {/* Student Routes - Wrapped in StudentLayout */}
      <Route path="/student/*" element={
        <RequireAuth role="student">
          <StudentLayout>
            <Routes>
              <Route path="" element={<StudentDashboard />} />
              <Route path="profile" element={<StudentProfile />} />
              <Route path="history" element={<AttendanceHistory />} />
              <Route path="enroll" element={<FaceEnrollment />} />
              <Route path="*" element={<Navigate to="/student" replace />} />
            </Routes>
          </StudentLayout>
        </RequireAuth>
      } />

      {/* Head */}
      <Route path="/head" element={<RequireAuth role="head"><HeadDashboard /></RequireAuth>} />

      {/* Fallback */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
