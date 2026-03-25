import { NextResponse } from 'next/server';

import { confirmControlRoomEvent } from '@/lib/getControlRoomData';

export const dynamic = 'force-dynamic';

export async function POST(
  _request: Request,
  context: { params: { eventId: string } },
) {
  const payload = await confirmControlRoomEvent(context.params.eventId);
  return NextResponse.json(payload);
}
