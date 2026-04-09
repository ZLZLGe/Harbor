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

function shouldRestoreStoredFilter(isDeepLinkEntry: boolean, savedAt?: number): boolean {
  if (isDeepLinkEntry) {
    return false;
  }

  if (!savedAt) {
    return true;
  }

  return Date.now() - savedAt < RESTORE_WINDOW_MS;
}

function resolveInitialFilter(initialFilter: string, isDeepLinkEntry: boolean): string {
  const fallbackFilter = initialFilter || DEFAULT_FILTER;
  const stored = readStoredDashboardContext();
  const restoredFilter = stored?.filterId;

  if (!restoredFilter || restoredFilter === fallbackFilter) {
    return fallbackFilter;
  }

  if (!shouldRestoreStoredFilter(isDeepLinkEntry, stored?.savedAt)) {
    return fallbackFilter;
  }

  return restoredFilter;
}

export function useDashboardFilterState(initialFilter: string, isDeepLinkEntry: boolean) {
  const [activeFilter, setActiveFilter] = useState(() => resolveInitialFilter(initialFilter, isDeepLinkEntry));

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
