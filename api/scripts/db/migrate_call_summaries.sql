-- Add call_summaries table for post-call transcripts and notes.
-- Usage: uv run python scripts/migrate_db.py --file db/migrate_call_summaries.sql

CREATE TABLE IF NOT EXISTS call_summaries (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    client_email_id VARCHAR(255) NOT NULL,
    call_start_time TIMESTAMPTZ NOT NULL,
    call_end_time TIMESTAMPTZ,
    call_summary TEXT NOT NULL DEFAULT '',
    job_id UUID REFERENCES call_jobs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_summaries_customer
    ON call_summaries (customer_id);

CREATE INDEX IF NOT EXISTS idx_call_summaries_client_email
    ON call_summaries (client_email_id);

CREATE INDEX IF NOT EXISTS idx_call_summaries_call_start
    ON call_summaries (client_email_id, call_start_time DESC);
