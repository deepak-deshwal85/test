-- Windows-friendly PostgreSQL setup for RelayDesk API
-- Run: psql -U postgres -h localhost -p 5432 -f scripts/seed_db.sql

CREATE DATABASE relaydesk;

\c relaydesk

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    client_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customers_client_consumer UNIQUE (client_phone_number, consumer_phone_number)
);

CREATE INDEX IF NOT EXISTS idx_customers_client_phone ON customers (client_phone_number);

CREATE TABLE IF NOT EXISTS call_jobs (
    id UUID PRIMARY KEY,
    client_phone_number VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_customers INTEGER NOT NULL DEFAULT 0,
    calls_completed INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_jobs_client_phone ON call_jobs (client_phone_number);
CREATE INDEX IF NOT EXISTS idx_call_jobs_status ON call_jobs (status);

ALTER TABLE call_jobs
    ADD COLUMN IF NOT EXISTS results_json TEXT;

INSERT INTO customers (client_phone_number, client_name, consumer_phone_number)
VALUES
    ('911171366880', 'Deepak Kumar', '9876543210'),
    ('911171366880', 'Deepak Kumar', '9123456789'),
    ('911171366880', 'Deepak Kumar', '9988776655')
ON CONFLICT (client_phone_number, consumer_phone_number) DO NOTHING;
