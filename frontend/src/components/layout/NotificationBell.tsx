import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await apiClient.get('/notifications/')).data,
    refetchInterval: 30_000,
  });

  const unreadCount = notifications.filter((n: any) => !n.is_read).length;

  const markAsRead = useMutation({
    mutationFn: async (id: string) => await apiClient.patch(`/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllAsRead = useMutation({
    mutationFn: async () => await apiClient.patch('/notifications/read-all'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-bg-elevated transition-colors relative"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-brand rounded-full border-2 border-bg-primary"></span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-bg-elevated border border-border-subtle rounded-xl shadow-2xl z-50 animate-slide-up">
          <div className="sticky top-0 bg-bg-elevated/95 backdrop-blur-sm p-4 border-b border-border-subtle flex justify-between items-center z-10">
            <h3 className="font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button 
                onClick={() => markAllAsRead.mutate()}
                className="text-xs text-brand-light hover:text-white transition-colors"
              >
                Mark all as read
              </button>
            )}
          </div>
          
          <div className="flex flex-col">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">
                No notifications yet.
              </div>
            ) : (
              notifications.map((n: any) => (
                <div 
                  key={n.id} 
                  className={`p-4 border-b border-border-subtle last:border-0 hover:bg-bg-primary transition-colors cursor-pointer ${!n.is_read ? 'bg-brand/5' : ''}`}
                  onClick={() => {
                    if (!n.is_read) markAsRead.mutate(n.id);
                  }}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className={`text-sm font-medium ${!n.is_read ? 'text-white' : 'text-slate-300'}`}>
                      {n.title}
                    </span>
                    {!n.is_read && <span className="w-2 h-2 rounded-full bg-brand mt-1.5 flex-shrink-0"></span>}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-2">{n.body}</p>
                  <span className="text-[10px] text-slate-500">
                    {new Date(n.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
