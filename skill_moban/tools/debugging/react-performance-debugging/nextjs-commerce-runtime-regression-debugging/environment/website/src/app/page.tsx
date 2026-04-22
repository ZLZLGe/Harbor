import { BookCatalog } from '@/components/BookCatalog';
import { DEFAULT_SHELF } from '@/lib/catalog';
import { fetchBooksFromService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

interface Props {
  searchParams?: {
    shelf?: string;
  };
}

export default async function HomePage({ searchParams }: Props) {
  const books = await fetchBooksFromService();
  const hasLinkedReview = typeof searchParams?.shelf === 'string';
  const initialShelf = hasLinkedReview ? searchParams.shelf! : DEFAULT_SHELF;

  return (
    <main className="min-h-screen bg-stone-50 px-6 py-10 md:px-10">
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Production reading room</p>
          <h1 className="mt-3 text-4xl font-semibold text-stone-900">Merch shelf diagnostics</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-600">
            Audit the live catalog shelf using the same public-domain metadata snapshot that feeds compare and shortlist workflows.
          </p>
        </div>
        <a
          href="/compare"
          className="inline-flex items-center rounded-full bg-stone-900 px-5 py-3 text-sm font-medium text-stone-50 transition hover:bg-stone-800"
        >
          Open compare workspace
        </a>
      </header>
      <BookCatalog books={books} initialShelf={initialShelf} entryIntent={hasLinkedReview ? 'linked-review' : 'catalog-home'} />
    </main>
  );
}
