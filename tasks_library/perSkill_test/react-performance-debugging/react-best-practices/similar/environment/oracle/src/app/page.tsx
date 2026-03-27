import { fetchActorFromService, fetchItemsFromService, fetchReviewsFromService } from '@/services/api-client';
import { CatalogList } from '@/components/CatalogList';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const [actor, items, reviews] = await Promise.all([
    fetchActorFromService(),
    fetchItemsFromService(),
    fetchReviewsFromService(),
  ]);

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <header className="mb-8">
        <div className="flex justify-between items-start gap-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-700">Meridian Gear Shop</p>
            <h1 className="text-3xl font-bold text-gray-900">Welcome back, {actor.name}</h1>
            <p className="mt-2 text-gray-600">Browse live inventory and shortlist the best gear bundles.</p>
            <p className="text-gray-500">Tracking {items.length} active items today.</p>
          </div>
          <a
            href="/compare"
            className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
          >
            Compare Products
          </a>
        </div>
      </header>
      <CatalogList items={items} reviews={reviews} />
    </main>
  );
}
