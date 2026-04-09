export interface CatalogBook {
  id: string;
  title: string;
  author: string;
  authorBirthYear: number | null;
  authorDeathYear: number | null;
  shelves: string[];
  subjects: string[];
  summary: string;
  language: string;
  downloadCount: number;
  coverUrl: string | null;
  htmlUrl: string | null;
  textUrl: string | null;
}

export interface ShelfOption {
  slug: string;
  label: string;
  teaser: string;
  subjectNeedle?: string;
}

export const FEATURED_SHELVES: ShelfOption[] = [
  {
    slug: 'category-classics-of-literature',
    label: 'Category: Classics of Literature',
    teaser: 'High-circulation titles used for homepage curation and merch QA.',
  },
  {
    slug: 'gothic-fiction',
    label: 'Gothic Fiction',
    teaser: 'Dark, psychologically unstable classics with large descriptive hero copy.',
    subjectNeedle: 'Gothic',
  },
  {
    slug: 'category-romance',
    label: 'Category: Romance',
    teaser: 'Reader-favorite relationship stories often pinned for campaign reviews.',
    subjectNeedle: 'Love stories',
  },
  {
    slug: 'category-adventure',
    label: 'Category: Adventure',
    teaser: 'Voyages, sea stories, and travel-heavy fiction used in seasonal promos.',
    subjectNeedle: 'Adventure',
  },
];

export const DEFAULT_SHELF = FEATURED_SHELVES[0].slug;

export function findShelf(slug: string): ShelfOption {
  return FEATURED_SHELVES.find((option) => option.slug === slug) ?? FEATURED_SHELVES[0];
}

export function matchesShelf(book: CatalogBook, slug: string): boolean {
  const option = findShelf(slug);
  const shelfHit = book.shelves.some((shelf) => slugify(shelf) === option.slug);
  const subjectHit = option.subjectNeedle
    ? book.subjects.some((subject) => subject.toLowerCase().includes(option.subjectNeedle!.toLowerCase()))
    : false;
  return shelfHit || subjectHit;
}

export function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export function shortSummary(book: CatalogBook): string {
  return book.summary.replace(/\s+\(This is an automatically generated summary\.\)$/, '');
}
