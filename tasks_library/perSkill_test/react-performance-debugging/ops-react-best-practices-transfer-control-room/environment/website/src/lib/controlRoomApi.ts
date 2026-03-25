const API_BASE = process.env.EXTERNAL_API_URL || 'http://localhost:3001';

export interface OperatorSession {
  operatorId: string;
  displayName: string;
  region: string;
  token: string;
}

export interface IncidentItem {
  incidentId: string;
  title: string;
  service: string;
  eta: string;
}

export interface ServiceHealthItem {
  service: string;
  status: string;
  saturation: number;
}

export interface DeploymentItem {
  train: string;
  window: string;
  owner: string;
}

export interface ApprovalItem {
  eventId: string;
  service: string;
  severity: string;
  summary: string;
}

export interface PolicyPack {
  eventId: string;
  runbookId: string;
  escalationTarget: string;
}

export interface ConfirmationDraft {
  eventId: string;
  confirmationId: string;
  service: string;
}

export interface ConfirmationResult {
  eventId: string;
  status: string;
  confirmationId: string;
  runbookId: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: 'no-store',
    headers: {
      ...(init?.headers || {}),
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${path}`);
  }

  return response.json() as Promise<T>;
}

export function fetchOperatorSession() {
  return requestJson<OperatorSession>('/api/session');
}

export function fetchIncidentFeed(token: string) {
  return requestJson<IncidentItem[]>('/api/incidents', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchServiceHealth(token: string) {
  return requestJson<ServiceHealthItem[]>('/api/service-health', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchDeploymentLane(token: string) {
  return requestJson<DeploymentItem[]>('/api/deployments', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchApprovalQueue(token: string) {
  return requestJson<ApprovalItem[]>('/api/approvals', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchPolicyPack(eventId: string, token: string) {
  return requestJson<PolicyPack>(`/api/policy/${eventId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchConfirmationDraft(eventId: string, token: string) {
  return requestJson<ConfirmationDraft>(`/api/events/${eventId}/prepare`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function commitEventConfirmation(
  eventId: string,
  token: string,
  confirmationId: string,
  runbookId: string,
) {
  return requestJson<ConfirmationResult>(`/api/events/${eventId}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ confirmationId, runbookId }),
  });
}

export function logEventConfirmation(body: Record<string, unknown>) {
  return requestJson<{ ok: boolean }>('/api/audit', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
