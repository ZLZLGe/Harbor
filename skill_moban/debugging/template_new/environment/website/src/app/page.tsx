import { DashboardShell } from '@/components/DashboardShell';
import { DEFAULT_FILTER } from '@/lib/dashboard';
import { fetchDashboardSnapshot } from '@/services/api-client';

export const dynamic = 'force-dynamic';

interface Props {
  searchParams?: {
    filter?: string;
    alert?: string;
  };
}

export default async function HomePage({ searchParams }: Props) {
  const snapshot = await fetchDashboardSnapshot();
  const initialFilter = typeof searchParams?.filter === 'string' ? searchParams.filter : DEFAULT_FILTER;
  const initialAlertId = typeof searchParams?.alert === 'string' ? searchParams.alert : null;

  return <DashboardShell snapshot={snapshot} initialFilter={initialFilter} initialAlertId={initialAlertId} />;
}
