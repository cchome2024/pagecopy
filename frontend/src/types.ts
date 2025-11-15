export type SnapshotStatus = 'success' | 'failed';

export interface SnapshotRequestBody {
  urls: string[];
  force_browser: boolean;
}

export interface SnapshotResult {
  original_url: string;
  archived_url: string | null;
  archived_relative_url: string | null;
  status: SnapshotStatus;
  error: string | null;
}

export interface SnapshotResponse {
  results: SnapshotResult[];
}

export interface SnapshotHistoryEntry {
  id: string;
  original_url: string;
  archived_url: string | null;
  archived_relative_url: string | null;
  status: SnapshotStatus;
  error: string | null;
  captured_at: string;
}

export interface HistoryResponse {
  items: SnapshotHistoryEntry[];
}
