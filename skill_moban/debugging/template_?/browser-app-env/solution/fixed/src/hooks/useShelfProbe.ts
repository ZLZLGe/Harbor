'use client';

import { useEffect } from 'react';

declare global {
  interface Window {
    __reviewPulseRuns?: number;
  }
}

export function useShelfProbe(activeShelf: string, searchTerm: string) {
  useEffect(() => {
    const probe = () => {
      const payload = `${activeShelf}|${searchTerm}|${window.innerWidth}|${document.visibilityState}`.repeat(320);
      let checksum = 0;
      for (let i = 0; i < payload.length; i += 1) {
        checksum = (checksum + payload.charCodeAt(i) * (i + 1)) % 10000019;
      }
      window.__reviewPulseRuns = (window.__reviewPulseRuns ?? 0) + checksum % 4 + 1;
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        probe();
      }
    };

    window.addEventListener('resize', probe);
    window.addEventListener('catalog:heartbeat', probe);
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      window.removeEventListener('resize', probe);
      window.removeEventListener('catalog:heartbeat', probe);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [activeShelf, searchTerm]);
}
