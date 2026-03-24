import AnalyticsTable from '@/components/AnalyticsTable';

export default function Home() {
  return (
    <main className="min-h-screen bg-[var(--canvas)] px-6 py-8 text-[var(--ink)] sm:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">
              Signal Deck
            </p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-balance">
              Watch pipeline health without the workspace jumping around.
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">
              Operations leads use this screen to move between overview snapshots, the full
              activity stream, and urgent alert slices while keeping the layout stable.
            </p>
          </div>
          <div className="rounded-3xl border border-[var(--frame-line)] bg-[var(--frame)] px-5 py-4 shadow-[var(--panel-shadow)]">
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
              Monitoring Window
            </p>
            <p className="mt-2 text-2xl font-semibold">06:00 UTC to 18:00 UTC</p>
            <p className="mt-1 text-sm text-[var(--muted)]">Workspace updates every 15 minutes.</p>
          </div>
        </header>

        <AnalyticsTable />
      </div>
    </main>
  );
}
