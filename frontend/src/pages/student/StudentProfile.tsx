import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../store/authStore';

export default function StudentProfile() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    phone: '',
    bio: '',
    avatar_url: '',
  });

  const { data: profile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['student-profile'],
    queryFn: async () => (await apiClient.get('/students/me')).data,
  });

  const { data: enrollmentStatus } = useQuery({
    queryKey: ['enrollment-status'],
    queryFn: async () => (await apiClient.get('/faces/enrollment-status')).data,
  });

  const updateProfileMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      await apiClient.patch('/students/me', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-profile'] });
      setIsEditing(false);
    },
  });

  useEffect(() => {
    if (profile) {
      setFormData({
        phone: profile.phone || '',
        bio: profile.bio || '',
        avatar_url: profile.avatar_url || '',
      });
    }
  }, [profile]);

  if (isLoadingProfile) {
    return <div className="animate-pulse space-y-4">Loading profile...</div>;
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white">Student Profile</h1>
          <p className="text-slate-400 mt-1 text-sm">Manage your personal information and biometric enrollment</p>
        </div>
        {!isEditing && (
          <button 
            onClick={() => setIsEditing(true)}
            className="btn-secondary py-1.5 px-4 text-sm"
          >
            Edit Profile
          </button>
        )}
      </div>

      <div className="glass-card p-8">
        <div className="flex flex-col md:flex-row gap-8 items-start">
          <div className="w-24 h-24 rounded-2xl bg-bg-primary overflow-hidden border border-border-subtle flex-shrink-0">
            {isEditing ? (
              <img src={formData.avatar_url || 'https://via.placeholder.com/150'} alt="Profile" className="w-full h-full object-cover" />
            ) : profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="Profile" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400 text-3xl font-medium">
                {profile?.full_name?.charAt(0)}
              </div>
            )}
          </div>
          
          <div className="space-y-6 w-full">
            {isEditing ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Avatar URL</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={formData.avatar_url}
                    onChange={(e) => setFormData({...formData, avatar_url: e.target.value})}
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Phone Number</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                    placeholder="+1 234 567 890"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Bio</label>
                  <textarea 
                    className="input-field min-h-[80px]" 
                    value={formData.bio}
                    onChange={(e) => setFormData({...formData, bio: e.target.value})}
                    placeholder="A short bio about yourself..."
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button 
                    onClick={() => updateProfileMutation.mutate(formData)}
                    className="btn-primary py-2 px-4 text-sm flex-1"
                    disabled={updateProfileMutation.isPending}
                  >
                    {updateProfileMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button 
                    onClick={() => setIsEditing(false)}
                    className="btn-secondary py-2 px-4 text-sm flex-1"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Full Name</label>
                    <div className="text-white font-medium">{profile?.full_name}</div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Roll Number</label>
                    <div className="text-white font-medium">{profile?.student_id || 'Not Assigned'}</div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Email Address</label>
                    <div className="text-white font-medium">{profile?.email}</div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Phone</label>
                    <div className="text-white font-medium">{profile?.phone || '—'}</div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Department</label>
                    <div className="text-white font-medium">{profile?.department || 'Not Assigned'}</div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Year of Study</label>
                    <div className="text-white font-medium">{profile?.year_of_study ? `Year ${profile.year_of_study}` : '-'}</div>
                  </div>
                </div>
                
                {profile?.bio && (
                  <div>
                    <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Bio</label>
                    <div className="text-slate-300 text-sm whitespace-pre-wrap">{profile.bio}</div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Biometric Enrollment Status</h2>
        
        <div className={`glass-card p-6 border-l-4 ${
          enrollmentStatus?.is_face_approved
            ? 'border-l-success'
            : enrollmentStatus?.pending_request
            ? 'border-l-warning'
            : 'border-l-brand'
        }`}>
          <div className="flex flex-col md:flex-row items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold text-white mb-1">Face Recognition Data</h3>
              <p className="text-sm text-slate-400 max-w-lg mb-4">
                {enrollmentStatus?.is_face_approved
                  ? 'Your biometric face data has been verified by your professor and is actively used to mark your attendance.'
                  : enrollmentStatus?.pending_request
                  ? 'Your face enrollment has been submitted and is waiting for your professor to approve it.'
                  : 'You have not completed the face enrollment process. You will not be marked present in AI attendance sessions until you enroll.'}
              </p>
              
              {!enrollmentStatus?.is_face_approved && !enrollmentStatus?.pending_request && (
                <Link to="/student/enroll" className="btn-primary py-2 px-4 text-sm inline-flex">
                  Enroll Face Now
                </Link>
              )}
            </div>
            
            <div className="shrink-0">
              {enrollmentStatus?.is_face_approved ? (
                <span className="badge-present text-sm px-3 py-1">Active</span>
              ) : enrollmentStatus?.pending_request ? (
                <span className="badge-warning text-sm px-3 py-1">Pending Approval</span>
              ) : (
                <span className="px-3 py-1 rounded-full text-sm font-semibold bg-slate-500/20 text-slate-400">Not Enrolled</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
