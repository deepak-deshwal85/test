export interface ClientProfile {
  id: number;
  client_phone_number: string;
  client_name: string;
  client_email_id: string;
  created_at: string;
}

export interface Customer {
  id: number;
  client_id: number | null;
  client_phone_number: string;
  client_name: string;
  client_email_id: string;
  consumer_phone_number: string;
  consumer_email_id: string;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerListResponse {
  customers: Customer[];
  count: number;
}

export interface CallAttempt {
  customer_id: number;
  consumer_phone_number: string;
  success: boolean;
  detail: string;
}

export interface CallJob {
  id: string;
  client_phone_number: string;
  client_email_id: string;
  status: string;
  total_customers: number;
  calls_completed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  results: CallAttempt[] | null;
}

export interface CallJobListResponse {
  jobs: CallJob[];
  count: number;
}

export interface CollectionInfo {
  name: string;
  points_count: number;
  vector_size: number;
  client_phone_number?: string | null;
}

export interface CollectionListResponse {
  collections: string[];
  count: number;
  client_phone_number?: string | null;
  client_email_id?: string | null;
}

export interface DocumentSummary {
  document_id: string;
  source_uri: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  collection: string;
  documents: DocumentSummary[];
  count: number;
  client_phone_number?: string | null;
}

export interface SearchHit {
  text: string;
  score: number;
  source_uri: string | null;
}

export interface SearchResponse {
  hits: SearchHit[];
  count: number;
  collection: string;
  client_phone_number?: string | null;
  client_email_id?: string | null;
}

export interface HealthResponse {
  status: string;
}
