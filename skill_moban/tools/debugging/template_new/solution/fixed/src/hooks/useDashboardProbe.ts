'use client';

import { useEffect } from 'react';

declare global {
  interface Window {
    __dashboardPulseRuns?: number;
    __lastTimelineRefreshMs?: number;
  }
}

export function useDashboardProbe(activeFilter: string, activeAlertId: string | null, refreshNonce: number) {
  useEffect(() => {
    const pulse = () => {
      const payload = `${activeFilter}|${activeAlertId ?? 'none'}|${refreshNonce}|${window.innerWidth}|${document.visibilityState}`.repeat(320);
      let checksum = 0;
      for (let index = 0; index < payload.length; index += 1) {
        checksum = (checksum + payload.charCodeAt(index) * (index + 1)) % 10000019;
      }
      window.__dashboardPulseRuns = (window.__dashboardPulseRuns ?? 0) + (checksum % 4) + 1;
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        pulse();
      }
    };

    window.addEventListener('resize', pulse);
    window.addEventListener('dashboard:heartbeat', pulse);
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      window.removeEventListener('resize', pulse);
      window.removeEventListener('dashboard:heartbeat', pulse);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [activeAlertId, activeFilter, refreshNonce]);
}
