'use client';

import dynamic from 'next/dynamic';
import { useMemo } from 'react';
import { filterAlerts, filterTimeline, type DashboardSnapshot } from '@/lib/dashboard';
import { loadAdvancedInsightsPanel } from '@/lib/loadAdvancedInsightsPanel';

interface Props {
  snapshot: DashboardSnapshot;
  activeFilter: string;
  isAdvancedOpen: boolean;
  onOpenAdvanced: () => void;
  onOpenAlert: (alertId: string) => void;
  onRefresh: () => void;
}

const AdvancedInsightsPanel = dynamic(loadAdvancedInsightsPanel, {
  ssr: false,
  loading: () => <div className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">Loading advanced insights…</div>,
});

export function TimelinePanel({
  snapshot,
  activeFilter,
  isAdvancedOpen,
  onOpenAdvanced,
  onOpenAlert,
  onRefresh,
}: Props) {
  const visibleAlerts = useMemo(() => filterAlerts(snapshot.alerts, activeFilter), [activeFilter, snapshot.alerts]);
  const visibleTimeline = useMemo(() => filterTimeline(snapshot.timeline, activeFilter), [activeFilter, snapshot.timeline]);

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Timeline</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Regional pacing and live alert pressure</h2>
          </div>
          <div className="flex gap-3">
            <button
              data-testid="timeline-refresh"
              onClick={onRefresh}
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Refresh timeline
            </button>
            <button
              data-testid="toggle-advanced-insights"
              onClick={onOpenAdvanced}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
            >
              {isAdvancedOpen ? 'Advanced insights open' : 'Open advanced insights'}
            </button>
          </div>
        </div>

        <div data-testid="timeline-chart" className="grid gap-3 md:grid-cols-4">
          {visibleTimeline.map((point) => (
            <article key={point.id} className="rounded-2xl bg-slate-50 p-4">
              <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{point.day}</div>
              <div className="mt-2 text-xl font-semibold text-slate-950">{point.sessions.toLocaleString()}</div>
              <div className="mt-1 text-sm text-slate-600">{point.conversionRate.toFixed(1)}% conversion</div>
              <div className="mt-1 text-sm text-slate-600">${point.revenueK.toFixed(1)}k revenue</div>
            </article>
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.9fr]">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Live Alerts</p>
          <div className="mt-4 grid gap-4">
            {visibleAlerts.map((alert) => (
              <article key={alert.id} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-950">{alert.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{alert.summary}</p>
                  </div>
                  <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-rose-600">
                    {alert.severity}
                  </span>
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <div className="text-sm text-slate-500">Owner: {alert.owner}</div>
                  <button
                    data-testid={`open-alert-${alert.id}`}
                    onClick={() => onOpenAlert(alert.id)}
                    className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-800"
                  >
                    Open alert
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        {isAdvancedOpen ? <AdvancedInsightsPanel snapshot={snapshot} activeFilter={activeFilter} /> : <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">Advanced insights stay out of the critical path until explicitly opened.</div>}
      </div>
    </section>
  );
}
