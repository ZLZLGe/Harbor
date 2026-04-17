'use client';

import type { CatalogBook } from '@/lib/catalog';

interface Props {
  book: CatalogBook;
  isShortlisted: boolean;
  onToggleShortlist: (id: string) => void;
}

export function BookCard({ book, isShortlisted, onToggleShortlist }: Props) {
  return (
    <article data-testid={`book-card-${book.id}`} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Reader shelf</p>
          <h3 className="mt-2 text-lg font-semibold leading-tight text-stone-900">{book.title}</h3>
          <p className="mt-1 text-sm text-stone-600">{book.author}</p>
        </div>
        <div className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700">
          {book.language.toUpperCase()}
        </div>
      </div>

      <p className="line-clamp-4 min-h-24 text-sm leading-6 text-stone-700">
        {book.summary}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {book.shelves.slice(0, 2).map((shelf) => (
          <span key={shelf} className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-900">
            {shelf}
          </span>
        ))}
      </div>

      <div className="mt-5 flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Downloads</div>
          <div className="text-lg font-semibold text-stone-900">{book.downloadCount.toLocaleString()}</div>
        </div>
        <button
          data-testid={`save-book-${book.id}`}
          onClick={() => onToggleShortlist(book.id)}
          className={`rounded-full px-4 py-2 text-sm font-medium transition ${
            isShortlisted ? 'bg-stone-900 text-stone-50' : 'bg-stone-100 text-stone-800 hover:bg-stone-200'
          }`}
        >
          {isShortlisted ? 'Pinned' : 'Pin to shortlist'}
        </button>
      </div>
    </article>
  );
}
