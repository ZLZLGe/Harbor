'use client';

        import { useState } from 'react';
        import dynamic from 'next/dynamic';
        import groupBy from 'lodash/groupBy';
        import sortBy from 'lodash/sortBy';
        import meanBy from 'lodash/meanBy';
        import sumBy from 'lodash/sumBy';
        import maxBy from 'lodash/maxBy';
        import minBy from 'lodash/minBy';

        interface CatalogItem {
          id: string;
          name: string;
          price: number;
          category: string;
          rating: number;
          reviews: number;
          inStock: boolean;
        }

        const ITEMS: CatalogItem[] = [
  { id: '1', name: 'Package Aurora', price: 920.0, category: 'City', rating: 4.5, reviews: 620, inStock: true },
  { id: '2', name: 'Package Solstice', price: 1180.0, category: 'Adventure', rating: 4.2, reviews: 540, inStock: true },
  { id: '3', name: 'Package Meridian', price: 1425.0, category: 'Luxury', rating: 4.8, reviews: 430, inStock: false },
  { id: '4', name: 'Package Drift', price: 760.0, category: 'Beach', rating: 4.1, reviews: 710, inStock: true },
  { id: '5', name: 'Package Northstar', price: 1010.0, category: 'Expedition', rating: 4.4, reviews: 488, inStock: true }
];

        function Overview({ items }: { items: CatalogItem[] }) {
          const sorted = sortBy(items, 'price');
          const categoryCount = Object.keys(groupBy(items, 'category')).length;
          const avgPrice = meanBy(items, 'price');
          const totalReviews = sumBy(items, 'reviews');
          const bestRated = maxBy(items, 'rating');
          const cheapest = minBy(items, 'price');

          return (
            <section className="rounded-xl bg-white p-6 shadow-md">
              <h2 className="mb-4 text-xl font-bold">Offer Overview</h2>
              <div className="mb-6 grid grid-cols-4 gap-4 text-center">
                <div className="rounded-lg bg-blue-50 p-4">
                  <div className="text-2xl font-bold text-blue-600">${avgPrice.toFixed(2)}</div>
                  <div className="text-sm text-gray-600">Average Price</div>
                </div>
                <div className="rounded-lg bg-green-50 p-4">
                  <div className="text-2xl font-bold text-green-600">{totalReviews.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">Review Volume</div>
                </div>
                <div className="rounded-lg bg-amber-50 p-4">
                  <div className="text-2xl font-bold text-amber-600">{bestRated?.name}</div>
                  <div className="text-sm text-gray-600">Top Rated</div>
                </div>
                <div className="rounded-lg bg-fuchsia-50 p-4">
                  <div className="text-2xl font-bold text-fuchsia-600">{categoryCount}</div>
                  <div className="text-sm text-gray-600">Categories</div>
                </div>
              </div>
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left">Package</th>
                    <th className="px-4 py-3 text-right">Price</th>
                    <th className="px-4 py-3 text-right">Rating</th>
                    <th className="px-4 py-3 text-right">Reviews</th>
                    <th className="px-4 py-3 text-right">Best Value</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((item) => (
                    <tr key={item.id} className="border-t">
                      <td className="px-4 py-3 font-medium">{item.name}</td>
                      <td className="px-4 py-3 text-right">${item.price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{item.rating}</td>
                      <td className="px-4 py-3 text-right">{item.reviews.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right">{cheapest?.name === item.name ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          );
        }

        const AdvancedPanel = dynamic(() => import('@/components/AdvancedAnalysis'), {
          loading: () => <section className="rounded-xl bg-white p-6 shadow-md text-center">Loading analysis...</section>,
        });

        export default function AnalysisPage() {
          const [activeTab, setActiveTab] = useState<'overview' | 'advanced'>('overview');

          return (
            <main className="min-h-screen bg-gray-50 p-8">
              <header className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Fare Analysis</h1>
                <p className="text-gray-600">Compare {ITEMS.length} active options side by side.</p>
              </header>

              <div className="mb-6 border-b border-gray-200">
                <nav className="flex gap-4">
                  <button
                    data-testid="tab-overview"
                    onClick={() => setActiveTab('overview')}
                    className={`border-b-2 py-3 px-4 font-medium transition-colors ${
                      activeTab === 'overview'
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    data-testid="tab-advanced"
                    onClick={() => setActiveTab('advanced')}
                    className={`border-b-2 py-3 px-4 font-medium transition-colors ${
                      activeTab === 'advanced'
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Detailed Model
                  </button>
                </nav>
              </div>

              {activeTab === 'overview' ? <Overview items={ITEMS} /> : <AdvancedPanel items={ITEMS} />}

              <div className="mt-6 text-center">
                <a href="/" className="text-blue-600 hover:underline">← Back to package list</a>
              </div>
            </main>
          );
        }
