import type { DashboardSnapshot } from '@/lib/dashboard';

const API_BASE = process.env.EXTERNAL_API_URL || 'http://localhost:3001';

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const res = await fetch(`${API_BASE}/api/dashboard`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error('Failed to fetch dashboard snapshot');
  }
  return res.json();
}
