-- Seed data for local development (optional)
-- Run after init_db.sql against the relaydesk database.

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    client_business_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    CONSTRAINT uq_customers_client_consumer UNIQUE (
      client_business_phone_number,
      consumer_phone_number
    )
);

CREATE INDEX IF NOT EXISTS idx_customers_client_business_phone
ON customers (client_business_phone_number);

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_jobs_client_business_phone
ON call_jobs (client_business_phone_number);

INSERT INTO customers (client_business_phone_number, client_name, consumer_phone_number)
VALUES
    ('911171366880', 'Acme Corp', '9876543210'),
    ('911171366880', 'Acme Corp', '9123456780')
ON CONFLICT (client_business_phone_number, consumer_phone_number) DO NOTHING;
