import { fetchDashboardSnapshot } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export async function GET() {
  const snapshot = await fetchDashboardSnapshot();
  return Response.json(snapshot);
}
