export type StatusState = 'idle' | 'loading' | 'success' | 'error';

export interface SummaryResponse {
  summary: string;
  source: 'cache' | 'llm';
}

export interface ApiError {
  error: string;
}