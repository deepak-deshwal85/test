-- PostgreSQL setup for RelayDesk API
-- Run as postgres superuser, e.g.:
--   psql -U postgres -h localhost -p 5432 -f scripts/init_db.sql

CREATE DATABASE relaydesk
    WITH ENCODING 'UTF8'
    LC_COLLATE='en_US.UTF-8'
    LC_CTYPE='en_US.UTF-8'
    TEMPLATE template0;

\c relaydesk

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    client_phone_number VARCHAR(32) NOT NULL UNIQUE,
    client_name VARCHAR(255) NOT NULL DEFAULT '',
    client_email_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_sub VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    consumer_email_id VARCHAR(255) NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customers_client_consumer UNIQUE (
      client_email_id,
      consumer_phone_number
    )
);

CREATE INDEX idx_customers_client_phone ON customers (client_phone_number);
CREATE INDEX idx_customers_client_email ON customers (client_email_id);

CREATE TABLE call_jobs (
    id UUID PRIMARY KEY,
    client_phone_number VARCHAR(32) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_customers INTEGER NOT NULL DEFAULT 0,
    calls_completed INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_call_jobs_client_phone ON call_jobs (client_phone_number);
CREATE INDEX idx_call_jobs_client_email ON call_jobs (client_email_id);
CREATE INDEX idx_call_jobs_status ON call_jobs (status);

ALTER TABLE call_jobs
    ADD COLUMN IF NOT EXISTS results_json TEXT;
