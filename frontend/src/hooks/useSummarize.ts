import { useState } from 'react';
import type { SummarizeResponse } from '../types';
import { getAuthToken } from '../services/auth';

export function useSummarize() {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SummarizeResponse | null>(null);
  const [needsAuth, setNeedsAuth] = useState<boolean>(false);

  const submitUrl = async (youtubeUrl: string) => {
    setError(null);
    setLoading(true);

    const token = await getAuthToken();

    if (!token) {
      setNeedsAuth(true);
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ url: youtubeUrl }),
      });

      const json = await response.json();

      if (!response.ok) {
        setError(json.error ?? `Request failed with status ${response.status}`);
      } else {
        setData(json as SummarizeResponse);
      }
    } catch {
      setError('Network Error: Unable to reach the API endpoint.');
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    data,
    needsAuth,
    setNeedsAuth,
    submitUrl,
  };
}
