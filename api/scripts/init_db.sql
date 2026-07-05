-- PostgreSQL setup for Telephone Agent API
-- Run as postgres superuser, e.g.:
--   psql -U postgres -h localhost -p 5432 -f scripts/init_db.sql

CREATE DATABASE telephone_agent
    WITH ENCODING 'UTF8'
    LC_COLLATE='en_US.UTF-8'
    LC_CTYPE='en_US.UTF-8'
    TEMPLATE template0;

\c telephone_agent

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    client_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customers_client_consumer UNIQUE (client_phone_number, consumer_phone_number)
);

CREATE INDEX idx_customers_client_phone ON customers (client_phone_number);

CREATE TABLE call_jobs (
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

CREATE INDEX idx_call_jobs_client_phone ON call_jobs (client_phone_number);
CREATE INDEX idx_call_jobs_status ON call_jobs (status);

ALTER TABLE call_jobs
    ADD COLUMN IF NOT EXISTS results_json TEXT;
