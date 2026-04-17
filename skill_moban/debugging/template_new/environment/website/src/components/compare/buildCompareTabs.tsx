'use client';

import type { ReactNode } from 'react';
import groupBy from 'lodash/groupBy';
import orderBy from 'lodash/orderBy';
import uniq from 'lodash/uniq';
import { mean, median, quantileSeq, std, variance } from 'mathjs';
import type { CatalogBook } from '@/lib/catalog';

interface CompareTabDefinition {
  id: 'overview' | 'advanced';
  label: string;
  render: () => ReactNode;
}

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

function AdvancedPanel({ books }: { books: CatalogBook[] }) {
  const downloadCounts = books.map((book) => book.downloadCount);
  const subjectCounts = books.map((book) => book.subjects.length);
  const shelfClusters = groupBy(
    books.flatMap((book) => book.shelves.slice(0, 2).map((shelf) => ({ shelf, title: book.title }))),
    'shelf',
  );
  const rankedBooks = orderBy(
    books.map((book) => ({
      title: book.title,
      subjectBreadth: book.subjects.length,
      shelfBreadth: uniq(book.shelves).length,
      reachScore: book.downloadCount / Math.max(book.subjects.length, 1),
    })),
    ['reachScore'],
    ['desc'],
  );

  return (
    <div data-testid="advanced-content" className="rounded-[1.75rem] border border-stone-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-stone-900">Advanced analysis</h2>
      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        <div className="rounded-2xl bg-stone-50 p-4">
          <h3 className="font-medium text-stone-800">Download distribution</h3>
          <dl className="mt-3 space-y-2 text-sm text-stone-600">
            <div className="flex justify-between"><dt>Mean</dt><dd>{Math.round(Number(mean(downloadCounts))).toLocaleString()}</dd></div>
            <div className="flex justify-between"><dt>Median</dt><dd>{Math.round(Number(median(downloadCounts))).toLocaleString()}</dd></div>
            <div className="flex justify-between"><dt>Std dev</dt><dd>{Math.round(Number(std(downloadCounts))).toLocaleString()}</dd></div>
            <div className="flex justify-between"><dt>Variance</dt><dd>{Math.round(Number(variance(downloadCounts))).toLocaleString()}</dd></div>
            <div className="flex justify-between"><dt>Q1</dt><dd>{Math.round(Number(quantileSeq(downloadCounts, 0.25))).toLocaleString()}</dd></div>
            <div className="flex justify-between"><dt>Q3</dt><dd>{Math.round(Number(quantileSeq(downloadCounts, 0.75))).toLocaleString()}</dd></div>
          </dl>
        </div>

        <div className="rounded-2xl bg-stone-50 p-4">
          <h3 className="font-medium text-stone-800">Subject breadth</h3>
          <dl className="mt-3 space-y-2 text-sm text-stone-600">
            <div className="flex justify-between"><dt>Mean</dt><dd>{Number(mean(subjectCounts)).toFixed(2)}</dd></div>
            <div className="flex justify-between"><dt>Median</dt><dd>{Number(median(subjectCounts)).toFixed(2)}</dd></div>
            <div className="flex justify-between"><dt>Std dev</dt><dd>{Number(std(subjectCounts)).toFixed(2)}</dd></div>
          </dl>
          <ul className="mt-4 space-y-2 text-sm text-stone-600">
            {Object.entries(shelfClusters).slice(0, 4).map(([shelf, entries]) => (
              <li key={shelf} className="flex justify-between gap-3">
                <span className="line-clamp-1">{shelf}</span>
                <span className="font-medium text-stone-900">{entries.length}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl bg-stone-50 p-4">
          <h3 className="font-medium text-stone-800">Reach score</h3>
          <ol className="mt-3 space-y-2 text-sm text-stone-600">
            {rankedBooks.slice(0, 5).map((book, index) => (
              <li key={book.title} className="flex items-center justify-between gap-3">
                <span>{index + 1}. {book.title}</span>
                <span className="font-medium text-stone-900">{book.reachScore.toFixed(1)}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

export function buildCompareTabs(books: CatalogBook[]): CompareTabDefinition[] {
  return [
    {
      id: 'overview',
      label: 'Overview',
      render: () => <OverviewPanel books={books} />,
    },
    {
      id: 'advanced',
      label: 'Advanced analysis',
      render: () => <AdvancedPanel books={books} />,
    },
  ];
}
