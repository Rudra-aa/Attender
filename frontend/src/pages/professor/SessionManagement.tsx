import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../api/client';

export default function SessionManagement() {
  const [searchParams] = useSearchParams();
  const subjectId = searchParams.get('subject');

  // We are mocking the session management state for the UI
  const [activeSession, setActiveSession] = useState(false);

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="sticky top-0 z-20 bg-bg-primary/80 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/professor" className="text-slate-400 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="font-semibold text-white">Session Management</h1>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Start New Session</h2>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Geofence Radius (meters)</label>
              <input type="number" defaultValue={100} className="input" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Late Threshold (mins)</label>
              <input type="number" defaultValue={10} className="input" />
            </div>
          </div>
          <button 
            onClick={() => setActiveSession(!activeSession)} 
            className={`btn-primary w-full ${activeSession ? 'bg-danger hover:bg-danger text-white hover:shadow-glow-success border-none' : ''}`}
          >
            {activeSession ? 'End Session' : 'Start Session Now'}
          </button>
        </div>

        {activeSession && (
          <div className="glass-card p-6 border-brand/40 shadow-glow-brand animate-fade-in">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <span className="live-dot" /> Live Attendance Feed
              </h2>
              <span className="text-brand-light text-sm">34/42 Marked</span>
            </div>
            
            <div className="space-y-3">
              {/* Mock Feed */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-bg-elevated border border-success/30">
                <div>
                  <p className="text-sm font-medium text-white">Alex Johnson</p>
                  <p className="text-xs text-slate-400">Marked at 09:14 AM • Distance: 12m</p>
                </div>
                <div className="text-right">
                  <span className="badge-present">Present</span>
                  <p className="text-xs text-slate-400 mt-1">98% match</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-bg-elevated border border-warning/30">
                <div>
                  <p className="text-sm font-medium text-white">Maria Garcia</p>
                  <p className="text-xs text-slate-400">Marked at 09:21 AM • Distance: 8m</p>
                </div>
                <div className="text-right">
                  <span className="badge-warning">Late</span>
                  <p className="text-xs text-slate-400 mt-1">99% match</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
