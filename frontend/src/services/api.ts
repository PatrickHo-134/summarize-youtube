import type { JobRecord, SubmitJobResponse } from '../types';

const VIDEO_ID_REGEX =
  /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;

export class ApiRequestError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

export function extractVideoId(youtubeUrl: string): string | null {
  const match = youtubeUrl.trim().match(VIDEO_ID_REGEX);
  return match ? match[1] : null;
}

async function parseJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export async function submitSummarizationJob(videoId: string, token: string): Promise<SubmitJobResponse> {
  const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/summarize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ video_id: videoId }),
  });

  const json = await parseJsonSafe(response);

  if (!response.ok) {
    throw new ApiRequestError(
      response.status,
      (json.error as string) ?? `Request failed with status ${response.status}`
    );
  }

  return json as unknown as SubmitJobResponse;
}

export async function checkJobStatus(jobId: string, token: string): Promise<JobRecord> {
  const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/jobs/${jobId}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await parseJsonSafe(response);

  if (!response.ok) {
    throw new ApiRequestError(
      response.status,
      (json.error as string) ?? `Request failed with status ${response.status}`
    );
  }

  return json as unknown as JobRecord;
}
