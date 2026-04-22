import { CompareWorkspace } from '@/components/CompareWorkspace';
import { fetchBooksFromService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export default async function ComparePage() {
  const books = await fetchBooksFromService();
  return <CompareWorkspace books={books} />;
}
