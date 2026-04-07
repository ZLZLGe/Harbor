import { NextResponse } from 'next/server';
import { fetchBooksFromService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export async function GET() {
  const books = await fetchBooksFromService();
  return NextResponse.json({ books });
}
