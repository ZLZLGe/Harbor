'use client';

import { useMemo, useState } from 'react';
import { BookCard } from './BookCard';
import { DEFAULT_SHELF, FEATURED_SHELVES, findShelf, matchesShelf, shortSummary, type CatalogBook } from '@/lib/catalog';
import { useShelfProbe } from '@/hooks/useShelfProbe';
import { type ReviewEntryIntent, useReviewShelfState } from '@/hooks/useReviewShelfState';

interface Props {
  books: CatalogBook[];
  initialShelf: string;
  entryIntent: ReviewEntryIntent;
}

export function BookCatalog({ books, initialShelf, entryIntent }: Props) {
  const [activeShelf, setActiveShelf] = useReviewShelfState(initialShelf || DEFAULT_SHELF, entryIntent);
  const [searchTerm, setSearchTerm] = useState('');
  const [shortlist, setShortlist] = useState<string[]>([]);

  useShelfProbe(activeShelf, searchTerm);

  const visibleBooks = useMemo(() => {
    return books
      .filter((book) => matchesShelf(book, activeShelf))
      .filter((book) => {
        const haystack = `${book.title} ${book.author} ${book.subjects.join(' ')}`.toLowerCase();
        return haystack.includes(searchTerm.toLowerCase());
      });
  }, [books, activeShelf, searchTerm]);

  const activeShelfConfig = findShelf(activeShelf);
  const heroBook = visibleBooks[0] ?? books[0];

  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] bg-stone-900 px-6 py-8 text-stone-50 shadow-xl md:px-10">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.32em] text-stone-300">Runtime reading room</p>
            <h2 data-testid="active-shelf-label" className="mt-3 text-3xl font-semibold leading-tight md:text-4xl">
              {activeShelfConfig.label}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-200 md:text-base" data-testid="shelf-summary">
              {activeShelfConfig.teaser} Featured title: {heroBook.title} by {heroBook.author}. {shortSummary(heroBook)}
            </p>
          </div>
          <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
            <div className="text-xs uppercase tracking-[0.18em] text-stone-300">Pinned shortlist</div>
            <div data-testid="shortlist-count" className="mt-2 text-2xl font-semibold">
              {shortlist.length}
            </div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4 rounded-[1.75rem] border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap gap-3">
          {FEATURED_SHELVES.map((shelf) => (
            <button
              key={shelf.slug}
              data-testid={`shelf-tab-${shelf.slug}`}
              onClick={() => setActiveShelf(shelf.slug)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                activeShelf === shelf.slug
                  ? 'bg-stone-900 text-stone-50'
                  : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
              }`}
            >
              {shelf.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <input
            data-testid="shelf-search"
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search titles, authors, or subjects"
            className="w-full rounded-full border border-stone-300 px-4 py-3 text-sm outline-none ring-0 transition placeholder:text-stone-400 focus:border-stone-900 md:max-w-md"
          />
          <div className="text-sm text-stone-600">
            Showing <span className="font-semibold text-stone-900">{visibleBooks.length}</span> titles from the active shelf
          </div>
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {visibleBooks.map((book) => (
          <BookCard
            key={book.id}
            book={book}
            isShortlisted={shortlist.includes(book.id)}
            onToggleShortlist={(id) => {
              setShortlist((current) => (current.includes(id) ? current.filter((entry) => entry !== id) : [...current, id]));
            }}
          />
        ))}
      </section>
    </div>
  );
}
