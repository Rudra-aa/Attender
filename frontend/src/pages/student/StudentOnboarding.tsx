import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface Department {
  id: string;
  name: string;
  code: string;
}

interface Batch {
  id: string;
  name: string;
  department_id: string;
  year: number;
  semester: number;
}

interface MetadataResponse {
  departments: Department[];
  batches: Batch[];
}

export default function StudentOnboarding() {
  const queryClient = useQueryClient();
  const [selectedDept, setSelectedDept] = useState('');
  const [selectedYear, setSelectedYear] = useState<number | ''>('');
  const [selectedSem, setSelectedSem] = useState<number | ''>('');
  const [selectedBatch, setSelectedBatch] = useState('');

  const { data, isLoading } = useQuery<MetadataResponse>({
    queryKey: ['onboard-metadata'],
    queryFn: async () => (await apiClient.get('/students/onboard/metadata')).data,
  });

  const onboardMutation = useMutation({
    mutationFn: async (payload: { department_id: string; year_of_study: number; batch_id: string }) => {
      await apiClient.post('/students/me/onboard', payload);
    },
    onSuccess: () => {
      // Invalidate queries so the dashboard refreshes
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });
      queryClient.invalidateQueries({ queryKey: ['student-subjects'] });
    },
  });

  if (isLoading) return <div className="p-8 text-center text-slate-400">Loading onboarding...</div>;

  const departments = data?.departments || [];
  const allBatches = data?.batches || [];

  const availableBatches = allBatches.filter(
    (b) =>
      b.department_id === selectedDept &&
      b.year === Number(selectedYear) &&
      b.semester === Number(selectedSem)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDept || !selectedYear || !selectedBatch) return;
    onboardMutation.mutate({
      department_id: selectedDept,
      year_of_study: Number(selectedYear),
      batch_id: selectedBatch,
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8 max-w-md w-full relative overflow-hidden">
        {/* Glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-indigo-500/20 rounded-full blur-3xl" />

        <div className="relative">
          <h2 className="text-2xl font-bold text-white mb-2">Welcome to Attender</h2>
          <p className="text-slate-400 text-sm mb-8">
            Let's get you set up. Please select your academic details to enroll in your subjects automatically.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Department */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                Department
              </label>
              <select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                required
              >
                <option value="">Select Department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Year & Semester */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Year of Study
                </label>
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  required
                >
                  <option value="">Year</option>
                  {[1, 2, 3, 4, 5].map((y) => (
                    <option key={y} value={y}>
                      Year {y}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Semester
                </label>
                <select
                  value={selectedSem}
                  onChange={(e) => setSelectedSem(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  required
                >
                  <option value="">Semester</option>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((s) => (
                    <option key={s} value={s}>
                      Sem {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Batch */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                Batch / Section
              </label>
              <select
                value={selectedBatch}
                onChange={(e) => setSelectedBatch(e.target.value)}
                className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50"
                required
                disabled={!selectedDept || !selectedYear || !selectedSem}
              >
                <option value="">Select Batch</option>
                {availableBatches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
              {selectedDept && selectedYear && selectedSem && availableBatches.length === 0 && (
                <p className="text-xs text-amber-500 mt-2">No batches found for this combination.</p>
              )}
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={!selectedBatch || onboardMutation.isPending}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 px-4 rounded-xl shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
              >
                {onboardMutation.isPending ? 'Completing Setup...' : 'Complete Setup'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
