'use client';

import { useState } from 'react';
import { rowsForView, type ActivityRecord, type WorkspaceView } from '@/data/activityFeed';

const ROW_HEIGHT = 56;

const views: Array<{ id: WorkspaceView; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'activity', label: 'Activity Feed' },
  { id: 'alerts', label: 'Alerts' },
];

function formatSeverity(severity: ActivityRecord['severity']) {
  if (severity === 'critical') return 'Critical';
  if (severity === 'watch') return 'Watch';
  return 'Healthy';
}

function severityTone(severity: ActivityRecord['severity']) {
  if (severity === 'critical') return 'var(--danger)';
  if (severity === 'watch') return 'var(--warning)';
  return 'var(--success)';
}

export default function AnalyticsTable() {
  const [activeView, setActiveView] = useState<WorkspaceView>('activity');
  const [severityFilter, setSeverityFilter] = useState<'all' | ActivityRecord['severity']>('all');
  const [scrollTop, setScrollTop] = useState(0);
  const rows = rowsForView(activeView).filter((row) =>
    severityFilter === 'all' ? true : row.severity === severityFilter
  );

  const isCondensed =
    (typeof document !== 'undefined'
      ? document.getElementById('activity-scroller')?.scrollHeight ?? 0
      : 0) >
    (typeof document !== 'undefined'
      ? document.getElementById('activity-scroller')?.clientHeight ?? 0
      : 0);

  const windowStart = Math.floor(scrollTop / ROW_HEIGHT) + 1;

  return (
    <section
      className="rounded-[32px] border border-[var(--frame-line)] bg-[var(--frame)] p-5 shadow-[var(--panel-shadow)] lg:p-6"
      style={{ backdropFilter: 'blur(14px)' }}
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">
            Activity workspace
          </p>
          <h2 className="mt-2 text-3xl font-semibold">Live operator traffic</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Review the live stream, urgent alert-only slices, or the compact overview without
            changing the underlying monitoring flow.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          {views.map((view) => (
            <button
              key={view.id}
              data-testid={`view-${view.id}`}
              className="rounded-full border px-4 py-2 text-sm transition-colors"
              style={{
                borderColor: activeView === view.id ? 'var(--accent)' : 'var(--panel-border)',
                backgroundColor: activeView === view.id ? 'var(--accent-soft)' : 'transparent',
              }}
              onClick={() => setActiveView(view.id)}
            >
              {view.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        {(['all', 'healthy', 'watch', 'critical'] as const).map((tone) => (
          <button
            key={tone}
            data-testid={`filter-${tone}`}
            className="rounded-full border px-4 py-2 text-sm"
            style={{
              borderColor: severityFilter === tone ? 'var(--accent)' : 'var(--panel-border)',
              backgroundColor: severityFilter === tone ? 'var(--accent-soft)' : 'transparent',
            }}
            onClick={() => setSeverityFilter(tone)}
          >
            {tone === 'all' ? 'All severities' : tone}
          </button>
        ))}
      </div>

      <div
        data-testid="widget-grid"
        className={`mt-6 grid gap-4 ${isCondensed ? 'grid-cols-1' : 'grid-cols-4'}`}
      >
        <article
          data-testid="summary-card-mounted"
          className="rounded-[24px] border border-[var(--panel-border)] bg-[var(--panel)] p-4"
        >
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Mounted rows</p>
          <p data-testid="rows-mounted-value" className="mt-3 text-3xl font-semibold">
            {rows.length}
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">Everything in the active slice is mounted.</p>
        </article>

        <article
          data-testid="summary-card-window"
          className="rounded-[24px] border border-[var(--panel-border)] bg-[var(--panel)] p-4"
        >
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Window marker</p>
          <p className="mt-3 text-3xl font-semibold">{windowStart}</p>
          <p className="mt-2 text-sm text-[var(--muted)]">Updates with every scroll change.</p>
        </article>

        <article
          data-testid="summary-card-pressure"
          className="rounded-[24px] border border-[var(--panel-border)] bg-[var(--panel)] p-4"
        >
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Queue pressure</p>
          <p className="mt-3 text-3xl font-semibold">
            {rows.slice(0, 30).reduce((sum, row) => sum + row.queueDepth, 0)}
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">Immediate backlog across the visible slice.</p>
        </article>

        <article
          data-testid="summary-card-watch"
          className="rounded-[24px] border border-[var(--panel-border)] bg-[var(--panel)] p-4"
        >
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Needs review</p>
          <p className="mt-3 text-3xl font-semibold">
            {rows.filter((row) => row.severity !== 'healthy').length}
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">Open watch or critical items.</p>
        </article>
      </div>

      <div className="mt-6 overflow-hidden rounded-[28px] border border-[var(--panel-border)] bg-[var(--panel)]">
        <div className="grid grid-cols-[1.15fr_0.85fr_0.7fr_0.9fr_1fr_1.6fr] gap-4 border-b border-[var(--panel-border)] px-5 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          <span>Stream</span>
          <span>Owner</span>
          <span>Status</span>
          <span>Latency</span>
          <span>Queue</span>
          <span>Summary</span>
        </div>

        <div
          id="activity-scroller"
          data-testid="activity-scroller"
          className="h-[420px] overflow-y-auto"
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        >
          {rows.map((row, index) => (
            <div
              key={row.id}
              data-testid="activity-row"
              data-row-id={row.id}
              className="grid grid-cols-[1.15fr_0.85fr_0.7fr_0.9fr_1fr_1.6fr] gap-4 border-b border-[var(--panel-border)] px-5 py-4 text-sm"
              style={{
                minHeight: `${ROW_HEIGHT}px`,
                backgroundColor: index % 2 === 0 ? 'transparent' : 'var(--row-stripe)',
              }}
            >
              <div>
                <p className="font-semibold">{row.id}</p>
                <p className="text-xs text-[var(--muted)]">{row.pipeline}</p>
              </div>
              <span>{row.owner}</span>
              <span style={{ color: severityTone(row.severity) }}>{formatSeverity(row.severity)}</span>
              <span>{row.latencyMs} ms</span>
              <span>{row.queueDepth}</span>
              <span className="min-w-0 truncate">{row.summary}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
