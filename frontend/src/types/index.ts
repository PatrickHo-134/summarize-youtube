export type StatusState = 'idle' | 'loading' | 'success' | 'error';

export interface SummaryResponse {
  summary: string;
  source: 'cache' | 'llm';
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
  nextCursor: string | null;
}