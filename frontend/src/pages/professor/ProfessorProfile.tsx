import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../store/authStore';

export default function ProfessorProfile() {
  const { user } = useAuthStore();

  const { data: profile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['professor-profile'],
    queryFn: async () => (await apiClient.get('/professor/me')).data,
  });

  const { data: subjects = [], isLoading: isLoadingSubjects } = useQuery({
    queryKey: ['professor-subjects'],
    queryFn: async () => (await apiClient.get('/professor/subjects')).data,
  });

  const activeSubjects = subjects.filter((s: any) => s.is_active);

  if (isLoadingProfile) {
    return <div className="animate-pulse space-y-4">Loading profile...</div>;
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Professor Profile</h1>
        <p className="text-slate-400 mt-1 text-sm">Manage your personal information and teaching assignments</p>
      </div>

      <div className="glass-card p-8">
        <div className="flex flex-col md:flex-row gap-8 items-start">
          <div className="w-24 h-24 rounded-2xl bg-bg-primary overflow-hidden border border-border-subtle flex-shrink-0">
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="Profile" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400 text-3xl font-medium">
                {profile?.full_name?.charAt(0)}
              </div>
            )}
          </div>
          
          <div className="space-y-4 w-full">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Full Name</label>
                <div className="text-white font-medium">{profile?.full_name}</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Email Address</label>
                <div className="text-white font-medium">{profile?.email}</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Department</label>
                <div className="text-white font-medium">{profile?.department || 'Not Assigned'}</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Designation</label>
                <div className="text-white font-medium">{profile?.designation || 'Professor'}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Subjects Currently Teaching</h2>
        <div className="bg-bg-elevated border border-border-subtle rounded-2xl overflow-hidden">
          {isLoadingSubjects ? (
            <div className="p-6 text-slate-500 text-sm">Loading subjects...</div>
          ) : activeSubjects.length === 0 ? (
            <div className="p-6 text-slate-500 text-sm">You are not currently teaching any active subjects.</div>
          ) : (
            <div className="divide-y divide-border-subtle">
              {activeSubjects.map((subject: any) => (
                <div key={subject.id} className="p-4 flex items-center justify-between hover:bg-bg-primary transition-colors">
                  <div>
                    <h3 className="text-white font-medium">{subject.name}</h3>
                    <p className="text-sm text-slate-400">{subject.code} · Semester {subject.semester}</p>
                  </div>
                  <span className="badge-present text-xs">Active</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
