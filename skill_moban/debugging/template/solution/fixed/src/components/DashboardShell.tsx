'use client';

import { useMemo, useState } from 'react';
import { AlertDrawer } from '@/components/AlertDrawer';
import { TimelinePanel } from '@/components/TimelinePanel';
import { buildHeroSummary, buildLinkedAlertContext, DEFAULT_FILTER, findAlert, findFilter, type DashboardSnapshot } from '@/lib/dashboard';
import { replayRefreshTelemetry } from '@/lib/dashboardRefreshTelemetry';
import { useDashboardFilterState } from '@/hooks/useDashboardFilterState';
import { useDashboardProbe } from '@/hooks/useDashboardProbe';

interface Props {
  snapshot: DashboardSnapshot;
  initialFilter: string;
  initialAlertId: string | null;
}

declare global {
  interface Window {
    __lastTimelineRefreshMs?: number;
  }
}

export function DashboardShell({ snapshot, initialFilter, initialAlertId }: Props) {
  const [activeFilter, setActiveFilter] = useDashboardFilterState(initialFilter || DEFAULT_FILTER, Boolean(initialAlertId));
  const [activeAlertId, setActiveAlertId] = useState<string | null>(initialAlertId);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [refreshNonce, setRefreshNonce] = useState(0);

  useDashboardProbe(activeFilter, activeAlertId, refreshNonce);

  const activeAlert = useMemo(() => findAlert(snapshot.alerts, activeAlertId), [activeAlertId, snapshot.alerts]);
  const activeFilterConfig = useMemo(() => findFilter(snapshot.filters, activeFilter), [activeFilter, snapshot.filters]);

  const handleRefresh = () => {
    const start = performance.now();
    window.dispatchEvent(new Event('dashboard:heartbeat'));
    window.setTimeout(() => {
      replayRefreshTelemetry(activeFilter, activeAlertId, refreshNonce);
      window.__lastTimelineRefreshMs = Math.round(performance.now() - start);
      setRefreshNonce((current) => current + 1);
    }, 120);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_32%),linear-gradient(180deg,#f8fbff_0%,#eef4fb_100%)] px-6 py-8 md:px-10">
      <header className="mx-auto max-w-7xl">
        <div className="rounded-[2rem] border border-slate-200/80 bg-white/85 px-6 py-8 shadow-xl backdrop-blur md:px-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-[0.28em] text-sky-700">Live analytics console</p>
              <h1 data-testid="active-filter-label" className="mt-3 text-3xl font-semibold leading-tight text-slate-950 md:text-4xl">
                {activeFilterConfig.label}
              </h1>
              <p data-testid="hero-summary" className="mt-3 min-h-28 max-w-3xl text-sm leading-7 text-slate-600 md:text-base">
                {buildHeroSummary(snapshot, activeFilter)}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <article className="rounded-2xl bg-slate-950 px-4 py-4 text-white">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-300">Revenue today</div>
                <div className="mt-2 text-2xl font-semibold">${snapshot.summary.revenueToday.toLocaleString()}</div>
              </article>
              <article className="rounded-2xl bg-white px-4 py-4 shadow-sm ring-1 ring-slate-200">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Active alerts</div>
                <div className="mt-2 text-2xl font-semibold text-slate-950">{snapshot.summary.activeAlerts}</div>
              </article>
              <article className="rounded-2xl bg-white px-4 py-4 shadow-sm ring-1 ring-slate-200">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Conversion delta</div>
                <div className="mt-2 text-2xl font-semibold text-rose-600">{snapshot.summary.conversionDelta}%</div>
              </article>
            </div>
          </div>

          <nav className="mt-8 flex flex-wrap gap-3">
            {snapshot.filters.map((filter) => (
              <button
                key={filter.id}
                data-testid={`filter-tab-${filter.id}`}
                onClick={() => setActiveFilter(filter.id)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  activeFilter === filter.id ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <div className="mx-auto mt-8 max-w-7xl">
        <TimelinePanel
          snapshot={snapshot}
          activeFilter={activeFilter}
          isAdvancedOpen={isAdvancedOpen}
          onOpenAdvanced={() => setIsAdvancedOpen(true)}
          onOpenAlert={setActiveAlertId}
          onRefresh={handleRefresh}
        />
      </div>

      <AlertDrawer
        snapshot={snapshot}
        alertId={activeAlertId}
        linkedAlertContext={activeAlert ? buildLinkedAlertContext(activeAlert.owner, activeFilterConfig.label) : null}
        onClose={() => setActiveAlertId(null)}
      />
    </main>
  );
}
