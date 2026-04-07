'use client';

import { useEffect, useState } from 'react';
import { DEFAULT_SHELF } from '@/lib/catalog';

export type ReviewEntryIntent = 'catalog-home' | 'linked-review';

interface StoredReviewContext {
  shelf?: string;
  savedAt?: number;
}

const LEGACY_STORAGE_KEY = 'reader-active-shelf';
const REVIEW_CONTEXT_KEY = 'reader-review-context';
const RESTORE_WINDOW_MS = 6 * 60 * 60 * 1000;

function readStoredReviewContext(): StoredReviewContext | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawContext = window.localStorage.getItem(REVIEW_CONTEXT_KEY);
  if (rawContext) {
    try {
      return JSON.parse(rawContext) as StoredReviewContext;
    } catch {
      return {
        shelf: window.localStorage.getItem(LEGACY_STORAGE_KEY) ?? undefined,
      };
    }
  }

  const legacyShelf = window.localStorage.getItem(LEGACY_STORAGE_KEY);
  return legacyShelf ? { shelf: legacyShelf } : null;
}

function shouldRestorePersistedShelf(entryIntent: ReviewEntryIntent, savedAt?: number): boolean {
  if (entryIntent !== 'catalog-home') {
    return false;
  }

  if (!savedAt) {
    return true;
  }

  return Date.now() - savedAt < RESTORE_WINDOW_MS;
}

export function useReviewShelfState(initialShelf: string, entryIntent: ReviewEntryIntent) {
  const [activeShelf, setActiveShelf] = useState(initialShelf || DEFAULT_SHELF);

  useEffect(() => {
    const stored = readStoredReviewContext();
    const restoredShelf = stored?.shelf;

    if (!restoredShelf || restoredShelf === activeShelf) {
      return;
    }

    if (!shouldRestorePersistedShelf(entryIntent, stored?.savedAt)) {
      return;
    }

    setActiveShelf(restoredShelf);
  }, [activeShelf, entryIntent]);

  useEffect(() => {
    window.localStorage.setItem(LEGACY_STORAGE_KEY, activeShelf);
    window.localStorage.setItem(
      REVIEW_CONTEXT_KEY,
      JSON.stringify({
        shelf: activeShelf,
        savedAt: Date.now(),
      }),
    );
  }, [activeShelf]);

  return [activeShelf, setActiveShelf] as const;
}
