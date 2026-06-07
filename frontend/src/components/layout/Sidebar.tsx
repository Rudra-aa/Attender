import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export default function Sidebar({ 
  isMobileOpen = false, 
  setIsMobileOpen = () => {} 
}: { 
  isMobileOpen?: boolean; 
  setIsMobileOpen?: (val: boolean) => void 
}) {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(true);

  const professorLinks = [
    { label: 'Dashboard', path: '/professor' },
    { label: 'My Subjects', path: '/professor/subjects' },
    { label: 'Sessions', path: '/professor/sessions' },
    { label: 'Enrollment Requests', path: '/professor/enrollments' },
    { label: 'Attendance Drafts', path: '/professor/drafts' },
    { label: 'Reports', path: '/professor/reports' },
    { label: 'Notifications', path: '/professor/notifications' },
    { label: 'Profile', path: '/professor/profile' },
  ];

  const studentLinks = [
    { label: 'Dashboard', path: '/student' },
    { label: 'Attendance History', path: '/student/history' },
    { label: 'Subjects', path: '/student/subjects' },
    { label: 'Enrollment Status', path: '/student/enroll' },
    { label: 'Notifications', path: '/student/notifications' },
    { label: 'Profile', path: '/student/profile' },
  ];

  const links = user?.role === 'professor' ? professorLinks : studentLinks;

  // Handle mobile click overlay
  const handleLinkClick = () => {
    if (isMobileOpen) {
      setIsMobileOpen(false);
    }
  };

  const overlayClasses = isMobileOpen 
    ? 'fixed inset-0 bg-black/50 z-40 md:hidden' 
    : 'hidden';

  const sidebarClasses = isMobileOpen
    ? 'fixed inset-y-0 left-0 z-50 w-64 bg-bg-elevated border-r border-border-subtle flex flex-col transform translate-x-0 transition-transform duration-300 ease-in-out'
    : 'fixed inset-y-0 left-0 z-50 w-64 bg-bg-elevated border-r border-border-subtle flex flex-col transform -translate-x-full transition-transform duration-300 ease-in-out md:relative md:translate-x-0';

  if (!isOpen && !isMobileOpen) {
    return (
      <aside className="w-16 bg-bg-elevated border-r border-border-subtle h-screen sticky top-0 flex flex-col hidden md:flex items-center py-6 transition-all shrink-0">
        <button 
          onClick={() => setIsOpen(true)}
          className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-bg-primary transition-colors"
          title="Show Sidebar"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <>
      {/* Mobile Overlay */}
      <div className={overlayClasses} onClick={() => setIsMobileOpen(false)} />
      
      {/* Main Sidebar */}
      <aside className={sidebarClasses + (isOpen ? '' : ' md:w-16')}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center shrink-0">
                <span className="text-white font-bold text-xs">A</span>
              </div>
              <span className={`font-semibold text-white whitespace-nowrap ${!isOpen && !isMobileOpen ? 'md:hidden' : ''}`}>Attender V3</span>
            </div>
            {/* Desktop hide button */}
            <button 
              onClick={() => setIsOpen(false)}
              className="hidden md:block p-1 rounded-lg text-slate-400 hover:text-white hover:bg-bg-primary transition-colors"
              title="Hide Sidebar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>
            {/* Mobile close button */}
            <button 
              onClick={() => setIsMobileOpen(false)}
              className="md:hidden p-1 rounded-lg text-slate-400 hover:text-white hover:bg-bg-primary transition-colors"
              title="Close Sidebar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <nav className={`space-y-1 ${!isOpen && !isMobileOpen ? 'md:hidden' : ''}`}>
            {links.map((link) => {
              const isActive = location.pathname === link.path || location.pathname.startsWith(link.path + '/');
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={handleLinkClick}
                  className={`flex items-center px-4 py-2.5 rounded-xl text-sm transition-all whitespace-nowrap ${
                    isActive 
                      ? 'bg-brand/10 text-brand-light font-medium' 
                      : 'text-slate-400 hover:text-white hover:bg-bg-primary'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className={`mt-auto p-6 border-t border-border-subtle ${!isOpen && !isMobileOpen ? 'md:hidden' : ''}`}>
          <div className="flex items-center gap-3 mb-4 overflow-hidden">
            <div className="w-10 h-10 rounded-full bg-bg-primary overflow-hidden border border-border-subtle shrink-0">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-400 text-xs">
                  {user?.fullName?.charAt(0)}
                </div>
              )}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-white truncate">{user?.fullName}</span>
              <span className="text-xs text-slate-500 capitalize">{user?.role}</span>
            </div>
          </div>
          
          <button 
            onClick={logout} 
            className="w-full text-left px-4 py-2 text-sm text-slate-400 hover:text-danger hover:bg-danger/10 rounded-xl transition-all whitespace-nowrap"
          >
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
