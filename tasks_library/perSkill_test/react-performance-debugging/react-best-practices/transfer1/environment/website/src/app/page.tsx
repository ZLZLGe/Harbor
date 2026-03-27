import { fetchActorFromService, fetchItemsFromService, fetchReviewsFromService } from '@/services/api-client';
import { CatalogList } from '@/components/CatalogList';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const actor = await fetchActorFromService();
  const items = await fetchItemsFromService();
  const reviews = await fetchReviewsFromService();

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <header className="mb-8">
        <div className="flex justify-between items-start gap-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-700">Atlas Course Planner</p>
            <h1 className="text-3xl font-bold text-gray-900">Welcome back, {actor.name}</h1>
            <p className="mt-2 text-gray-600">Review live course offerings and pin the next cohort plan.</p>
            <p className="text-gray-500">Tracking {items.length} active courses today.</p>
          </div>
          <a
            href="/benchmarks"
            className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
          >
            Open Benchmarks
          </a>
        </div>
      </header>
      <CatalogList items={items} reviews={reviews} />
    </main>
  );
}
