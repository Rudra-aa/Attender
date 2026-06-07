import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface Subject {
  id: string;
  name: string;
  code: string;
  semester: number;
  is_active: boolean;
}

export default function MySubjects() {
  const queryClient = useQueryClient();
  const [showCreateSubject, setShowCreateSubject] = useState(false);
  const [form, setForm] = useState({
    name: '', code: '', semester: 5, academic_year: '2025-26', credits: 4
  });
  const [formError, setFormError] = useState('');

  const { data: subjects = [], isLoading } = useQuery<Subject[]>({
    queryKey: ['professor-subjects'],
    queryFn: async () => (await apiClient.get('/professor/subjects')).data,
  });

  const createSubject = useMutation({
    mutationFn: async (data: typeof form) =>
      (await apiClient.post('/subjects/', data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['professor-subjects'] });
      setShowCreateSubject(false);
      setForm({ name: '', code: '', semester: 5, academic_year: '2025-26', credits: 4 });
      setFormError('');
    },
    onError: (err: any) => {
      setFormError(err?.response?.data?.detail || 'Failed to create subject.');
    },
  });

  const archiveSubject = useMutation({
    mutationFn: async (id: string) => await apiClient.patch(`/subjects/${id}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['professor-subjects'] });
    }
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.code.trim()) {
      setFormError('Subject name and code are required.');
      return;
    }
    createSubject.mutate(form);
  };

  const handleArchive = (id: string, name: string) => {
    if (confirm(`Are you sure you want to archive ${name}? This will hide it from active lists, but preserve attendance records.`)) {
      archiveSubject.mutate(id);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">My Subjects</h1>
          <p className="text-slate-400 mt-1 text-sm">Manage the subjects you are teaching</p>
        </div>
        <button onClick={() => setShowCreateSubject(true)} className="btn-primary">
          + Add Subject
        </button>
      </div>

      <div className="bg-bg-elevated border border-border-subtle rounded-2xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-bg-primary/50 text-slate-400 border-b border-border-subtle">
            <tr>
              <th className="px-6 py-4 font-medium">Subject</th>
              <th className="px-6 py-4 font-medium">Code</th>
              <th className="px-6 py-4 font-medium">Semester</th>
              <th className="px-6 py-4 font-medium">Status</th>
              <th className="px-6 py-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle text-slate-300">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading subjects...</td>
              </tr>
            ) : subjects.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No subjects found.</td>
              </tr>
            ) : subjects.map(subject => (
              <tr key={subject.id} className="hover:bg-bg-primary/50 transition-colors">
                <td className="px-6 py-4 font-medium text-white">{subject.name}</td>
                <td className="px-6 py-4">{subject.code}</td>
                <td className="px-6 py-4">Sem {subject.semester}</td>
                <td className="px-6 py-4">
                  {subject.is_active ? (
                    <span className="badge-present text-xs">Active</span>
                  ) : (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400">Archived</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  {subject.is_active && (
                    <button 
                      onClick={() => handleArchive(subject.id, subject.name)}
                      className="text-danger hover:text-danger/80 transition-colors text-xs font-medium"
                    >
                      Archive Subject
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateSubject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-card p-8 w-full max-w-md animate-slide-up">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-white">Create Subject</h2>
              <button onClick={() => { setShowCreateSubject(false); setFormError(''); }}
                className="text-slate-400 hover:text-white transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Subject Name *</label>
                <input id="subject-name" className="input" placeholder="Data Structures"
                  value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Code *</label>
                  <input id="subject-code" className="input" placeholder="CS301"
                    value={form.code} onChange={e => setForm(p => ({ ...p, code: e.target.value.toUpperCase() }))} />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Semester</label>
                  <input id="subject-semester" type="number" min={1} max={8} className="input"
                    value={form.semester} onChange={e => setForm(p => ({ ...p, semester: +e.target.value }))} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Academic Year</label>
                  <input id="subject-year" className="input" placeholder="2025-26"
                    value={form.academic_year} onChange={e => setForm(p => ({ ...p, academic_year: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Credits</label>
                  <input id="subject-credits" type="number" min={1} max={6} className="input"
                    value={form.credits} onChange={e => setForm(p => ({ ...p, credits: +e.target.value }))} />
                </div>
              </div>

              {formError && (
                <div className="p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
                  {formError}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreateSubject(false)} className="btn-secondary flex-1">
                  Cancel
                </button>
                <button type="submit" id="create-subject-submit" disabled={createSubject.isPending} className="btn-primary flex-1">
                  {createSubject.isPending ? 'Creating...' : 'Create Subject'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
