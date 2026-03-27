import { NextResponse } from 'next/server';
import { fetchActorFromService, fetchConfigFromService, fetchProfileFromService } from '@/services/api-client';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  await request.json().catch(() => ({}));

  const actorPromise = fetchActorFromService();
  const configPromise = fetchConfigFromService();
  const profilePromise = actorPromise.then((actor) => fetchProfileFromService(actor.id));

  const [actor, config, profile] = await Promise.all([actorPromise, configPromise, profilePromise]);

  return NextResponse.json({
    success: true,
    actor: { id: actor.id, name: actor.name },
    profile,
    config: { currency: config.currency },
  });
}
