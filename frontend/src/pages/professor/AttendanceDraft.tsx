import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface Candidate {
  student_id: string;
  name: string;
  roll: string;
  confidence: number;
  face_photo: string | null;
}

interface DraftItem {
  draft_id: string;
  student_id: string | null;
  name: string | null;
  roll: string | null;
  confidence: number;
  status: string;
  face_crop: string | null;
  candidates: Candidate[];
}

interface DraftData {
  session_id: string;
  is_finalized: boolean;
  auto_present: DraftItem[];
  needs_review: DraftItem[];
  unknown_faces: DraftItem[];
  not_detected: { student_id: string; name: string; roll: string; face_photo: string | null }[];
}

export default function AttendanceDraft() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [overrideErrors, setOverrideErrors] = useState<Record<string, string>>({});

  const { data: draft, isLoading, error: loadError } = useQuery<DraftData>({
    queryKey: ['draft', sessionId],
    queryFn: async () => (await apiClient.get(`/drafts/${sessionId}`)).data,
    enabled: !!sessionId,
  });

  const overrideMutation = useMutation({
    mutationFn: async ({ draftId, action, studentId }: { draftId: string; action: 'present' | 'absent'; studentId?: string }) =>
      (await apiClient.patch(`/drafts/${draftId}/override`, { action, student_id: studentId })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['draft', sessionId] }),
    onError: (err: any, { draftId }) => {
      setOverrideErrors(p => ({ ...p, [draftId]: err?.response?.data?.detail || 'Override failed' }));
    },
  });

  const addManualMutation = useMutation({
    mutationFn: async ({ studentId, action }: { studentId: string; action: 'present' | 'absent' }) =>
      (await apiClient.post(`/drafts/${sessionId}/add-manual`, { student_id: studentId, action })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['draft', sessionId] }),
  });

  const finalizeMutation = useMutation({
    mutationFn: async () =>
      (await apiClient.post(`/drafts/${sessionId}/finalize`)).data,
    onSuccess: () => {
      navigate(`/professor/session/${sessionId}/records`);
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-center space-y-3">
          <svg className="animate-spin w-10 h-10 text-brand mx-auto" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-slate-400 text-sm">Loading attendance draft...</p>
        </div>
      </div>
    );
  }

  if (loadError || !draft) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="glass-card p-8 text-center max-w-sm">
          <p className="text-danger mb-4">Failed to load draft.</p>
          <Link to="/professor" className="btn-secondary">← Back</Link>
        </div>
      </div>
    );
  }

  // Combine items requiring manual candidate selection
  const reviewItems = [...draft.needs_review, ...draft.unknown_faces];

  return (
    <div className="min-h-screen bg-bg-primary pb-16">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/professor" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="font-semibold text-white">Attendance Review</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">Session: {sessionId?.slice(0, 8)}...</p>
            </div>
          </div>
          <button
            onClick={() => finalizeMutation.mutate()}
            disabled={finalizeMutation.isPending || draft.is_finalized}
            id="finalize-btn"
            className="btn-primary text-sm px-6 disabled:opacity-50"
          >
            {finalizeMutation.isPending ? 'Finalizing...' : draft.is_finalized ? 'Finalized ✓' : 'Finalize & Save'}
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
        {/* Stages Progress Indicator */}
        <div className="grid grid-cols-3 gap-4 border-b border-border-subtle pb-6 text-center">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-brand-light uppercase tracking-wider">Stage 1</span>
            <p className="text-sm font-medium text-white">Auto Marked ({draft.auto_present.length})</p>
          </div>
          <div className="space-y-1">
            <span className="text-xs font-semibold text-warning uppercase tracking-wider text-yellow-400">Stage 2</span>
            <p className="text-sm font-medium text-white">Review Candidates ({reviewItems.length})</p>
          </div>
          <div className="space-y-1">
            <span className="text-xs font-semibold text-danger uppercase tracking-wider text-rose-400">Stage 3</span>
            <p className="text-sm font-medium text-white">Missing Students ({draft.not_detected.length})</p>
          </div>
        </div>

        {finalizeMutation.isError && (
          <div className="p-4 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm">
            {(finalizeMutation.error as any)?.response?.data?.detail || 'Finalization failed.'}
          </div>
        )}

        {/* ── STAGE 1: AUTO PRESENT ────────────────────────────────────── */}
        <div className="glass-card p-6">
          <details className="group">
            <summary className="cursor-pointer font-semibold text-white flex items-center gap-2 list-none">
              <span className="w-2.5 h-2.5 rounded-full bg-success" />
              Stage 1: Automatically Marked Present ({draft.auto_present.length})
              <span className="ml-auto text-xs text-slate-400 font-normal group-open:hidden">Show List ▼</span>
              <span className="ml-auto text-xs text-slate-400 font-normal hidden group-open:inline">Hide List ▲</span>
            </summary>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 animate-fade-in">
              {draft.auto_present.map((item) => (
                <div key={item.draft_id} className="flex items-center justify-between p-3 rounded-xl bg-bg-elevated border border-border-subtle">
                  <div className="flex items-center gap-3">
                    {item.face_crop && (
                      <img src={item.face_crop} alt="" className="w-10 h-10 rounded-lg object-cover border border-border-subtle" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-white">{item.name}</p>
                      <p className="text-xs text-slate-400">{item.roll}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-success font-mono">{(item.confidence * 100).toFixed(0)}% Match</span>
                    <button
                      onClick={() => overrideMutation.mutate({ draftId: item.draft_id, action: 'absent' })}
                      className="text-xs text-danger/70 hover:text-danger font-medium transition-colors"
                    >
                      Override
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>

        {/* ── STAGE 2: REVIEW CANDIDATES (0.75 - 0.90 & UNKNOWN) ────────────────── */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-warning" />
            Stage 2: Match Candidates ({reviewItems.length})
          </h2>
          <p className="text-xs text-slate-400">
            For medium-confidence or unrecognized faces, choose the correct matching student profile below.
          </p>

          {reviewItems.length === 0 ? (
            <div className="p-8 rounded-xl border border-dashed border-border-subtle text-center text-slate-500 text-sm">
              🎉 No candidates to review! Everything was auto-resolved.
            </div>
          ) : (
            <div className="space-y-6">
              {reviewItems.map((item) => (
                <div key={item.draft_id} className="glass-card p-6 border-warning/20">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {/* Captured crop */}
                    <div className="flex flex-col items-center justify-center p-4 bg-bg-elevated rounded-xl border border-border-subtle text-center">
                      <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">Captured Crop</span>
                      {item.face_crop ? (
                        <img src={item.face_crop} alt="crop" className="w-24 h-24 rounded-xl object-cover border-2 border-brand/40 shadow-glow-brand" />
                      ) : (
                        <div className="w-24 h-24 rounded-xl bg-slate-800 flex items-center justify-center text-slate-500">No Image</div>
                      )}
                      <p className="text-xs text-slate-500 mt-2 font-mono">Index: {item.source_image_idx}</p>
                    </div>

                    {/* Candidate choices */}
                    <div className="md:col-span-3 space-y-4">
                      <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Top 3 Student Candidates</span>
                      
                      {item.candidates.length === 0 ? (
                        <div className="text-slate-500 text-sm italic py-4">No matching registered students found.</div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          {item.candidates.map((cand) => (
                            <div key={cand.student_id} className="flex flex-col justify-between p-3 rounded-xl bg-bg-elevated border border-border-subtle hover:border-brand/40 transition-all text-center">
                              <div className="space-y-2">
                                {cand.face_photo ? (
                                  <img src={cand.face_photo} alt="" className="w-14 h-14 rounded-full object-cover mx-auto border border-border-subtle" />
                                ) : (
                                  <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-500 text-xs">No Face</div>
                                )}
                                <div>
                                  <p className="text-sm font-semibold text-white leading-tight truncate">{cand.name}</p>
                                  <p className="text-xs text-slate-500 truncate">{cand.roll}</p>
                                </div>
                                <span className="inline-block text-xs font-semibold text-brand-light font-mono px-2 py-0.5 rounded-full bg-brand/10">
                                  {(cand.confidence * 100).toFixed(0)}% Match
                                </span>
                              </div>
                              <button
                                onClick={() => overrideMutation.mutate({ draftId: item.draft_id, action: 'present', studentId: cand.student_id })}
                                disabled={overrideMutation.isPending}
                                className="btn-secondary w-full py-1.5 text-xs font-medium mt-3"
                              >
                                Select Student
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex justify-between items-center pt-2 border-t border-border-subtle">
                        {overrideErrors[item.draft_id] && (
                          <p className="text-xs text-danger">{overrideErrors[item.draft_id]}</p>
                        )}
                        <button
                          onClick={() => overrideMutation.mutate({ draftId: item.draft_id, action: 'absent' })}
                          disabled={overrideMutation.isPending}
                          className="text-xs text-danger/80 hover:text-danger font-medium ml-auto"
                        >
                          Mark as Unrecognized / Absent
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── STAGE 3: MISSING STUDENTS ────────────────────────────────────── */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-danger" />
            Stage 3: Missing / Not Detected ({draft.not_detected.length})
          </h2>
          <p className="text-xs text-slate-400">
            Enrolled students who were not detected in the classroom images. Double-check and verify if present.
          </p>

          {draft.not_detected.length === 0 ? (
            <div className="p-8 rounded-xl border border-dashed border-border-subtle text-center text-slate-500 text-sm">
              🙌 Perfect attendance! Every enrolled student was detected.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {draft.not_detected.map((student) => (
                <div key={student.student_id} className="flex items-center gap-3 p-3 rounded-xl bg-bg-elevated border border-border-subtle justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    {student.face_photo ? (
                      <img src={student.face_photo} alt="" className="w-10 h-10 rounded-full object-cover border border-border-subtle flex-shrink-0" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 text-xs flex-shrink-0">No Face</div>
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white leading-tight truncate">{student.name}</p>
                      <p className="text-xs text-slate-500 truncate">{student.roll}</p>
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => addManualMutation.mutate({ studentId: student.student_id, action: 'present' })}
                      disabled={addManualMutation.isPending}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-success/15 text-success hover:bg-success/25 transition-all"
                    >
                      Present
                    </button>
                    <button
                      onClick={() => addManualMutation.mutate({ studentId: student.student_id, action: 'absent' })}
                      disabled={addManualMutation.isPending}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-danger/15 text-danger hover:bg-danger/25 transition-all"
                    >
                      Absent
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Finalize footer */}
        <div className="pt-6 border-t border-border-subtle text-center">
          <button
            onClick={() => finalizeMutation.mutate()}
            disabled={finalizeMutation.isPending || draft.is_finalized}
            id="finalize-bottom-btn"
            className="btn-primary py-4 px-12 text-base disabled:opacity-50"
          >
            {finalizeMutation.isPending ? 'Saving attendance...' : 'Finalize & Save Attendance'}
          </button>
          <p className="text-xs text-slate-500 mt-2">
            This compiles finalized attendance records and closes the session.
          </p>
        </div>
      </main>
    </div>
  );
}
