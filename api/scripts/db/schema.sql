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

CREATE TABLE IF NOT EXISTS consumers (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_business_phone_number VARCHAR(32) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    consumer_phone_number VARCHAR(32) NOT NULL,
    consumer_email_id VARCHAR(255) NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    call_schedule VARCHAR(3) NOT NULL DEFAULT 'no',
    status VARCHAR(32) NOT NULL DEFAULT 'READY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_consumers_client_consumer
    ON consumers (client_email_id, consumer_phone_number);

CREATE INDEX IF NOT EXISTS idx_consumers_client_business_phone
    ON consumers (client_business_phone_number);

CREATE INDEX IF NOT EXISTS idx_consumers_client_email
    ON consumers (client_email_id);

CREATE INDEX IF NOT EXISTS idx_consumers_call_schedule
    ON consumers (client_email_id, call_schedule);

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_call_schedule;

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_call_schedule
    CHECK (call_schedule IN ('yes', 'no'));

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_status;

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_status
    CHECK (status IN ('READY', 'MEETING_SCHEDULED', 'MEETING_NOT_SCHEDULED'));

CREATE TABLE IF NOT EXISTS call_jobs (
    id UUID PRIMARY KEY,
    client_business_phone_number VARCHAR(32) NOT NULL,
    client_email_id VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_consumers INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS call_summaries (
    id SERIAL PRIMARY KEY,
    consumer_id INTEGER NOT NULL REFERENCES consumers(id) ON DELETE CASCADE,
    client_email_id VARCHAR(255) NOT NULL,
    call_start_time TIMESTAMPTZ NOT NULL,
    call_end_time TIMESTAMPTZ,
    call_summary TEXT NOT NULL DEFAULT '',
    job_id UUID REFERENCES call_jobs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_summaries_consumer
    ON call_summaries (consumer_id);

CREATE INDEX IF NOT EXISTS idx_call_summaries_client_email
    ON call_summaries (client_email_id);

CREATE INDEX IF NOT EXISTS idx_call_summaries_call_start
    ON call_summaries (client_email_id, call_start_time DESC);

CREATE TABLE IF NOT EXISTS client_voice_agent_configs (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL UNIQUE REFERENCES clients(id) ON DELETE CASCADE,
    voice_agent_greeting_message TEXT NOT NULL DEFAULT (
        'Greet the caller briefly. Introduce the business and summarize key service '
        'offerings. Say you can answer questions by searching the uploaded documents. '
        'Ask what they would like to know.'
    ),
    calcom_username VARCHAR(255),
    calcom_event_type_slug VARCHAR(255),
    calcom_event_type_id INTEGER,
    calcom_organization_slug VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_voice_agent_configs_client_id
    ON client_voice_agent_configs (client_id);
