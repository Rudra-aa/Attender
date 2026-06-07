import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { apiClient } from '../../api/client';

interface Subject {
  id: string;
  name: string;
  code: string;
  semester: number;
  is_active: boolean;
}

export default function ProfessorDashboard() {
  const { user } = useAuthStore();

  const { data: subjects = [], isLoading } = useQuery<Subject[]>({
    queryKey: ['professor-subjects'],
    queryFn: async () => (await apiClient.get('/professor/subjects')).data,
  });

  const { data: enrollmentCount } = useQuery<{ pending_count: number }>({
    queryKey: ['enrollment-count'],
    queryFn: async () => (await apiClient.get('/enrollment/count')).data,
    refetchInterval: 60_000,
  });

  const pendingCount = enrollmentCount?.pending_count ?? 0;
  const activeSubjects = subjects.filter(s => s.is_active);

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Good day, {user?.fullName?.split(' ')[0]}</h1>
        <p className="text-slate-400 mt-1 text-sm">Here is what's happening today.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 border-l-4 border-l-brand">
          <p className="text-sm text-slate-400 mb-1">Active Subjects</p>
          <h2 className="text-3xl font-bold text-white">{activeSubjects.length}</h2>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-warning">
          <p className="text-sm text-slate-400 mb-1">Pending Enrollments</p>
          <h2 className="text-3xl font-bold text-white">{pendingCount}</h2>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-success">
          <p className="text-sm text-slate-400 mb-1">Total Students</p>
          <h2 className="text-3xl font-bold text-white">-</h2>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Quick Actions</h2>
        
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => <div key={i} className="h-40 rounded-xl bg-bg-elevated animate-pulse" />)}
          </div>
        ) : activeSubjects.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <div className="text-5xl mb-4">📚</div>
            <h2 className="font-semibold text-white mb-2">No subjects yet</h2>
            <p className="text-slate-400 text-sm mb-6">Create your first subject from the My Subjects page.</p>
            <Link to="/professor/subjects" className="btn-primary">
              Manage Subjects
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeSubjects.map((subject) => (
              <div key={subject.id} className="glass-card p-6 hover:border-brand/40 transition-all group flex flex-col justify-between h-40">
                <div>
                  <p className="text-xs text-brand-light font-medium mb-1">{subject.code} · Sem {subject.semester}</p>
                  <h3 className="font-bold text-white text-lg leading-tight">{subject.name}</h3>
                </div>

                <Link
                  to={`/professor/take-attendance/${subject.id}`}
                  className="btn-primary w-full text-sm flex items-center justify-center gap-2 py-2 mt-4"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Take Attendance
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
