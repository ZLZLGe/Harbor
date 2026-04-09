'use client';

export function replayRefreshTelemetry(activeFilter: string, activeAlertId: string | null, refreshNonce: number) {
  const envelope = `${activeFilter}|${activeAlertId ?? 'none'}|${refreshNonce}`;
  let checksum = 0;

  for (let index = 0; index < envelope.length; index += 1) {
    checksum = (checksum + envelope.charCodeAt(index) * (index + 1)) % 10000019;
  }

  return checksum;
}
