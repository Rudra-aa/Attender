import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '../../api/client';

interface AttendanceRecord {
  record_id: string;
  status: string;
  marked_at: string;
  marked_by: string;
  confidence: number | null;
  subject: string;
  session_id: string;
}

interface DisputeItem {
  id: string;
  reason: string;
  status: string;
  raised_at: string;
  resolved_at: string | null;
  professor_note: string | null;
  subject: string;
  class_date: string;
}

export default function AttendanceHistory() {
  const queryClient = useQueryClient();
  const [showDisputeModal, setShowDisputeModal] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<AttendanceRecord | null>(null);
  const [disputeReason, setDisputeReason] = useState('');
  const [submitError, setSubmitError] = useState('');

  // 1. Fetch individual attendance records
  const { data: records = [], isLoading: recordsLoading } = useQuery<AttendanceRecord[]>({
    queryKey: ['student-records'],
    queryFn: async () => (await apiClient.get('/students/me/attendance/records')).data,
  });

  // 2. Fetch raised disputes
  const { data: disputes = [], isLoading: disputesLoading } = useQuery<DisputeItem[]>({
    queryKey: ['student-disputes'],
    queryFn: async () => (await apiClient.get('/disputes/student')).data,
  });

  // 3. Submit dispute mutation
  const submitDisputeMutation = useMutation({
    mutationFn: async ({ recordId, reason }: { recordId: string; reason: string }) =>
      (await apiClient.post('/disputes/', { record_id: recordId, reason })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-records'] });
      queryClient.invalidateQueries({ queryKey: ['student-disputes'] });
      setShowDisputeModal(false);
      setSelectedRecord(null);
      setDisputeReason('');
      setSubmitError('');
    },
    onError: (err: any) => {
      setSubmitError(err?.response?.data?.detail || 'Failed to submit dispute.');
    },
  });

  const openDispute = (rec: AttendanceRecord) => {
    setSelectedRecord(rec);
    setShowDisputeModal(true);
  };

  const handleDisputeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!disputeReason.trim()) {
      setSubmitError('Please enter a reason for the review request.');
      return;
    }
    if (selectedRecord) {
      submitDisputeMutation.mutate({ recordId: selectedRecord.record_id, reason: disputeReason });
    }
  };

  const isDisputed = (recordId: string) => {
    return disputes.some(d => d.id === recordId || records.some(r => r.record_id === recordId && disputes.some(d => d.subject === r.subject && new Date(d.class_date).toDateString() === new Date(r.marked_at).toDateString())));
  };

  return (
    <div className="min-h-screen bg-bg-primary pb-16">
      <header className="sticky top-0 z-20 bg-bg-primary/80 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/student" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="font-semibold text-white">Attendance History &amp; Reviews</h1>
          </div>
          <Link to="/student" className="btn-secondary text-xs">Dashboard</Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
        
        {/* ── SECTION: ACTIVE DISPUTES / REVIEWS ──────────────────────── */}
        {disputes.length > 0 && (
          <div className="glass-card p-6">
            <h2 className="text-lg font-bold text-white mb-4">Review Requests</h2>
            <div className="space-y-3">
              {disputes.map((d) => (
                <div key={d.id} className="p-4 rounded-xl bg-bg-elevated border border-border-subtle flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="space-y-1">
                    <p className="font-semibold text-white text-sm">{d.subject}</p>
                    <p className="text-xs text-slate-400">Class Date: {new Date(d.class_date).toLocaleDateString()}</p>
                    <p className="text-xs text-slate-300 italic">"Reason: {d.reason}"</p>
                    {d.professor_note && (
                      <p className="text-xs text-brand-light font-medium">Faculty note: {d.professor_note}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <span className={
                      d.status === 'pending' ? 'badge-warning' :
                      d.status === 'approved' ? 'badge-present' : 'badge-absent'
                    }>
                      {d.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── SECTION: HISTORY LIST ────────────────────────────────────── */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold text-white mb-4">Lecture Records</h2>

          {recordsLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-bg-elevated animate-pulse rounded-xl" />
              ))}
            </div>
          ) : records.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-12">No attendance logs found.</p>
          ) : (
            <div className="space-y-3">
              {records.map((rec) => {
                const disputed = disputes.some(d => d.subject === rec.subject && new Date(d.class_date).toDateString() === new Date(rec.marked_at).toDateString());
                
                return (
                  <div key={rec.record_id} className="flex items-center justify-between p-4 rounded-xl bg-bg-elevated border border-border-subtle hover:border-border-subtle/80 transition-all">
                    <div>
                      <p className="font-semibold text-white text-sm">{rec.subject}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(rec.marked_at).toLocaleString()} · Marked by {rec.marked_by.toUpperCase()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={rec.status === 'present' ? 'badge-present' : 'badge-absent'}>
                        {rec.status.toUpperCase()}
                      </span>
                      {rec.status === 'absent' && !disputed && (
                        <button
                          onClick={() => openDispute(rec)}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand/10 text-brand-light hover:bg-brand/20 transition-all"
                        >
                          Dispute
                        </button>
                      )}
                      {disputed && (
                        <span className="text-xs text-slate-500 font-medium">Under Review</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Dispute Modal */}
      {showDisputeModal && selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-card p-6 w-full max-w-md animate-slide-up">
            <h2 className="text-lg font-bold text-white mb-2">Request Attendance Review</h2>
            <p className="text-xs text-slate-400 mb-4">
              Submit a correction request for {selectedRecord.subject} on {new Date(selectedRecord.marked_at).toLocaleDateString()}.
            </p>

            <form onSubmit={handleDisputeSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Explanation / Reason *
                </label>
                <textarea
                  value={disputeReason}
                  onChange={(e) => setDisputeReason(e.target.value)}
                  className="input min-h-[100px] py-2.5 text-sm"
                  placeholder="e.g. I was sitting in the third row, but AI did not pick up my face crop. Please verify with classroom image."
                  required
                />
              </div>

              {submitError && (
                <p className="text-xs text-danger">{submitError}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowDisputeModal(false); setSelectedRecord(null); setDisputeReason(''); }}
                  className="btn-secondary flex-1 py-2 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitDisputeMutation.isPending}
                  className="btn-primary flex-1 py-2 text-xs font-semibold"
                >
                  {submitDisputeMutation.isPending ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
