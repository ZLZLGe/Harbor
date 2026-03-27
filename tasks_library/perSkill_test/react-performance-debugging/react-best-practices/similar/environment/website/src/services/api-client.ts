const API_BASE = process.env.EXTERNAL_API_URL || 'http://localhost:3001';

export async function fetchActorFromService() {
  const response = await fetch(`${API_BASE}/api/user`);
  if (!response.ok) throw new Error('Failed to fetch actor');
  return response.json();
}

export async function fetchItemsFromService() {
  const response = await fetch(`${API_BASE}/api/products`);
  if (!response.ok) throw new Error('Failed to fetch items');
  return response.json();
}

export async function fetchReviewsFromService() {
  const response = await fetch(`${API_BASE}/api/reviews`);
  if (!response.ok) throw new Error('Failed to fetch reviews');
  return response.json();
}

export async function fetchConfigFromService() {
  const response = await fetch(`${API_BASE}/api/config`);
  if (!response.ok) throw new Error('Failed to fetch config');
  return response.json();
}

export async function fetchProfileFromService(actorId: string) {
  const response = await fetch(`${API_BASE}/api/profile/${actorId}`);
  if (!response.ok) throw new Error('Failed to fetch profile');
  return response.json();
}

export async function logActionToService(data: unknown) {
  const response = await fetch(`${API_BASE}/api/analytics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to log action');
  return response.json();
}
