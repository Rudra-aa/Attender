import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface EnrollmentRequest {
  request_id: string;
  student_id: string;
  student_name: string;
  student_roll: string;
  subject_id: string;
  subject_name: string;
  subject_code: string;
  semester: number;
  year_of_study: number;
  status: string;
  quality_score: number | null;
  created_at: string;
  reference_photo: string | null;
}

interface RequestDetail {
  request_id: string;
  status: string;
  quality_score: number | null;
  created_at: string;
  student: {
    id: string;
    name: string;
    roll: string;
    year_of_study: number;
    is_face_approved: boolean;
    enrollment_locked: boolean;
  };
  subject: { id: string; semester: number };
  angle_photos: Record<string, string>;
  angles_captured: string[];
  rejected_reason: string | null;
  approved_at: string | null;
}

const ANGLE_LABELS: Record<string, string> = {
  front: '😐 Straight',
  left:  '👈 Left',
  right: '👉 Right',
  up:    '👆 Up',
  down:  '👇 Down',
};

export default function EnrollmentPanel() {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailRequest, setDetailRequest] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('Photo quality not acceptable. Please re-enroll.');
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const showNotification = (type: 'success' | 'error', msg: string) => {
    setNotification({ type, msg });
    setTimeout(() => setNotification(null), 4000);
  };

  const { data: profile } = useQuery({
    queryKey: ['professor-profile'],
    queryFn: async () => (await apiClient.get('/professor/me')).data,
  });

  const { data: requests = [], isLoading } = useQuery<EnrollmentRequest[]>({
    queryKey: ['enrollment-pending'],
    queryFn: async () => (await apiClient.get('/enrollment/pending')).data,
    refetchInterval: 30_000,
  });

  const { data: detail, isLoading: detailLoading } = useQuery<RequestDetail>({
    queryKey: ['enrollment-detail', detailRequest],
    queryFn: async () => (await apiClient.get(`/enrollment/${detailRequest}`)).data,
    enabled: !!detailRequest,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['enrollment-pending'] });
    if (detailRequest) queryClient.invalidateQueries({ queryKey: ['enrollment-detail', detailRequest] });
  };

  const settingsMutation = useMutation({
    mutationFn: async (autoApprove: boolean) =>
      (await apiClient.patch('/professor/settings', { auto_approve_enrollments: autoApprove })).data,
    onSuccess: (data) => {
      showNotification('success', `Auto-Approval is now ${data.auto_approve_enrollments ? 'ON' : 'OFF'}`);
      queryClient.invalidateQueries({ queryKey: ['professor-profile'] });
    },
    onError: () => showNotification('error', 'Failed to update settings'),
  });

  const approveMutation = useMutation({
    mutationFn: async (id: string) => (await apiClient.post(`/enrollment/${id}/approve`)).data,
    onSuccess: (_, id) => {
      showNotification('success', 'Enrollment approved successfully');
      setSelectedIds((s) => { const n = new Set(s); n.delete(id); return n; });
      if (detailRequest === id) setDetailRequest(null);
      invalidate();
    },
    onError: (err: any) => showNotification('error', err?.response?.data?.detail || 'Approve failed'),
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) =>
      (await apiClient.post(`/enrollment/${id}/reject`, { reason })).data,
    onSuccess: (_, { id }) => {
      showNotification('success', 'Enrollment rejected');
      setRejectTarget(null);
      setSelectedIds((s) => { const n = new Set(s); n.delete(id); return n; });
      if (detailRequest === id) setDetailRequest(null);
      invalidate();
    },
    onError: (err: any) => showNotification('error', err?.response?.data?.detail || 'Reject failed'),
  });

  const bulkApproveMutation = useMutation({
    mutationFn: async (ids: string[]) =>
      (await apiClient.post('/enrollment/bulk-approve', { request_ids: ids })).data,
    onSuccess: (data) => {
      showNotification('success', `${data.approved_count} enrollments approved`);
      setSelectedIds(new Set());
      invalidate();
    },
    onError: (err: any) => showNotification('error', err?.response?.data?.detail || 'Bulk approve failed'),
  });

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === requests.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(requests.map(r => r.request_id)));
  };

  const getQualityColor = (score: number | null) => {
    if (!score) return 'text-slate-400';
    if (score >= 85) return 'text-success';
    if (score >= 70) return 'text-warning';
    return 'text-danger';
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Notification toast */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl text-sm font-medium shadow-xl animate-slide-up
          ${notification.type === 'success' ? 'bg-success/20 border border-success/30 text-success' : 'bg-danger/20 border border-danger/30 text-danger'}`}>
          {notification.msg}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/professor" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="font-semibold text-white">Enrollment Approvals</h1>
              <p className="text-xs text-slate-500">
                {requests.length} pending request{requests.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Auto-Approve Toggle */}
            <div className="flex items-center gap-3 bg-bg-elevated/50 px-4 py-2 rounded-xl border border-border-subtle">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-white">AI Auto-Approval</span>
                <span className="text-xs text-slate-400">Accept good photos instantly</span>
              </div>
              <button
                onClick={() => {
                  if (profile) settingsMutation.mutate(!profile.auto_approve_enrollments);
                }}
                disabled={!profile || settingsMutation.isPending}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  profile?.auto_approve_enrollments ? 'bg-brand' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    profile?.auto_approve_enrollments ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {/* Bulk Actions */}
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-400">{selectedIds.size} selected</span>
                <button
                  onClick={() => bulkApproveMutation.mutate(Array.from(selectedIds))}
                  disabled={bulkApproveMutation.isPending}
                  className="btn-primary text-sm py-2 px-4 flex items-center gap-2"
                  id="bulk-approve-btn"
                >
                  {bulkApproveMutation.isPending ? (
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : '✓'} Approve All Selected
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="h-20 rounded-xl bg-bg-elevated animate-pulse" />)}
          </div>
        ) : requests.length === 0 ? (
          <div className="glass-card p-16 text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-xl font-bold text-white mb-2">All caught up!</h2>
            <p className="text-slate-400 text-sm">No pending enrollment requests for your subjects.</p>
          </div>
        ) : (
          <div className="glass-card overflow-hidden">
            {/* Table header */}
            <div className="flex items-center gap-3 px-5 py-3 border-b border-border-subtle bg-bg-elevated/50">
              <input
                type="checkbox"
                id="select-all-checkbox"
                checked={selectedIds.size === requests.length && requests.length > 0}
                onChange={selectAll}
                className="w-4 h-4 rounded accent-brand cursor-pointer"
              />
              <span className="text-xs text-slate-500 uppercase tracking-wide">Select All</span>
            </div>

            {/* Table rows */}
            <div className="divide-y divide-border-subtle">
              {requests.map((req) => (
                <div
                  key={req.request_id}
                  className={`flex items-center gap-4 px-5 py-4 hover:bg-bg-elevated/40 transition-colors ${
                    selectedIds.has(req.request_id) ? 'bg-brand/5' : ''
                  }`}
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedIds.has(req.request_id)}
                    onChange={() => toggleSelect(req.request_id)}
                    className="w-4 h-4 rounded accent-brand cursor-pointer flex-shrink-0"
                  />

                  {/* Reference photo */}
                  {req.reference_photo ? (
                    <img
                      src={req.reference_photo}
                      alt={req.student_name}
                      className="w-12 h-12 rounded-xl object-cover border border-border-subtle flex-shrink-0"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-xl bg-brand/15 flex items-center justify-center flex-shrink-0 text-brand font-bold">
                      {req.student_name[0]}
                    </div>
                  )}

                  {/* Student info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white text-sm">{req.student_name}</p>
                    <p className="text-xs text-slate-500">{req.student_roll} · {req.subject_name} ({req.subject_code})</p>
                  </div>

                  {/* Quality */}
                  <div className="text-right hidden sm:block">
                    <p className={`font-bold text-sm ${getQualityColor(req.quality_score)}`}>
                      {req.quality_score?.toFixed(1) ?? '—'}/100
                    </p>
                    <p className="text-xs text-slate-500">Quality</p>
                  </div>

                  {/* Status badge */}
                  <div className="hidden sm:block">
                    {req.status === 're_enrollment'
                      ? <span className="badge-warning text-xs">Re-Enroll</span>
                      : <span className="badge-absent text-xs">Pending</span>
                    }
                  </div>

                  {/* Date */}
                  <p className="text-xs text-slate-500 hidden md:block">{formatDate(req.created_at)}</p>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      id={`view-${req.request_id}`}
                      onClick={() => setDetailRequest(req.request_id)}
                      className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-bg-elevated transition-all text-xs"
                      title="View details"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      id={`approve-${req.request_id}`}
                      onClick={() => approveMutation.mutate(req.request_id)}
                      disabled={approveMutation.isPending}
                      className="px-3 py-1.5 rounded-lg bg-success/15 text-success hover:bg-success/25 transition-all text-xs font-medium"
                    >
                      Approve
                    </button>
                    <button
                      id={`reject-${req.request_id}`}
                      onClick={() => setRejectTarget(req.request_id)}
                      className="px-3 py-1.5 rounded-lg bg-danger/10 text-danger hover:bg-danger/20 transition-all text-xs font-medium"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ── Detail Modal ────────────────────────────────────────────────────── */}
      {detailRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
            <div className="flex items-center justify-between p-6 border-b border-border-subtle">
              <h2 className="text-lg font-bold text-white">Enrollment Review</h2>
              <button
                onClick={() => setDetailRequest(null)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {detailLoading ? (
              <div className="p-12 text-center">
                <svg className="animate-spin w-8 h-8 text-brand mx-auto" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
            ) : detail ? (
              <div className="p-6 space-y-5">
                {/* Student info */}
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-brand/20 flex items-center justify-center text-2xl font-bold text-brand">
                    {detail.student.name[0]}
                  </div>
                  <div>
                    <p className="font-semibold text-white">{detail.student.name}</p>
                    <p className="text-sm text-slate-400">{detail.student.roll} · Year {detail.student.year_of_study}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs ${getQualityColor(detail.quality_score)}`}>
                        Quality: {detail.quality_score?.toFixed(1)}/100
                      </span>
                      <span className="text-slate-600">·</span>
                      <span className="badge-absent text-xs capitalize">{detail.status.replace('_', ' ')}</span>
                    </div>
                  </div>
                </div>

                {/* Angle photos grid */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Face Photos — {detail.angles_captured.length}/5 angles</h3>
                  <div className="grid grid-cols-5 gap-2">
                    {(['front', 'left', 'right', 'up', 'down'] as const).map((angle) => (
                      <div key={angle} className="text-center">
                        {detail.angle_photos[angle] ? (
                          <img
                            src={detail.angle_photos[angle]}
                            alt={angle}
                            className="w-full aspect-square object-cover rounded-lg border border-border-subtle"
                          />
                        ) : (
                          <div className="w-full aspect-square rounded-lg bg-bg-elevated border border-border-subtle flex items-center justify-center text-slate-600 text-xs">
                            N/A
                          </div>
                        )}
                        <p className="text-xs text-slate-500 mt-1">{ANGLE_LABELS[angle]}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => { setRejectTarget(detailRequest); setDetailRequest(null); }}
                    className="btn-secondary flex-1 text-sm text-danger border-danger/30 hover:bg-danger/10"
                  >
                    Reject
                  </button>
                  <button
                    id={`modal-approve-${detailRequest}`}
                    onClick={() => { approveMutation.mutate(detailRequest); setDetailRequest(null); }}
                    disabled={approveMutation.isPending}
                    className="btn-primary flex-1 text-sm"
                  >
                    ✓ Approve Enrollment
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ── Reject Modal ─────────────────────────────────────────────────────── */}
      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="glass-card w-full max-w-sm p-6 animate-slide-up">
            <h2 className="text-lg font-bold text-white mb-2">Reject Enrollment</h2>
            <p className="text-slate-400 text-sm mb-4">Provide a reason so the student knows how to improve.</p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="input w-full resize-none mb-4"
              placeholder="Reason for rejection..."
            />
            <div className="flex gap-3">
              <button onClick={() => setRejectTarget(null)} className="btn-secondary flex-1 text-sm">
                Cancel
              </button>
              <button
                id="confirm-reject-btn"
                onClick={() => rejectMutation.mutate({ id: rejectTarget, reason: rejectReason })}
                disabled={rejectMutation.isPending}
                className="flex-1 py-2.5 px-4 rounded-xl bg-danger/15 text-danger hover:bg-danger/25 transition-all text-sm font-medium"
              >
                {rejectMutation.isPending ? 'Rejecting...' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
