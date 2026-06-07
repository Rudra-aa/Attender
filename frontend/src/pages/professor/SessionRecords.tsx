import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../../api/client';

interface RecordItem {
  name: string;
  roll: string;
  status: string;
  marked_by: string;
  confidence: number | null;
  marked_at: string;
}

interface DisputeItem {
  id: string;
  reason: string;
  status: string;
  raised_at: string;
  student_name: string;
  roll: string;
  subject: string;
  class_date: string;
  original_status: string;
}

export default function SessionRecords() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const queryClient = useQueryClient();

  // 1. Fetch records
  const { data: records = [], isLoading: recordsLoading } = useQuery<RecordItem[]>({
    queryKey: ['session-records', sessionId],
    queryFn: async () => (await apiClient.get(`/drafts/${sessionId}/records`)).data,
    enabled: !!sessionId,
  });

  // 2. Fetch professor disputes
  const { data: disputes = [], isLoading: disputesLoading } = useQuery<DisputeItem[]>({
    queryKey: ['professor-disputes'],
    queryFn: async () => (await apiClient.get('/disputes/professor')).data,
  });

  // 3. Resolve dispute mutation
  const resolveDisputeMutation = useMutation({
    mutationFn: async ({ disputeId, status, note }: { disputeId: string; status: 'approved' | 'rejected'; note?: string }) =>
      (await apiClient.patch(`/disputes/${disputeId}/resolve`, { status, professor_note: note })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session-records', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['professor-disputes'] });
    },
  });

  // Filter disputes relevant to this session date/subject if applicable
  // For simplicity, we match by student name and subject if present, or just list all pending disputes for the professor
  const activeDisputes = disputes.filter(d => d.status === 'pending');

  const presentCount = records.filter(r => r.status === 'present').length;
  const absentCount = records.filter(r => r.status === 'absent').length;

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/professor" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="font-semibold text-white">Finalized Attendance Records</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">{sessionId?.slice(0, 8)}...</p>
            </div>
          </div>
          <Link to="/professor" className="btn-secondary text-xs">
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
        {/* KPI Banner */}
        <div className="grid grid-cols-3 gap-4">
          <div className="stat-card text-center">
            <p className="text-3xl font-bold text-white">{records.length}</p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Total Students</p>
          </div>
          <div className="stat-card text-center border-success/20">
            <p className="text-3xl font-bold text-success">{presentCount}</p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Present</p>
          </div>
          <div className="stat-card text-center border-danger/20">
            <p className="text-3xl font-bold text-danger">{absentCount}</p>
            <p className="text-slate-400 text-xs mt-1 uppercase tracking-wide">Absent</p>
          </div>
        </div>

        {/* ── SECTION: DISPUTES / REVIEW REQUESTS ──────────────────────── */}
        {activeDisputes.length > 0 && (
          <div className="glass-card p-6 border-warning/20">
            <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
              <span className="live-dot bg-warning" />
              Pending Attendance Disputes ({activeDisputes.length})
            </h2>
            <div className="space-y-4">
              {activeDisputes.map((disp) => (
                <div key={disp.id} className="p-4 rounded-xl bg-bg-elevated border border-border-subtle space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-white">{disp.student_name} ({disp.roll})</p>
                      <p className="text-xs text-slate-400">Raised for {disp.subject} · {new Date(disp.class_date).toLocaleDateString()}</p>
                    </div>
                    <span className="badge-absent">Marked Absent</span>
                  </div>
                  <div className="p-3 rounded-lg bg-bg-primary text-xs text-slate-300 italic border-l-2 border-brand">
                    "{disp.reason}"
                  </div>
                  <div className="flex gap-2 justify-end pt-2">
                    <button
                      onClick={() => resolveDisputeMutation.mutate({ disputeId: disp.id, status: 'approved', note: 'Approved via review' })}
                      disabled={resolveDisputeMutation.isPending}
                      className="px-4 py-2 rounded-xl text-xs font-semibold bg-success text-white hover:shadow-glow-success transition-all"
                    >
                      Approve (Mark Present)
                    </button>
                    <button
                      onClick={() => resolveDisputeMutation.mutate({ disputeId: disp.id, status: 'rejected', note: 'Rejected: face match not confirmed' })}
                      disabled={resolveDisputeMutation.isPending}
                      className="px-4 py-2 rounded-xl text-xs font-semibold bg-danger/20 text-danger hover:bg-danger/30 transition-all"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── SECTION: RECORDS LIST ────────────────────────────────────── */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold text-white mb-4">Class Attendance Register</h2>
          {recordsLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-12 bg-bg-elevated animate-pulse rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border-subtle text-slate-400 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Student Name</th>
                    <th className="py-3 px-4">Roll Number</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Marked By</th>
                    <th className="py-3 px-4">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle/50 text-sm">
                  {records.map((r, i) => (
                    <tr key={i} className="hover:bg-bg-elevated/40 transition-colors">
                      <td className="py-3.5 px-4 font-medium text-white">{r.name}</td>
                      <td className="py-3.5 px-4 text-slate-400">{r.roll}</td>
                      <td className="py-3.5 px-4">
                        <span className={r.status === 'present' ? 'badge-present' : 'badge-absent'}>
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs font-medium text-slate-300">
                        {r.marked_by === 'ai' ? '🤖 AI Engine' : '👨‍🏫 Professor'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs text-brand-light">
                        {r.confidence ? `${(r.confidence * 100).toFixed(0)}%` : '—'}
                      </td>
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
