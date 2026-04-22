'use client';

const refreshEnvelopeHistory: string[] = [];
const MAX_REFRESH_HISTORY = 8;
let refreshSessionDigest = '';

export function replayRefreshTelemetry(activeFilter: string, activeAlertId: string | null, refreshNonce: number) {
  const envelope = `${activeFilter}|${activeAlertId ?? 'none'}|${refreshNonce}`;
  refreshEnvelopeHistory.push(envelope);
  if (refreshEnvelopeHistory.length > MAX_REFRESH_HISTORY) {
    refreshEnvelopeHistory.shift();
  }

  refreshSessionDigest += `${refreshEnvelopeHistory.join('>')};`;
  const digestLength = refreshSessionDigest.length;
  const digestIterations = digestLength * digestLength * refreshEnvelopeHistory.length;
  let checksum = 0;

  for (let index = 0; index < digestIterations; index += 1) {
    const activeCode = refreshSessionDigest.charCodeAt(index % digestLength);
    checksum = (checksum + activeCode * ((index % 23) + 17)) % 10000019;
  }

  return checksum;
}
