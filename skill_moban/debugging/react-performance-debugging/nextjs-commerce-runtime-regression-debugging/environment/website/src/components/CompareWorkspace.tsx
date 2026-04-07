'use client';

import orderBy from 'lodash/orderBy';
import { useMemo, useState } from 'react';
import type { CatalogBook } from '@/lib/catalog';
import { buildCompareTabs } from './compare/buildCompareTabs';

interface Props {
  books: CatalogBook[];
}

export function CompareWorkspace({ books }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'advanced'>('overview');
  const compareBooks = useMemo(() => orderBy(books.slice(0, 6), ['downloadCount'], ['desc']), [books]);
  const tabs = useMemo(() => buildCompareTabs(compareBooks), [compareBooks]);
  const selectedTab = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  return (
    <main className="min-h-screen bg-stone-50 px-6 py-10 md:px-10">
      <header className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Merch compare</p>
          <h1 className="mt-2 text-3xl font-semibold text-stone-900">Reader favorites side by side</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
            Compare six high-circulation public-domain titles before publishing shelf changes. Keep the review flow light enough
            that merch can inspect advanced analysis only when it is needed.
          </p>
        </div>
        <a href="/" className="text-sm font-medium text-stone-700 underline-offset-4 hover:underline">Back to shelves</a>
      </header>

      <div className="mb-6 border-b border-stone-200">
        <nav className="flex gap-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              data-testid={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-t-2xl px-4 py-3 text-sm font-medium ${
                activeTab === tab.id ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {selectedTab.render()}
    </main>
  );
}
