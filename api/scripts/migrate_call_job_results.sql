-- Add per-call results to existing call_jobs table
ALTER TABLE call_jobs
    ADD COLUMN IF NOT EXISTS results_json TEXT;
