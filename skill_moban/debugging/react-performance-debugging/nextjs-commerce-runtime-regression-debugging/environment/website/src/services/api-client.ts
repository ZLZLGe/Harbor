import type { CatalogBook } from '@/lib/catalog';

const API_BASE = process.env.EXTERNAL_API_URL || 'http://localhost:3001';

export async function fetchBooksFromService(): Promise<CatalogBook[]> {
  const res = await fetch(`${API_BASE}/api/books`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error('Failed to fetch books');
  }
  return res.json();
}
