import { NextResponse } from 'next/server';
import { fetchActorFromService, fetchConfigFromService, fetchProfileFromService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  await request.json().catch(() => ({}));

  const [actor, config] = await Promise.all([fetchActorFromService(), fetchConfigFromService()]);
  const profile = await fetchProfileFromService(actor.id);

  return NextResponse.json({
    success: true,
    actor: { id: actor.id, name: actor.name },
    profile,
    config: { currency: config.currency },
  });
}
