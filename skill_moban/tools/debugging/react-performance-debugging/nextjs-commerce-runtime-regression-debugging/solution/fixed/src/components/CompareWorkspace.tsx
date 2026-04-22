'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';
import type { CatalogBook } from '@/lib/catalog';

interface Props {
  books: CatalogBook[];
}

const CompareAdvancedPanel = dynamic(
  () => import('./CompareAdvancedPanel').then((module) => module.CompareAdvancedPanel),
  {
    ssr: false,
    loading: () => <div className="rounded-[1.75rem] border border-stone-200 bg-white p-6 shadow-sm">Loading advanced analysis…</div>,
  },
);

function OverviewPanel({ books }: { books: CatalogBook[] }) {
  return (
    <div className="rounded-[1.75rem] border border-stone-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-stone-900">Compare shortlist</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-stone-600">Title</th>
              <th className="px-4 py-3 text-left font-medium text-stone-600">Author</th>
              <th className="px-4 py-3 text-left font-medium text-stone-600">Primary shelf</th>
              <th className="px-4 py-3 text-right font-medium text-stone-600">Downloads</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {books.map((book) => (
              <tr key={book.id}>
                <td className="px-4 py-3 text-stone-900">{book.title}</td>
                <td className="px-4 py-3 text-stone-600">{book.author}</td>
                <td className="px-4 py-3 text-stone-600">{book.shelves[0] ?? 'Unassigned'}</td>
                <td className="px-4 py-3 text-right text-stone-900">{book.downloadCount.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CompareWorkspace({ books }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'advanced'>('overview');
  const compareBooks = useMemo(
    () => [...books.slice(0, 6)].sort((left, right) => right.downloadCount - left.downloadCount),
    [books],
  );

  return (
    <main className="min-h-screen bg-stone-50 px-6 py-10 md:px-10">
      <header className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Merch compare</p>
          <h1 className="mt-2 text-3xl font-semibold text-stone-900">Reader favorites side by side</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
            Compare six high-circulation public-domain titles before publishing shelf changes.
          </p>
        </div>
        <a href="/" className="text-sm font-medium text-stone-700 underline-offset-4 hover:underline">Back to shelves</a>
      </header>

      <div className="mb-6 border-b border-stone-200">
        <nav className="flex gap-3">
          <button
            data-testid="tab-overview"
            onClick={() => setActiveTab('overview')}
            className={`rounded-t-2xl px-4 py-3 text-sm font-medium ${
              activeTab === 'overview' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600'
            }`}
          >
            Overview
          </button>
          <button
            data-testid="tab-advanced"
            onClick={() => setActiveTab('advanced')}
            className={`rounded-t-2xl px-4 py-3 text-sm font-medium ${
              activeTab === 'advanced' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600'
            }`}
          >
            Advanced analysis
          </button>
        </nav>
      </div>

      {activeTab === 'overview' ? <OverviewPanel books={compareBooks} /> : <CompareAdvancedPanel books={compareBooks} />}
    </main>
  );
}
