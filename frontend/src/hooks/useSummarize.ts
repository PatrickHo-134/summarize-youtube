import { useState } from 'react';
import { type StatusState } from '../types';

const API_ENDPOINT = 'https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize';

export function useSummarize() {
  const [status, setStatus] = useState<StatusState>('idle');
  const [summary, setSummary] = useState<string>('');
  const [source, setSource] = useState<'cache' | 'llm' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [lastUrl, setLastUrl] = useState<string>('');

  const summarize = async (url: string) => {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;

    setLastUrl(trimmedUrl);
    setStatus('loading');
    setErrorMessage('');

    try {
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmedUrl }),
      });

      const data = await response.json();

      if (response.ok) {
        setSummary(data.summary);
        setSource(data.source);
        setStatus('success');
      } else {
        setErrorMessage(data.error || 'Failed to summarize video.');
        setStatus('error');
      }
    } catch (err) {
      setErrorMessage('Network Error: Unable to reach the API endpoint.');
      setStatus('error');
    }
  };

  const retry = () => {
    if (lastUrl) {
      summarize(lastUrl);
    }
  };

  return {
    status,
    summary,
    source,
    errorMessage,
    summarize,
    retry,
  };
}