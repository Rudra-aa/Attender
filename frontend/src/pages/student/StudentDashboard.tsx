import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { apiClient } from '../../api/client';
import StudentOnboarding from './StudentOnboarding';

interface EnrollmentStatus {
  is_face_enrolled: boolean;
  is_face_approved: boolean;
  enrollment_locked: boolean;
  pending_request: { id: string; status: string; quality_score: number | null } | null;
}

interface SubjectAttendance {
  subject: string;
  pct: number;
  total: number;
  attended: number;
  threshold: number;
  at_risk: boolean;
}

interface ActiveSession {
  id: string;
  subject_batch_id: string;
  status: string;
  scheduled_end: string;
}

export default function StudentDashboard() {
  const { user } = useAuthStore();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => (await apiClient.get('/students/me')).data,
  });

  const { data: subjects = [], isLoading: subjectsLoading } = useQuery<SubjectAttendance[]>({
    queryKey: ['student-subjects'],
    queryFn: async () => (await apiClient.get('/students/me/attendance/subjects')).data,
    enabled: !!profile?.batch_id,
  });

  const { data: activeSessions = [] } = useQuery<ActiveSession[]>({
    queryKey: ['active-sessions'],
    queryFn: async () => (await apiClient.get('/attendance/sessions/active')).data,
    refetchInterval: 30_000,
  });

  const { data: enrollmentStatus } = useQuery<EnrollmentStatus>({
    queryKey: ['enrollment-status'],
    queryFn: async () => (await apiClient.get('/faces/enrollment-status')).data,
  });

  const overallPct = subjects.length
    ? subjects.reduce((s, x) => s + x.pct, 0) / subjects.length
    : 0;

  const atRiskCount = subjects.filter((s) => s.at_risk).length;

  const getHour = () => {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {profile && !profile.batch_id && <StudentOnboarding />}

      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          Good {getHour()}, {user?.fullName?.split(' ')[0]} 👋
        </h1>
        <p className="text-slate-400 mt-1 text-sm">Here's your attendance overview</p>
      </div>

      {/* Active Session Banner */}
      {activeSessions.length > 0 && (
        <div className="relative overflow-hidden rounded-2xl border border-brand/30 bg-brand/10 p-5 animate-slide-up">
          <div className="absolute inset-0 bg-gradient-to-r from-brand/5 to-purple-500/5" />
          <div className="relative flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="live-dot" />
              <div>
                <p className="font-semibold text-white text-sm">Class Session Active</p>
                <p className="text-slate-400 text-xs mt-0.5">
                  Your professor is currently taking classroom attendance. Please remain present.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-white">{overallPct.toFixed(1)}%</p>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Overall</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-white">{subjects.length}</p>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Subjects</p>
        </div>
        <div className={`stat-card text-center ${atRiskCount > 0 ? 'border-danger/30' : ''}`}>
          <p className={`text-3xl font-bold ${atRiskCount > 0 ? 'text-danger' : 'text-success'}`}>
            {atRiskCount}
          </p>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">At Risk</p>
        </div>
      </div>

      {/* Subject List */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-white">Subject-wise Attendance</h2>
          <Link to="/student/history" className="text-xs text-brand-light hover:underline">
            View history →
          </Link>
        </div>

        {subjectsLoading ? (
          <div className="space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 rounded-xl bg-bg-elevated animate-pulse" />
            ))}
          </div>
        ) : subjects.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">
            No subjects enrolled yet. Contact your professor.
          </p>
        ) : (
          <div className="space-y-4">
            {subjects.map((s) => (
              <div key={s.subject} className="animate-fade-in">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-slate-200">{s.subject}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{s.pct.toFixed(1)}%</span>
                    {s.at_risk ? (
                      s.pct < 60
                        ? <span className="badge-absent">🔴 Critical</span>
                        : <span className="badge-warning">⚠️ At Risk</span>
                    ) : (
                      <span className="badge-present">✓ Safe</span>
                    )}
                  </div>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${s.pct}%`,
                      background: s.at_risk
                        ? s.pct < 60 ? '#EF4444' : '#F59E0B'
                        : 'linear-gradient(90deg, #10B981, #059669)',
                    }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-muted">
                  <span>{s.attended}/{s.total} sessions</span>
                  <span>Min: {s.threshold}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/student/history"
          id="quick-disputes-btn"
          className="glass-card p-5 hover:border-brand/30 transition-all group cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-brand/15 flex items-center justify-center mb-3 group-hover:bg-brand/25 transition-colors">
              <svg className="w-5 h-5 text-brand-light" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <p className="font-medium text-white text-sm">Attendance Disputes</p>
            <p className="text-xs text-muted mt-1">Review absences and raise requests</p>
          </div>
        </Link>

        <Link
          to="/student/history"
          id="quick-history-btn"
          className="glass-card p-5 hover:border-brand/30 transition-all group cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center mb-3 group-hover:bg-purple-500/25 transition-colors">
              <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="font-medium text-white text-sm">Attendance History</p>
            <p className="text-xs text-muted mt-1">View full record</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
