import { useState, useRef, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

type CaptureStep = 'capture' | 'processing' | 'done';

interface CapturedPhoto {
  id: number;
  dataUrl: string;
  thumb: string;
}

export default function TakeAttendance() {
  const { subjectId } = useParams<{ subjectId: string }>();
  const navigate = useNavigate();
  const webcamRef = useRef<Webcam>(null);

  const [step, setStep] = useState<CaptureStep>('capture');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [photos, setPhotos] = useState<CapturedPhoto[]>([]);
  const [useCamera, setUseCamera] = useState(true);
  const [error, setError] = useState('');
  const [processingStatus, setProcessingStatus] = useState<string[]>([]);

  // Step 1: Create session when user arrives on this page
  const createSession = useMutation({
    mutationFn: async () =>
      (await apiClient.post('/sessions/', { subject_id: subjectId })).data,
    onSuccess: (data) => setSessionId(data.id),
    onError: (err: any) => setError(err?.response?.data?.detail || 'Failed to create session'),
  });

  // Initialize session on mount
  useState(() => {
    createSession.mutate();
  });

  // Step 2: Capture photo from webcam
  const capturePhoto = useCallback(() => {
    const dataUrl = webcamRef.current?.getScreenshot();
    if (!dataUrl) return;
    setPhotos(prev => [
      ...prev,
      { id: Date.now(), dataUrl, thumb: dataUrl }
    ]);
  }, []);

  // Step 2b: Upload photo from file
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.slice(0, 5 - photos.length).forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result as string;
        setPhotos(prev => [...prev, { id: Date.now() + Math.random(), dataUrl, thumb: dataUrl }]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removePhoto = (id: number) => {
    setPhotos(prev => prev.filter(p => p.id !== id));
  };

  // Step 3: Analyze
  const analyzeMutation = useMutation({
    mutationFn: async (images: string[]) => {
      setStep('processing');
      setProcessingStatus(['Uploading images...']);

      await new Promise(r => setTimeout(r, 300));
      setProcessingStatus(p => [...p, 'Detecting faces (SCRFD)...']);

      await new Promise(r => setTimeout(r, 400));
      setProcessingStatus(p => [...p, 'Generating ArcFace embeddings...']);

      const result = await apiClient.post(`/sessions/${sessionId}/analyze`, { images });

      setProcessingStatus(p => [...p, 'Matching students...']);
      await new Promise(r => setTimeout(r, 200));
      setProcessingStatus(p => [...p, '✅ Draft ready!']);

      setStep('done');
      return result.data;
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || 'Analysis failed. Please try again.');
      setStep('capture');
    },
  });

  const handleAnalyze = () => {
    if (photos.length < 2) {
      setError('Please capture at least 2 classroom photos for accurate detection.');
      return;
    }
    if (!sessionId) {
      setError('Session not ready yet. Please wait a moment.');
      return;
    }
    setError('');
    analyzeMutation.mutate(photos.map(p => p.dataUrl));
  };

  // Navigate to draft review
  const goToReview = () => {
    navigate(`/professor/draft/${sessionId}`);
  };

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/professor" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="font-semibold text-white">Take Attendance</h1>
              {sessionId && <p className="text-xs text-slate-500 font-mono mt-0.5">Session: {sessionId.slice(0, 8)}...</p>}
            </div>
          </div>
          {/* Photo count indicator */}
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i}
                className={`w-3 h-3 rounded-full transition-colors ${i <= photos.length ? 'bg-brand' : 'bg-bg-elevated border border-border-subtle'}`}
              />
            ))}
            <span className="text-xs text-slate-400 ml-2">{photos.length}/5</span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">

        {/* ── STEP: CAPTURE ───────────────────────────────────────────── */}
        {step === 'capture' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-white">Capture Classroom Photos</h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => setUseCamera(true)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${useCamera ? 'bg-brand text-white' : 'text-slate-400 hover:text-white'}`}
                  >
                    📷 Camera
                  </button>
                  <button
                    onClick={() => setUseCamera(false)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${!useCamera ? 'bg-brand text-white' : 'text-slate-400 hover:text-white'}`}
                  >
                    📁 Upload
                  </button>
                </div>
              </div>

              {useCamera ? (
                <div className="space-y-3">
                  <div className="relative rounded-xl overflow-hidden bg-bg-elevated aspect-video">
                    <Webcam
                      ref={webcamRef}
                      screenshotFormat="image/jpeg"
                      videoConstraints={{ facingMode: 'environment', width: 1280, height: 720 }}
                      className="w-full h-full object-cover"
                      screenshotQuality={0.9}
                    />
                    {/* Guide overlay */}
                    <div className="absolute inset-0 pointer-events-none">
                      <div className="absolute inset-4 border border-dashed border-white/20 rounded-xl" />
                      <p className="absolute bottom-4 left-0 right-0 text-center text-white/70 text-xs">
                        Ensure all students are visible
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={capturePhoto}
                    disabled={photos.length >= 5}
                    id="capture-photo-btn"
                    className="btn-primary w-full py-4 text-base disabled:opacity-40"
                  >
                    {photos.length >= 5 ? 'Maximum 5 photos' : `📸 Capture Photo ${photos.length + 1}`}
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <label
                    htmlFor="file-upload"
                    className="flex flex-col items-center justify-center h-48 rounded-xl border-2 border-dashed border-border-subtle hover:border-brand/50 transition-colors cursor-pointer"
                  >
                    <svg className="w-10 h-10 text-slate-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-slate-400 text-sm">Click to upload classroom photos</p>
                    <p className="text-slate-600 text-xs mt-1">PNG, JPG · Up to {5 - photos.length} more</p>
                    <input
                      id="file-upload"
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={handleFileUpload}
                      disabled={photos.length >= 5}
                    />
                  </label>
                </div>
              )}
            </div>

            {/* Photo Thumbnails */}
            {photos.length > 0 && (
              <div className="glass-card p-5">
                <p className="text-sm font-medium text-slate-300 mb-3">
                  Captured Photos ({photos.length})
                </p>
                <div className="flex gap-3 flex-wrap">
                  {photos.map((p) => (
                    <div key={p.id} className="relative group">
                      <img
                        src={p.thumb}
                        alt="Classroom"
                        className="w-24 h-16 object-cover rounded-lg border border-border-subtle"
                      />
                      <button
                        onClick={() => removePhoto(p.id)}
                        className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-danger flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="p-4 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm">
                {error}
              </div>
            )}

            {/* Analyze CTA */}
            <button
              onClick={handleAnalyze}
              disabled={photos.length < 2 || !sessionId}
              id="analyze-photos-btn"
              className="btn-primary w-full py-4 text-base disabled:opacity-40"
            >
              {photos.length < 2
                ? `Capture ${2 - photos.length} more photo${2 - photos.length > 1 ? 's' : ''} to analyze`
                : `Analyze ${photos.length} Photos →`}
            </button>
            {photos.length >= 2 && (
              <p className="text-center text-xs text-slate-500">
                More angles = higher accuracy. 3–5 photos recommended for large classrooms.
              </p>
            )}
          </div>
        )}

        {/* ── STEP: PROCESSING ────────────────────────────────────────── */}
        {step === 'processing' && (
          <div className="glass-card p-12 text-center space-y-6 animate-fade-in">
            <div className="w-20 h-20 rounded-full bg-brand/10 flex items-center justify-center mx-auto shadow-glow-brand">
              <svg className="animate-spin w-10 h-10 text-brand" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">AI is analyzing your classroom</h2>
              <p className="text-slate-400 text-sm">Detecting and recognizing all visible faces</p>
            </div>
            <div className="text-left space-y-2 max-w-xs mx-auto">
              {processingStatus.map((status, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm text-slate-300 animate-fade-in">
                  <span className="text-success">✓</span>
                  {status}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── STEP: DONE ──────────────────────────────────────────────── */}
        {step === 'done' && analyzeMutation.data && (
          <div className="glass-card p-8 text-center space-y-6 border-success/30 animate-slide-up">
            <div className="w-20 h-20 rounded-full bg-success/15 flex items-center justify-center mx-auto shadow-glow-success">
              <svg className="w-10 h-10 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Analysis Complete!</h2>
              <p className="text-slate-400 text-sm mt-1">AI has generated the attendance draft</p>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-4 rounded-xl bg-success/10 border border-success/20">
                <p className="text-2xl font-bold text-success">
                  {analyzeMutation.data.summary.auto_present_count}
                </p>
                <p className="text-xs text-slate-400 mt-1">Auto Marked</p>
              </div>
              <div className="p-4 rounded-xl bg-warning/10 border border-warning/20">
                <p className="text-2xl font-bold text-warning">
                  {analyzeMutation.data.summary.needs_review_count}
                </p>
                <p className="text-xs text-slate-400 mt-1">Review Needed</p>
              </div>
              <div className="p-4 rounded-xl bg-danger/10 border border-danger/20">
                <p className="text-2xl font-bold text-danger">
                  {analyzeMutation.data.summary.not_detected_count}
                </p>
                <p className="text-xs text-slate-400 mt-1">Not Detected</p>
              </div>
            </div>

            <button
              onClick={goToReview}
              id="go-to-review-btn"
              className="btn-primary w-full py-4 text-base"
            >
              Review &amp; Finalize →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
