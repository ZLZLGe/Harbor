import { NextResponse } from 'next/server';
import { fetchActorFromService, fetchItemsFromService, logActionToService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export async function GET() {
  const actor = await fetchActorFromService();
  const items = await fetchItemsFromService();

  await logActionToService({ actorId: actor.id, action: 'view_list', count: items.length });

  return NextResponse.json({ items });
}
