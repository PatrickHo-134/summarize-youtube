import { useState, useCallback } from 'react';
import type { HistoryItem } from '../types';
import { getAuthToken } from '../services/auth';

interface UseHistoryResult {
  items: HistoryItem[];
  isLoading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export function useHistory(): UseHistoryResult {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = await getAuthToken();
      if (!token) {
        setError('You must be signed in to view your history.');
        return;
      }

      const response = await globalThis.fetch(
        `${import.meta.env.VITE_API_ENDPOINT}/history`,
        {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const json = await response.json();

      if (!response.ok) {
        setError(json.error ?? `Failed to load history (${response.status}).`);
        return;
      }

      setItems(json.items ?? []);
    } catch {
      setError('Network error: unable to reach the history endpoint.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { items, isLoading, error, fetch };
}
