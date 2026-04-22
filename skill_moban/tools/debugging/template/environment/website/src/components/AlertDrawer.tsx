'use client';

import { findAlert, type DashboardSnapshot } from '@/lib/dashboard';

interface Props {
  snapshot: DashboardSnapshot;
  alertId: string | null;
  onClose: () => void;
}

export function AlertDrawer({ snapshot, alertId, onClose }: Props) {
  const alert = findAlert(snapshot.alerts, alertId);

  if (!alert) {
    return null;
  }

  return (
    <aside
      data-testid="alert-drawer"
      className="fixed inset-y-4 right-4 z-20 w-[min(26rem,calc(100vw-2rem))] overflow-auto rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-2xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Live Alert</p>
          <h2 data-testid="alert-drawer-title" className="mt-2 text-2xl font-semibold text-slate-950">
            {alert.title}
          </h2>
        </div>
        <button
          data-testid="close-alert-drawer"
          onClick={onClose}
          className="rounded-full border border-slate-200 px-3 py-1 text-sm font-medium text-slate-700"
        >
          Close
        </button>
      </div>

      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-slate-500">Owner</dt>
          <dd className="mt-2 text-lg font-semibold text-slate-900">{alert.owner}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-slate-500">Impact Delta</dt>
          <dd className="mt-2 text-lg font-semibold text-rose-600">{alert.impactDelta}%</dd>
        </div>
      </dl>

      <p className="mt-6 text-sm leading-7 text-slate-600">{alert.summary}</p>
    </aside>
  );
}
