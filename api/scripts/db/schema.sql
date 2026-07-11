-- RelayDesk PostgreSQL schema (idempotent).
-- Run manually after RDS/database exists — not during API container startup.
-- Usage: uv run python scripts/init_db.py

CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    client_phone_number VARCHAR(32),
    client_business_phone_number VARCHAR(32) UNIQUE,
    client_name VARCHAR(255) NOT NULL DEFAULT '',
    client_email_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_sub VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_business_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    consumer_email_id VARCHAR(255) NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_client_consumer
    ON customers (client_email_id, consumer_phone_number);

CREATE INDEX IF NOT EXISTS idx_customers_client_business_phone
    ON customers (client_business_phone_number);

CREATE INDEX IF NOT EXISTS idx_customers_client_email
    ON customers (client_email_id);

CREATE TABLE IF NOT EXISTS call_jobs (
    id UUID PRIMARY KEY,
    client_business_phone_number VARCHAR(32) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_customers INTEGER NOT NULL DEFAULT 0,
    calls_completed INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    results_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_jobs_client_business_phone
    ON call_jobs (client_business_phone_number);

CREATE INDEX IF NOT EXISTS idx_call_jobs_client_email
    ON call_jobs (client_email_id);

CREATE INDEX IF NOT EXISTS idx_call_jobs_status
    ON call_jobs (status);
