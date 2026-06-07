import React, { useState } from 'react';
import Sidebar from './Sidebar';
import NotificationBell from './NotificationBell';
import { useAuthStore } from '../../store/authStore';

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-bg-primary relative">
      <Sidebar isMobileOpen={isMobileOpen} setIsMobileOpen={setIsMobileOpen} />
      
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        <header className="sticky top-0 z-20 bg-bg-primary/90 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
          <div className="flex items-center justify-between md:justify-end">
            <div className="flex items-center gap-3 md:hidden">
              <button onClick={() => setIsMobileOpen(true)} className="p-2 -ml-2 text-slate-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center">
                <span className="text-white font-bold text-xs">A</span>
              </div>
              <span className="font-semibold text-white">Attender V3</span>
            </div>
            
            <div className="flex items-center gap-4">
              <NotificationBell />
              <div className="hidden sm:block text-sm text-slate-400">
                {user?.department || 'Student'}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 pb-24 md:pb-6">
          <div className="max-w-5xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
