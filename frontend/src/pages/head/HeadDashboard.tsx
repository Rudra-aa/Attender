import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { apiClient } from '../../api/client';

export default function HeadDashboard() {
  const { user, logout } = useAuthStore();

  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ['head-overview'],
    queryFn: async () => (await apiClient.get('/head/overview')).data,
  });

  const { data: atRisk = [], isLoading: loadingRisk } = useQuery({
    queryKey: ['head-at-risk'],
    queryFn: async () => (await apiClient.get('/head/students/at-risk')).data,
  });

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Top Nav */}
      <header className="sticky top-0 z-20 bg-bg-primary/80 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center">
              <span className="text-white text-xs font-bold">A</span>
            </div>
            <span className="font-semibold text-white">Attender Intelligence</span>
          </div>
          <button onClick={logout} className="text-sm text-slate-400 hover:text-white transition-colors">
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-2xl font-bold text-white">University Analytics</h1>
            <p className="text-slate-400 mt-1 text-sm">Institution-wide attendance metrics and risk analysis</p>
          </div>
          <button className="btn-secondary text-sm">Export Report</button>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-4 gap-4">
          <div className="stat-card">
            <p className="text-3xl font-bold text-white">
              {loadingOverview ? '...' : overview?.total_students?.toLocaleString() || 0}
            </p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Total Students</p>
          </div>
          <div className="stat-card">
            <p className="text-3xl font-bold text-white">
              {loadingOverview ? '...' : overview?.total_subjects?.toLocaleString() || 0}
            </p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Active Subjects</p>
          </div>
          <div className="stat-card">
            <p className="text-3xl font-bold text-brand-light">
              {loadingOverview ? '...' : `${overview?.avg_attendance_pct || 0}%`}
            </p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Average Attendance</p>
          </div>
          <div className="stat-card border-danger/30">
            <p className="text-3xl font-bold text-danger">
              {loadingOverview ? '...' : overview?.open_fraud_alerts || 0}
            </p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Open Fraud Alerts</p>
          </div>
        </div>

        {/* At Risk Table */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">University-Wide At-Risk Students</h2>
          {loadingRisk ? (
            <p className="text-slate-500 text-sm">Loading data...</p>
          ) : atRisk.length === 0 ? (
            <p className="text-slate-500 text-sm">No students at risk. Everything is perfect!</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-bg-elevated text-slate-400">
                  <tr>
                    <th className="px-4 py-3 rounded-tl-lg font-medium">Student Name</th>
                    <th className="px-4 py-3 font-medium">Department</th>
                    <th className="px-4 py-3 font-medium">Subject</th>
                    <th className="px-4 py-3 font-medium">Attendance</th>
                    <th className="px-4 py-3 rounded-tr-lg font-medium">Threshold</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {atRisk.map((r: any, idx: number) => (
                    <tr key={idx} className="hover:bg-bg-elevated/50 transition-colors">
                      <td className="px-4 py-3 font-medium text-white">{r.student_name}</td>
                      <td className="px-4 py-3">{r.department}</td>
                      <td className="px-4 py-3">{r.subject}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${r.attendance_pct < 60 ? 'bg-danger/20 text-danger' : 'bg-warning/20 text-warning'}`}>
                          {r.attendance_pct}%
                        </span>
                      </td>
                      <td className="px-4 py-3">{r.threshold}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
