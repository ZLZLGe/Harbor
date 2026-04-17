'use client';

import { filterTimeline, type DashboardSnapshot } from '@/lib/dashboard';

interface Props {
  snapshot: DashboardSnapshot;
  activeFilter: string;
}

export function AdvancedInsightsPanel({ snapshot, activeFilter }: Props) {
  const visiblePoints = filterTimeline(snapshot.timeline, activeFilter);
  const avgConversion =
    visiblePoints.reduce((sum, point) => sum + point.conversionRate, 0) / Math.max(visiblePoints.length, 1);

  return (
    <section
      data-testid="advanced-insights-panel"
      className="rounded-[1.75rem] border border-emerald-200 bg-emerald-50/80 p-6 shadow-sm"
    >
      <p className="text-xs uppercase tracking-[0.24em] text-emerald-700">Advanced Insights</p>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <article className="rounded-2xl bg-white p-4">
          <h3 className="text-sm font-medium text-slate-600">Average conversion</h3>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{avgConversion.toFixed(2)}%</p>
        </article>
        <article className="rounded-2xl bg-white p-4">
          <h3 className="text-sm font-medium text-slate-600">Tracked points</h3>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{visiblePoints.length}</p>
        </article>
        <article className="rounded-2xl bg-white p-4">
          <h3 className="text-sm font-medium text-slate-600">Snapshot</h3>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{snapshot.snapshotId}</p>
        </article>
      </div>
    </section>
  );
}
