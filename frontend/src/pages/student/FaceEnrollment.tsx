import { useState, useRef, useCallback, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import ErrorBoundary from '../../components/ErrorBoundary';

interface Subject {
  subject_id: string;
  subject_name: string;
  subject_code: string;
  status: string | null;
  request_id: string | null;
  quality_score: number | null;
}

const ANGLES = [
  { id: 'front', label: 'Look Straight', emoji: '😐', instruction: 'Face the camera directly. Keep your face centered.' },
  { id: 'left',  label: 'Turn Left',    emoji: '👈', instruction: 'Slowly turn your head to the LEFT.' },
  { id: 'right', label: 'Turn Right',   emoji: '👉', instruction: 'Slowly turn your head to the RIGHT.' },
  { id: 'up',    label: 'Look Up',      emoji: '👆', instruction: 'Tilt your head slightly UPWARD.' },
  { id: 'down',  label: 'Look Down',    emoji: '👇', instruction: 'Tilt your head slightly DOWNWARD.' },
];

type Stage = 'select-subject' | 'guided-capture' | 'submitting' | 'done' | 'error';

export default function FaceEnrollment() {
  const navigate = useNavigate();
  const webcamRef = useRef<Webcam>(null);

  const [stage, setStage] = useState<Stage>('select-subject');
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);
  const [currentAngleIdx, setCurrentAngleIdx] = useState(0);
  const [countdown, setCountdown] = useState(3);
  const [capturedAngles, setCapturedAngles] = useState<Record<string, string>>({});
  const [errorMsg, setErrorMsg] = useState('');
  const [submittedResult, setSubmittedResult] = useState<any>(null);
  const countdownRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasCapturedRef = useRef(false);

  // Fetch subject enrollment status
  const { data: subjects = [], isLoading } = useQuery<Subject[]>({
    queryKey: ['enrollment-subjects'],
    queryFn: async () => (await apiClient.get('/faces/enrollment-status/subjects')).data,
  });

  // Submit enrollment request
  const submitMutation = useMutation({
    mutationFn: async (data: { subject_id: string; angles: Record<string, string> }) =>
      (await apiClient.post('/faces/enroll/guided', data)).data,
    onSuccess: (data) => {
      setSubmittedResult(data);
      setStage('done');
    },
    onError: (err: any) => {
      setErrorMsg(err?.response?.data?.detail || 'Enrollment failed. Please try again.');
      setStage('error');
    },
  });

  const captureCurrentAngle = useCallback(() => {
    const dataUrl = webcamRef.current?.getScreenshot();
    if (!dataUrl) {
      setErrorMsg('Camera capture failed. Please check camera access.');
      setStage('error');
      return;
    }
    const angle = ANGLES[currentAngleIdx].id;
    setCapturedAngles((prev) => {
      const updated = { ...prev, [angle]: dataUrl };
      // If all angles captured, submit
      if (Object.keys(updated).length === ANGLES.length) {
        setStage('submitting');
        submitMutation.mutate({ subject_id: selectedSubject!.subject_id, angles: updated });
      } else {
        // Safely batch state updates for the next angle
        setCurrentAngleIdx((i) => i + 1);
        setCountdown(3);
      }
      return updated;
    });
  }, [currentAngleIdx, selectedSubject, submitMutation]);

  // Auto-capture countdown logic
  useEffect(() => {
    if (stage !== 'guided-capture') return;
    if (currentAngleIdx >= ANGLES.length) return;

    if (countdown > 0) {
      hasCapturedRef.current = false;
      const timer = setTimeout(() => {
        setCountdown((prev) => prev - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else {
      // countdown is 0
      if (!hasCapturedRef.current) {
        hasCapturedRef.current = true;
        captureCurrentAngle();
      }
    }
  }, [countdown, stage, currentAngleIdx, captureCurrentAngle]);

  const startCapture = (subject: Subject) => {
    setSelectedSubject(subject);
    setCapturedAngles({});
    setCurrentAngleIdx(0);
    setStage('guided-capture');
  };

  const currentAngle = ANGLES[currentAngleIdx];
  const completedCount = Object.keys(capturedAngles).length;

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center gap-4">
          <Link to="/student" className="text-slate-400 hover:text-white transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="font-semibold text-white">Face Enrollment</h1>
            <p className="text-xs text-slate-500">Guided biometric registration</p>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <ErrorBoundary>
        
        {/* ── STAGE: SELECT SUBJECT ───────────────────────────────────────── */}
        {stage === 'select-subject' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-brand/15 flex items-center justify-center">
                  <span className="text-xl">🛡️</span>
                </div>
                <div>
                  <h2 className="font-semibold text-white">Banking-Grade Enrollment</h2>
                  <p className="text-xs text-slate-500">Like Aadhaar / Face ID Setup</p>
                </div>
              </div>
              <div className="space-y-2 text-sm text-slate-400">
                <p>• Continuous video — no manual photos</p>
                <p>• 5 guided angles captured automatically</p>
                <p>• Quality score generated per angle</p>
                <p>• Professor reviews & approves before activation</p>
              </div>
            </div>

            <div className="glass-card p-6">
              <h2 className="font-semibold text-white mb-4">Select Subject to Enroll For</h2>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => <div key={i} className="h-16 rounded-xl bg-bg-elevated animate-pulse" />)}
                </div>
              ) : subjects.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-6">
                  You are not enrolled in any subjects yet.
                </p>
              ) : (
                <div className="space-y-3">
                  {subjects.map((s) => {
                    const isPending = s.status === 'pending_approval';
                    const isReEnrollment = s.status === 're_enrollment';
                    const isApproved = s.status === 'approved';

                    return (
                      <div
                        key={s.subject_id}
                        className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
                          isApproved
                            ? 'border-success/30 bg-success/5'
                            : isPending
                            ? 'border-warning/30 bg-warning/5'
                            : isReEnrollment
                            ? 'border-danger/30 bg-danger/5 hover:border-danger/50 cursor-pointer'
                            : 'border-border-subtle bg-bg-elevated hover:border-brand/40 cursor-pointer'
                        }`}
                        onClick={() => !isPending && !isApproved && startCapture(s)}
                      >
                        <div>
                          <p className="font-medium text-white text-sm">{s.subject_name}</p>
                          <p className="text-xs text-slate-500">{s.subject_code}</p>
                        </div>
                        <div className="text-right">
                          {isApproved ? (
                            <span className="badge-present text-xs">✓ Complete</span>
                          ) : isPending ? (
                            <span className="badge-warning text-xs">⏳ Pending</span>
                          ) : isReEnrollment ? (
                            <button
                              id={`enroll-${s.subject_id}`}
                              onClick={() => startCapture(s)}
                              className="px-3 py-1.5 bg-danger/10 text-danger border border-danger/30 rounded-lg text-xs font-medium hover:bg-danger/20 transition-colors"
                            >
                              ⚠️ Reverify
                            </button>
                          ) : (
                            <button
                              id={`enroll-${s.subject_id}`}
                              onClick={() => startCapture(s)}
                              className="btn-primary text-xs py-1.5 px-3"
                            >
                              Enroll →
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── STAGE: GUIDED CAPTURE ───────────────────────────────────────── */}
        {stage === 'guided-capture' && currentAngle && (
          <div className="space-y-5 animate-fade-in">
            {/* Progress */}
            <div className="glass-card p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-slate-400">Capturing for: <span className="text-white font-medium">{selectedSubject?.subject_name}</span></span>
                <span className="text-sm text-slate-400">{completedCount}/5 angles</span>
              </div>
              <div className="flex gap-2">
                {ANGLES.map((a, i) => (
                  <div
                    key={a.id}
                    className={`flex-1 h-2 rounded-full transition-all ${
                      capturedAngles[a.id]
                        ? 'bg-success'
                        : i === currentAngleIdx
                        ? 'bg-brand animate-pulse'
                        : 'bg-bg-elevated'
                    }`}
                  />
                ))}
              </div>
              <div className="flex justify-between mt-1.5">
                {ANGLES.map((a, i) => (
                  <span key={a.id} className={`text-xs ${
                    capturedAngles[a.id]
                      ? 'text-success'
                      : i === currentAngleIdx
                      ? 'text-brand'
                      : 'text-slate-600'
                  }`}>{a.emoji}</span>
                ))}
              </div>
            </div>

            {/* Webcam + Instruction */}
            <div className="glass-card p-5 space-y-4">
              <div className="text-center">
                <div className="text-5xl mb-2">{currentAngle.emoji}</div>
                <h2 className="text-xl font-bold text-white">{currentAngle.label}</h2>
                <p className="text-slate-400 text-sm mt-1">{currentAngle.instruction}</p>
              </div>

              {/* Webcam */}
              <div className="relative rounded-xl overflow-hidden bg-bg-elevated aspect-video">
                <Webcam
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ facingMode: 'user', width: 640, height: 480 }}
                  className="w-full h-full object-cover"
                  screenshotQuality={0.9}
                  mirrored
                />
                {/* Face guide oval overlay */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-48 h-60 border-2 border-dashed border-brand/60 rounded-full" />
                </div>
                {/* Countdown */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className={`w-20 h-20 rounded-full bg-black/70 flex items-center justify-center transition-transform ${countdown === 0 ? 'scale-125' : ''}`}>
                    <span className="text-4xl font-bold text-white">
                      {countdown > 0 ? countdown : '📸'}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-center text-xs text-slate-500">
                Photo will capture automatically. Hold the pose steady.
              </p>
            </div>
          </div>
        )}

        {/* ── STAGE: SUBMITTING ───────────────────────────────────────────── */}
        {stage === 'submitting' && (
          <div className="glass-card p-12 text-center space-y-6 animate-fade-in">
            <div className="w-20 h-20 rounded-full bg-brand/10 flex items-center justify-center mx-auto">
              <svg className="animate-spin w-10 h-10 text-brand" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Processing Enrollment</h2>
              <p className="text-slate-400 text-sm mt-1">Generating AI face embeddings for all 5 angles...</p>
            </div>
          </div>
        )}

        {/* ── STAGE: DONE ─────────────────────────────────────────────────── */}
        {stage === 'done' && submittedResult && (
          <div className="space-y-4 animate-slide-up">
            <div className="glass-card p-8 text-center border-success/30">
              <div className="w-20 h-20 rounded-full bg-success/15 flex items-center justify-center mx-auto mb-4">
                <svg className="w-10 h-10 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-white">Enrollment Submitted!</h2>
              <p className="text-slate-400 text-sm mt-2">
                Your face data is pending professor review.
              </p>
            </div>

            <div className="glass-card p-5 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Quality Score</span>
                <span className={`font-bold text-lg ${
                  submittedResult.quality_score >= 85 ? 'text-success' :
                  submittedResult.quality_score >= 70 ? 'text-warning' : 'text-danger'
                }`}>
                  {submittedResult.quality_score?.toFixed(1)}/100
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Angles Captured</span>
                <span className="font-medium text-white">{submittedResult.angles_captured}/5</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Status</span>
                <span className="badge-warning text-xs capitalize">{submittedResult.status?.replace('_', ' ')}</span>
              </div>
            </div>

            <div className="glass-card p-5 bg-brand/5 border-brand/20">
              <p className="text-sm text-slate-300">
                <span className="text-brand font-semibold">What happens next?</span><br />
                Your professor will receive your request and review your face photos. Once approved, you will be automatically included in AI attendance recognition.
              </p>
            </div>

            <button
              onClick={() => navigate('/student')}
              className="btn-primary w-full py-3"
            >
              Back to Dashboard
            </button>
          </div>
        )}

        {/* ── STAGE: ERROR ────────────────────────────────────────────────── */}
        {stage === 'error' && (
          <div className="space-y-4 animate-fade-in">
            <div className="glass-card p-8 text-center border-danger/30">
              <div className="w-16 h-16 rounded-full bg-danger/15 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-white">Enrollment Failed</h2>
              <p className="text-slate-400 text-sm mt-2">{errorMsg}</p>
            </div>
            <button
              onClick={() => { setStage('select-subject'); setCapturedAngles({}); setCurrentAngleIdx(0); }}
              className="btn-primary w-full py-3"
            >
              Try Again
            </button>
          </div>
        )}

        </ErrorBoundary>
      </main>
    </div>
  );
}
