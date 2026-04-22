'use client';

import { useEffect, useState } from 'react';
import { DEFAULT_FILTER } from '@/lib/dashboard';

interface StoredDashboardContext {
  filterId?: string;
  savedAt?: number;
}

const LEGACY_STORAGE_KEY = 'dashboard-active-filter';
const DASHBOARD_CONTEXT_KEY = 'dashboard-context';
const RESTORE_WINDOW_MS = 6 * 60 * 60 * 1000;

interface FilterRestorePlan {
  filterId: string;
  delayMs: number;
}

function readStoredDashboardContext(): StoredDashboardContext | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawContext = window.localStorage.getItem(DASHBOARD_CONTEXT_KEY);
  if (rawContext) {
    try {
      return JSON.parse(rawContext) as StoredDashboardContext;
    } catch {
      return {
        filterId: window.localStorage.getItem(LEGACY_STORAGE_KEY) ?? undefined,
      };
    }
  }

  const legacyFilter = window.localStorage.getItem(LEGACY_STORAGE_KEY);
  return legacyFilter ? { filterId: legacyFilter } : null;
}

function buildFilterRestorePlan(
  initialFilter: string,
  activeFilter: string,
  isDeepLinkEntry: boolean,
): FilterRestorePlan | null {
  if (typeof window === 'undefined') {
    return null;
  }

  if (!window.matchMedia('(max-width: 900px)').matches) {
    return null;
  }

  const stored = readStoredDashboardContext();
  const restoredFilter = stored?.filterId;

  if (!restoredFilter || restoredFilter === activeFilter) {
    return null;
  }

  if (stored?.savedAt && Date.now() - stored.savedAt >= RESTORE_WINDOW_MS) {
    return null;
  }

  if (!isDeepLinkEntry && restoredFilter === initialFilter) {
    return null;
  }

  return {
    filterId: restoredFilter,
    delayMs: isDeepLinkEntry ? 180 : 0,
  };
}

export function useDashboardFilterState(initialFilter: string, isDeepLinkEntry: boolean) {
  const [activeFilter, setActiveFilter] = useState(initialFilter || DEFAULT_FILTER);

  useEffect(() => {
    const restorePlan = buildFilterRestorePlan(initialFilter, activeFilter, isDeepLinkEntry);
    if (!restorePlan) {
      return;
    }

    const timer = window.setTimeout(() => {
      setActiveFilter(restorePlan.filterId);
    }, restorePlan.delayMs);

    return () => {
      window.clearTimeout(timer);
    };
  }, [activeFilter, initialFilter, isDeepLinkEntry]);

  useEffect(() => {
    window.localStorage.setItem(LEGACY_STORAGE_KEY, activeFilter);
    window.localStorage.setItem(
      DASHBOARD_CONTEXT_KEY,
      JSON.stringify({
        filterId: activeFilter,
        savedAt: Date.now(),
      }),
    );
  }, [activeFilter]);

  return [activeFilter, setActiveFilter] as const;
}
