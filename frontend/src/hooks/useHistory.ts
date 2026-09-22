import { useState, useCallback } from 'react';
import type { HistoryItem } from '../types';
import { getAuthToken } from '../services/auth';

interface UseHistoryResult {
  items: HistoryItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  nextToken: string | null;
  error: string | null;
  fetch: () => Promise<void>;
  fetchMore: () => Promise<void>;
}

export function useHistory(): UseHistoryResult {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [nextToken, setNextToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async (cursor?: string | null) => {
    const isInitial = !cursor;
    if (isInitial) {
      setIsLoading(true);
    } else {
      setIsLoadingMore(true);
    }
    setError(null);

    try {
      const token = await getAuthToken();
      if (!token) {
        setError('You must be signed in to view your history.');
        return;
      }

      const url = new URL(`${import.meta.env.VITE_API_ENDPOINT}/history`);
      url.searchParams.set('limit', '10');
      if (cursor) {
        url.searchParams.set('next_token', cursor);
      }

      const response = await globalThis.fetch(url.toString(), {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const json = await response.json();

      if (!response.ok) {
        setError(json.error ?? `Failed to load history (${response.status}).`);
        return;
      }

      const newItems: HistoryItem[] = json.items ?? [];
      if (isInitial) {
        setItems(newItems);
      } else {
        setItems((prev) => [...prev, ...newItems]);
      }
      setNextToken(json.next_token ?? null);
    } catch {
      setError('Network error: unable to reach the history endpoint.');
    } finally {
      if (isInitial) {
        setIsLoading(false);
      } else {
        setIsLoadingMore(false);
      }
    }
  }, []);

  const fetch = useCallback(() => fetchHistory(null), [fetchHistory]);
  const fetchMore = useCallback(() => fetchHistory(nextToken), [fetchHistory, nextToken]);

  return { items, isLoading, isLoadingMore, nextToken, error, fetch, fetchMore };
}
