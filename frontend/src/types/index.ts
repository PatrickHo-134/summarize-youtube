export type StatusState = 'idle' | 'loading' | 'success' | 'error';

export interface SummaryResponse {
  summary: string;
  source: 'cache' | 'llm';
  title?: string;
}

export type SummarizeResponse = SummaryResponse;

export interface ApiError {
  error: string;
}

export type AppView = 'new' | 'dashboard';

export interface HistoryItem {
  videoId: string;
  videoUrl: string;
  title?: string;
  summary: string;
  createdAt: string; // ISO date string e.g. "2026-09-12T10:00:00Z"
}

export interface HistoryPage {
  items: HistoryItem[];
  next_token: string | null;
}

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface JobResult {
  video_id: string;
  title?: string;
  summary: string;
}

export interface SubmitJobResponse {
  job_id?: string;
  status: JobStatus;
  cached?: boolean;
  data?: JobResult;
}

export interface JobRecord {
  job_id: string;
  video_id: string;
  user_id: string;
  status: JobStatus;
  result?: JobResult;
  error_message?: string;
  created_at?: string;
  updated_at?: string;
}