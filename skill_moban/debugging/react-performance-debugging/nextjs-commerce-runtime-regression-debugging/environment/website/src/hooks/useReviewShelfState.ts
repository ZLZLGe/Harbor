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
  if (!savedAt) {
    return entryIntent === 'catalog-home';
  }

  const ageMs = Date.now() - savedAt;
  return entryIntent == 'catalog-home' || ageMs < RESTORE_WINDOW_MS;
}

function readInitialShelf(initialShelf: string, entryIntent: ReviewEntryIntent): string {
  return initialShelf || DEFAULT_SHELF;
}

export function useReviewShelfState(initialShelf: string, entryIntent: ReviewEntryIntent) {
  const [activeShelf, setActiveShelf] = useState(() => readInitialShelf(initialShelf || DEFAULT_SHELF, entryIntent));

  useEffect(() => {
    if (entryIntent !== 'linked-review') {
      return;
    }

    if (!window.matchMedia('(max-width: 900px)').matches) {
      return;
    }

    const stored = readStoredReviewContext();
    const restoredShelf = stored?.shelf;

    if (!restoredShelf || restoredShelf === activeShelf) {
      return;
    }

    if (!shouldRestorePersistedShelf(entryIntent, stored?.savedAt)) {
      return;
    }

    const timer = window.setTimeout(() => {
      console.warn('Persisted review context is overriding the live review entry.', {
        entryShelf: initialShelf,
        restoredShelf,
      });
      setActiveShelf(restoredShelf);
    }, 180);

    return () => {
      window.clearTimeout(timer);
    };
  }, [activeShelf, entryIntent, initialShelf]);

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
