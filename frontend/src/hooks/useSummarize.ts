import { useState, useRef, useEffect, useCallback } from "react";
import type { SummarizeResponse } from "../types";
import { getAuthToken } from "../services/auth";
import {
  submitSummarizationJob,
  checkJobStatus,
  extractVideoId,
  sanitizeErrorMessage,
  ApiRequestError,
} from "../services/api";

const POLL_INTERVAL_MS = 2500;

export function useSummarize() {
  const [loading, setLoading] = useState<boolean>(false);
  const [polling, setPolling] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SummarizeResponse | null>(null);
  const [needsAuth, setNeedsAuth] = useState<boolean>(false);
  const [sessionExpired, setSessionExpired] = useState<boolean>(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const inFlightRef = useRef<boolean>(false);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    jobIdRef.current = null;
    setPolling(false);
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const pollJobStatus = useCallback(
    async (jobId: string) => {
      if (inFlightRef.current) return;
      inFlightRef.current = true;

      try {
        const token = await getAuthToken();
        if (!token) {
          stopPolling();
          setLoading(false);
          setNeedsAuth(true);
          return;
        }

        const job = await checkJobStatus(jobId, token);

        if (job.status === "COMPLETED") {
          stopPolling();
          setData({
            summary: job.result?.summary ?? "",
            title: job.result?.title,
            source: "llm",
          });
          setLoading(false);
        } else if (job.status === "FAILED") {
          stopPolling();
          setError(sanitizeErrorMessage(job.error_message));
          setLoading(false);
        }
      } catch (err) {
        if (
          err instanceof ApiRequestError &&
          (err.status === 401 || err.status === 403)
        ) {
          stopPolling();
          setSessionExpired(true);
          setLoading(false);
        }
      } finally {
        inFlightRef.current = false;
      }
    },
    [stopPolling]
  );

  const startPolling = useCallback(
    (jobId: string) => {
      jobIdRef.current = jobId;
      setPolling(true);
      intervalRef.current = setInterval(() => {
        if (jobIdRef.current) {
          pollJobStatus(jobIdRef.current);
        }
      }, POLL_INTERVAL_MS);
    },
    [pollJobStatus]
  );

  const submitUrl = async (youtubeUrl: string) => {
    stopPolling();
    setError(null);
    setData(null);
    setLoading(true);

    const videoId = extractVideoId(youtubeUrl);
    if (!videoId) {
      setError("Please enter a valid YouTube URL.");
      setLoading(false);
      return;
    }

    const token = await getAuthToken();
    if (!token) {
      setNeedsAuth(true);
      setLoading(false);
      return;
    }

    try {
      const response = await submitSummarizationJob(videoId, token);

      if (response.status === "COMPLETED") {
        setData({
          summary: response.data?.summary ?? "",
          title: response.data?.title,
          source: response.cached ? "cache" : "llm",
        });
        setLoading(false);
        return;
      }

      if (response.job_id) {
        startPolling(response.job_id);
      } else {
        setError("Unexpected response from server.");
        setLoading(false);
      }
    } catch (err) {
      if (
        err instanceof ApiRequestError &&
        (err.status === 401 || err.status === 403)
      ) {
        setSessionExpired(true);
      } else if (err instanceof ApiRequestError) {
        setError(sanitizeErrorMessage(err.message));
      } else {
        setError("Network Error: Unable to reach the API endpoint.");
      }
      setLoading(false);
    }
  };

  const reset = () => {
    stopPolling();
    setData(null);
    setError(null);
    setLoading(false);
    setNeedsAuth(false);
    setSessionExpired(false);
  };

  return {
    loading,
    polling,
    error,
    data,
    needsAuth,
    setNeedsAuth,
    sessionExpired,
    setSessionExpired,
    submitUrl,
    reset,
  };
}
